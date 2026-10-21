"""Coverage gaps in the dependency check: a dependency that a manifest DECLARES but that no scanner can look at.

The dependency scanners read lockfiles and pinned lists (never the manifest alone, and they never install anything). If package.json
declares express but package-lock.json does not list it, express is never checked, and a clean result for it means nothing. This module
compares what is declared with what is locked and returns one sentence per gap. The sentences go into the scan result, the report and
the incomplete reasons of a run, so the skipped check is visible.

Pure file reading; nothing is run or resolved.
"""

import json
import re
import tomllib
from pathlib import Path

from app.agents.security_assistant.tools.languages import walk_repo

DEPENDENCY_TOOLS = frozenset({"osv-scanner", "npm-audit", "pip-audit"})
MAX_NAMES = 8
MAX_BYTES = 2_000_000
_GRADLE_CONFIG = (r"implementation|api|compile|compileOnly|runtimeOnly|testImplementation|testRuntimeOnly|testCompileOnly|"
                  r"annotationProcessor|kapt|developmentOnly")
_GRADLE_DECL = re.compile(rf"\b(?:{_GRADLE_CONFIG})\s*\(?\s*['\"]([^'\":\s]+):([^'\":\s]+)(?::([^'\"]*))?['\"]")
_NPM_LOCAL = ("file:", "link:", "workspace:", "portal:")


def _names(names) -> str:
    names = sorted(names)
    return ", ".join(names[:MAX_NAMES]) + (f" and {len(names) - MAX_NAMES} more" if len(names) > MAX_NAMES else "")


def _plural(n: int, one: str, many: str) -> str:
    return one if n == 1 else many


def _read(path: Path) -> str | None:
    try:
        if path.stat().st_size > MAX_BYTES:
            return None
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _rel(repo: Path, path: Path) -> str:
    try:
        return path.relative_to(repo).as_posix()
    except ValueError:
        return path.name


# ---- npm -------------------------------------------------------------------------------------------------------------------------------------
def _npm(repo: Path, directory: Path) -> list[str]:
    manifest = directory / "package.json"
    try:
        doc = json.loads(_read(manifest) or "")
    except ValueError:
        return []
    declared = {n for key in ("dependencies", "devDependencies", "optionalDependencies") for n, v in (doc.get(key) or {}).items()
                if isinstance(v, str) and not v.startswith(_NPM_LOCAL)}
    if not declared:
        return []
    where = _rel(repo, manifest)
    for lock_name in ("package-lock.json", "npm-shrinkwrap.json"):
        lock = directory / lock_name
        if lock.is_file():
            try:
                lock_doc = json.loads(_read(lock) or "")
            except ValueError:
                return [f"{where}: {lock_name} cannot be read, so its {len(declared)} declared dependencies were not checked"]
            locked = {k.split("node_modules/")[-1] for k in (lock_doc.get("packages") or {}) if k} | set(lock_doc.get("dependencies") or {})
            missing = declared - locked
            return ([f"{where} declares {len(missing)} {_plural(len(missing), 'dependency', 'dependencies')} that {lock_name} does not list, "
                     f"so no scanner checked {_plural(len(missing), 'it', 'them')}: {_names(missing)}"] if missing else [])
    for lock_name in ("yarn.lock", "pnpm-lock.yaml"):
        lock = directory / lock_name
        if lock.is_file():
            text = _read(lock) or ""
            missing = {n for n in declared if n not in text}
            return ([f"{where} declares {len(missing)} {_plural(len(missing), 'dependency', 'dependencies')} that {lock_name} does not mention, "
                     f"so no scanner checked {_plural(len(missing), 'it', 'them')}: {_names(missing)}"] if missing else [])
    return [f"{where} has no lockfile (package-lock.json, yarn.lock or pnpm-lock.yaml): its {len(declared)} declared "
            f"{_plural(len(declared), 'dependency was', 'dependencies were')} not checked: {_names(declared)}"]


# ---- Python ---------------------------------------------------------------------------------------------------------------------------------
def _norm(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).strip().lower()


_REQ = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)\s*(?:\[[^\]]*\])?\s*([^;#]*)")


def _requirements(path: Path) -> tuple[dict[str, bool], bool]:
    """({normalised name: pinned to an exact version}, readable)."""
    text = _read(path)
    if text is None:
        return {}, False
    out: dict[str, bool] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", "-", "git+", "http")) or "://" in line:
            continue
        m = _REQ.match(line)
        if not m:
            continue
        spec = m.group(2).strip()
        out[_norm(m.group(1))] = bool(re.search(r"(?<![<>!~=])===?\s*[\w!+-][\w.!+-]*$", spec.split(",")[0].strip())) and "*" not in spec
    return out, True


def _python(repo: Path, directory: Path, names: list[str]) -> list[str]:
    gaps: list[str] = []
    pinned_names: set[str] = set()
    for req in sorted(n for n in names if re.fullmatch(r"requirements[\w.-]*\.txt", n, re.I)):
        entries, ok = _requirements(directory / req)
        if not ok:
            continue
        pinned_names |= {n for n, pinned in entries.items() if pinned}
        loose = {n for n, pinned in entries.items() if not pinned}
        if loose:
            gaps.append(f"{_rel(repo, directory / req)} lists {len(loose)} {_plural(len(loose), 'requirement', 'requirements')} without an exact "
                        f"version (==): {_names(loose)}. pip-audit and OSV-Scanner cannot tell which version is installed, so "
                        f"{_plural(len(loose), 'it was', 'they were')} not reliably checked")
    if "pyproject.toml" in names:
        try:
            doc = tomllib.loads(_read(directory / "pyproject.toml") or "")
        except tomllib.TOMLDecodeError:
            return gaps
        declared = {_norm(m.group(1)) for d in (doc.get("project") or {}).get("dependencies") or [] if (m := _REQ.match(str(d)))}
        declared |= {_norm(n) for n in (((doc.get("tool") or {}).get("poetry") or {}).get("dependencies") or {}) if n.lower() != "python"}
        if declared:
            locked: set[str] = set()
            for lock_name in ("poetry.lock", "uv.lock", "pdm.lock", "Pipfile.lock"):
                text = _read(directory / lock_name) if lock_name in names else None
                if text:
                    locked |= {_norm(n) for n in re.findall(r'(?m)^\s*name\s*=\s*"([^"]+)"', text)} | {_norm(n) for n in re.findall(r'"([A-Za-z0-9._-]+)"\s*:\s*\{', text)}
            missing = declared - locked - pinned_names
            if missing:
                gaps.append(f"{_rel(repo, directory / 'pyproject.toml')} declares {len(missing)} {_plural(len(missing), 'dependency', 'dependencies')} that "
                            f"no lockfile (poetry.lock, uv.lock, pdm.lock, Pipfile.lock) or pinned requirements file lists, so no scanner checked "
                            f"{_plural(len(missing), 'it', 'them')}: {_names(missing)}")
    return gaps


# ---- Maven and Gradle --------------------------------------------------------------------------------------------------------------------------
def _maven(repo: Path, directory: Path) -> list[str]:
    path = directory / "pom.xml"
    text = _read(path)
    if text is None:
        return []
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    managed = "<parent>" in text or "<dependencyManagement>" in text  # a version can come from there (OSV-Scanner resolves it online)
    props = dict(re.findall(r"<([\w.\-]+)>([^<]*)</\1>", (re.search(r"<properties>(.*?)</properties>", text, re.S) or [None, ""])[1]))
    body = re.sub(r"<(dependencyManagement|build|profiles|reporting)>.*?</\1>", "", text, flags=re.S)
    unresolved = set()
    for block in re.findall(r"<dependency>(.*?)</dependency>", body, flags=re.S):
        group, artifact = (re.search(rf"<{t}>\s*([^<\s]+)\s*</{t}>", block) for t in ("groupId", "artifactId"))
        version = re.search(r"<version>\s*([^<\s]+)\s*</version>", block)
        if not (group and artifact):
            continue
        value = version.group(1) if version else None
        if value and value.startswith("${"):
            value = props.get(value[2:-1])
        if not value and not managed:
            unresolved.add(f"{group.group(1)}:{artifact.group(1)}")
    return ([f"{_rel(repo, path)} declares {len(unresolved)} {_plural(len(unresolved), 'dependency', 'dependencies')} without a version that this pom "
             f"cannot resolve (no <parent> and no dependencyManagement), so no scanner checked {_plural(len(unresolved), 'it', 'them')}: "
             f"{_names(unresolved)}"] if unresolved else [])


def _gradle(repo: Path, directory: Path, names: list[str]) -> list[str]:
    build = next((n for n in ("build.gradle", "build.gradle.kts") if n in names), None)
    if build is None:
        return []
    declared = {f"{g}:{a}" for g, a, _v in _GRADLE_DECL.findall(_read(directory / build) or "")}
    if not declared:
        return []
    if "gradle.lockfile" not in names:
        return [f"{_rel(repo, directory / build)} has no gradle.lockfile: its {len(declared)} declared "
                f"{_plural(len(declared), 'dependency was', 'dependencies were')} not checked (build.gradle is not read, and gradle is never run): {_names(declared)}"]
    locked = {":".join(line.split("=")[0].split(":")[:2]) for line in (_read(directory / "gradle.lockfile") or "").splitlines()
              if line and not line.startswith("#") and ":" in line}
    missing = declared - locked
    return ([f"{_rel(repo, directory / build)} declares {len(missing)} {_plural(len(missing), 'dependency', 'dependencies')} that gradle.lockfile does "
             f"not list, so no scanner checked {_plural(len(missing), 'it', 'them')}: {_names(missing)}"] if missing else [])


def find_dependency_gaps(repo: Path) -> list[str]:
    """One sentence per declared-but-not-checked dependency group, in a stable order."""
    repo = Path(repo)
    gaps: list[str] = []
    for directory, names in sorted(walk_repo(repo), key=lambda x: str(x[0])):
        if "package.json" in names:
            gaps += _npm(repo, directory)
        gaps += _python(repo, directory, names)
        if "pom.xml" in names:
            gaps += _maven(repo, directory)
        gaps += _gradle(repo, directory, names)
    return gaps
