"""V5 dependency scanners: OSV-Scanner, npm audit, pip-audit.

None of them may run student code: manifests and lockfiles are read, nothing is installed,
built or resolved by running a package manager's build step.
"""

import json
import shutil
from dataclasses import dataclass
from pathlib import Path

from app.agents.security_assistant.schemas import Category, Finding
from app.agents.security_assistant.tools.base import (
    BaseTool, NotApplicable, ScanContext, ScanOutput, ToolFailed, rel_path, run_command,
)
from app.agents.security_assistant.tools.languages import walk_repo

CWE_VULNERABLE_COMPONENT = "CWE-1104"
MAX_PROJECTS = 5


def _first_cwe(ids) -> str | None:
    if not ids:
        return None
    first = str(ids[0] if isinstance(ids, list) else ids)
    return first if first.upper().startswith("CWE-") else f"CWE-{first}"


# --- OSV-Scanner ---------------------------------------------------------------------------
def parse_osv(doc: dict, repo: Path) -> list[Finding]:
    findings = []
    for result in doc.get("results") or []:
        source = rel_path(repo, (result.get("source") or {}).get("path"))
        for pkg in result.get("packages") or []:
            info = pkg.get("package") or {}
            where = f"{info.get('name')}@{info.get('version')} ({info.get('ecosystem')})"
            for vuln in pkg.get("vulnerabilities") or []:
                db = vuln.get("database_specific") or {}
                cve = next((a for a in vuln.get("aliases") or [] if a.startswith("CVE-")), None)
                findings.append(
                    Finding(
                        category=Category.V5,
                        cwe=_first_cwe(db.get("cwe_ids")) or CWE_VULNERABLE_COMPONENT,
                        file_path=source,
                        sink=where,
                        rule_id=vuln.get("id", "unknown"),
                        severity_tool=str(db["severity"]) if db.get("severity") else None,
                        message=f"{cve + ': ' if cve else ''}{vuln.get('summary', '')}".strip(),
                    )
                )
    return findings


def gradle_without_lockfile(repo: Path) -> bool:
    """True if a Gradle build exists whose dependencies OSV-Scanner cannot read (no gradle.lockfile)."""
    gradle_dirs, locked = set(), set()
    for directory, names in walk_repo(repo):
        if any(n in names for n in ("build.gradle", "build.gradle.kts")):
            gradle_dirs.add(directory)
        if "gradle.lockfile" in names:
            locked.add(directory)
    return bool(gradle_dirs - locked)


@dataclass
class OsvScannerTool(BaseTool):
    name: str = "osv-scanner"
    binary: str = "osv-scanner"

    async def scan(self, ctx: ScanContext, exe: str | None) -> ScanOutput:
        argv = [exe, "scan", "source", "-r", "--format", "json", str(ctx.repo)]
        notes: list[str] = []
        # exit 0 = clean, 1 = vulnerabilities found, 128 = nothing scanned
        res = await run_command(argv, cwd=ctx.work_dir, timeout=self.timeout_s, accept_codes=(0, 1, 128))
        if res.returncode == 128 and "Error during extraction" in res.stderr:
            # Maven pom.xml is resolved online (Maven Central via deps.dev) to find transitive
            # dependencies. If that fails, scan only the versions written in the pom.
            res = await run_command(
                [*argv[:-1], "--no-resolve", argv[-1]], cwd=ctx.work_dir, timeout=self.timeout_s,
                accept_codes=(0, 1, 128),
            )
            notes.append("Maven registry unreachable: transitive dependencies NOT resolved, "
                         "only versions written in pom.xml were checked")
        if res.returncode == 128:
            if "Error" in res.stderr:
                raise ToolFailed(f"osv-scanner could not scan: {res.stderr.strip()[-200:]}")
            raise NotApplicable("no supported manifest or lockfile found")
        try:
            doc = json.loads(res.stdout)
        except json.JSONDecodeError as exc:
            raise ToolFailed(f"invalid_output: {exc}") from exc
        if gradle_without_lockfile(ctx.repo):
            notes.append("Gradle dependencies NOT scanned: no gradle.lockfile "
                         "(build.gradle is not read, and gradle is never run)")
        return ScanOutput(parse_osv(doc, ctx.repo), res.stdout, res.returncode, note="; ".join(notes) or None)


# --- npm audit -----------------------------------------------------------------------------
def parse_npm_audit(doc: dict, manifest: str) -> list[Finding]:
    findings = []
    for name, vuln in (doc.get("vulnerabilities") or {}).items():
        advisories = [v for v in vuln.get("via") or [] if isinstance(v, dict)]
        for adv in advisories:
            cwe = _first_cwe(adv.get("cwe"))
            findings.append(
                Finding(
                    category=Category.V5,
                    cwe=cwe or CWE_VULNERABLE_COMPONENT,
                    file_path=manifest,
                    sink=f"{name} {vuln.get('range', '')}".strip(),
                    rule_id=str(adv.get("source") or adv.get("url") or adv.get("title", "npm-advisory")),
                    severity_tool=adv.get("severity") or vuln.get("severity"),
                    message=adv.get("title", ""),
                )
            )
    return findings


@dataclass
class NpmAuditTool(BaseTool):
    name: str = "npm-audit"
    binary: str = "npm"
    languages: frozenset[str] | None = frozenset({"javascript", "typescript"})

    async def scan(self, ctx: ScanContext, exe: str | None) -> ScanOutput:
        projects = [d for d, names in walk_repo(ctx.repo) if "package.json" in names and "package-lock.json" in names]
        if not projects:
            raise NotApplicable("no package-lock.json (not generated: that would require npm install)")
        findings, raws = [], []
        for i, proj in enumerate(projects[:MAX_PROJECTS]):
            tmp = ctx.work_dir / f"npm-{i}"
            tmp.mkdir(parents=True, exist_ok=True)
            for f in ("package.json", "package-lock.json"):  # only the manifests, never the code
                shutil.copy(proj / f, tmp / f)
            res = await run_command(
                [exe, "audit", "--package-lock-only", "--json", "--ignore-scripts"],
                cwd=tmp, timeout=self.timeout_s, accept_codes=(0, 1),
            )
            try:
                doc = json.loads(res.stdout)
            except json.JSONDecodeError as exc:
                raise ToolFailed(f"invalid_output: {exc}") from exc
            if "error" in doc and "vulnerabilities" not in doc:
                raise ToolFailed(f"npm audit error: {str(doc['error'])[:200]}")
            manifest = rel_path(ctx.repo, str(proj / "package-lock.json"))
            findings += parse_npm_audit(doc, manifest)
            raws.append(res.stdout)
        return ScanOutput(findings, "\n".join(raws), 0)


# --- pip-audit -----------------------------------------------------------------------------
def parse_pip_audit(doc: dict, manifest: str) -> list[Finding]:
    findings = []
    for dep in doc.get("dependencies") or []:
        for vuln in dep.get("vulns") or []:
            fix = ", ".join(vuln.get("fix_versions") or [])
            cve = next((a for a in vuln.get("aliases") or [] if a.startswith("CVE-")), None)
            findings.append(
                Finding(
                    category=Category.V5,
                    cwe=CWE_VULNERABLE_COMPONENT,
                    file_path=manifest,
                    sink=f"{dep.get('name')}=={dep.get('version')}",
                    rule_id=vuln.get("id", "unknown"),
                    severity_tool=None,  # pip-audit reports no severity
                    message=f"{cve + ': ' if cve else ''}{(vuln.get('description') or '')[:200]}"
                    + (f" (fix: {fix})" if fix else ""),
                )
            )
    return findings


@dataclass
class PipAuditTool(BaseTool):
    name: str = "pip-audit"
    binary: str = "pip-audit"
    languages: frozenset[str] | None = frozenset({"python"})

    async def scan(self, ctx: ScanContext, exe: str | None) -> ScanOutput:
        files = [d / "requirements.txt" for d, names in walk_repo(ctx.repo) if "requirements.txt" in names]
        if not files:
            raise NotApplicable("no requirements.txt")
        findings, raws = [], []
        for req in files[:MAX_PROJECTS]:
            # --no-deps + --disable-pip: pins are checked as written, no resolving/installing.
            res = await run_command(
                [exe, "-r", str(req), "--no-deps", "--disable-pip", "--format", "json"],
                cwd=ctx.work_dir, timeout=self.timeout_s, accept_codes=(0, 1),
            )
            try:
                doc = json.loads(res.stdout)
            except json.JSONDecodeError as exc:
                # e.g. unpinned requirements make pip-audit refuse with --no-deps
                raise ToolFailed(f"invalid_output for {req.name}: {res.stderr.strip()[-200:]}") from exc
            findings += parse_pip_audit(doc, rel_path(ctx.repo, str(req)))
            raws.append(res.stdout)
        return ScanOutput(findings, "\n".join(raws), 0)
