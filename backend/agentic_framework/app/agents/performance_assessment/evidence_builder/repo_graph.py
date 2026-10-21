"""Import graph and dependency reach of a checked-out repository (Task Complexity's "how many files depend on this one before the sprint started").

Ported from factor_models/dataset/scripts/repo_analysis.py so that it reads a working directory (a worktree at the right moment) instead of a local clone, has no
cache keyed only by name, and counts only ``code`` files (not tests), as the dataset build did. Known limits, as in the original: JS/TS/Dart resolve relative imports
only (no aliases, no tsconfig paths), Java/Kotlin match the class name only, Python matches the module name suffix.
"""
import re
from collections import defaultdict
from pathlib import Path, PurePosixPath

SOURCE = re.compile(r"\.(jsx?|tsx?|mjs|cjs|py|java|kt|dart|vue)$", re.I)
SKIP = re.compile(r"(^|/)(node_modules|dist|build|target|\.next|vendor|coverage|\.git)/")
JS_IMPORT = re.compile(r"""(?:import\s[^'"]*?from\s*|import\s*\(|require\s*\(|import\s+)['"]([^'"]+)['"]""")
JAVA_IMPORT = re.compile(r"^\s*import\s+(?:static\s+)?([\w.]+)\s*;", re.M)
PY_IMPORT = re.compile(r"^\s*(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))", re.M)
DART_IMPORT = re.compile(r"""^\s*import\s+['"]([^'"]+)['"]""", re.M)
MAX_FILES = 20000
MAX_BYTES = 400_000  # a source file larger than this is generated or data, not read


def source_files(root: Path, classify_path):
    """Relative posix paths of the ``code`` files (not tests, not vendored folders) under root."""
    out = []
    for p in root.rglob("*"):
        if len(out) >= MAX_FILES:
            break
        if not p.is_file():
            continue
        rel = p.relative_to(root).as_posix()
        if SOURCE.search(rel) and not SKIP.search(rel) and classify_path(rel) == "code":
            out.append(rel)
    return out


def resolve_relative(base, target, files):
    folder = PurePosixPath(base).parent
    parts = []
    for part in str(folder.joinpath(target)).split("/"):
        if part == "..":
            if parts:
                parts.pop()
        elif part and part != ".":
            parts.append(part)
    stem = "/".join(parts)
    for suffix in ("", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".vue", ".dart", "/index.js", "/index.jsx", "/index.ts", "/index.tsx"):
        if stem + suffix in files:
            return stem + suffix
    return None


def import_graph(root: Path, classify_path):
    """(set of files, {file: set of files it imports})."""
    names = source_files(root, classify_path)
    files = set(names)
    by_class, by_module = defaultdict(list), {}
    for n in names:
        p = PurePosixPath(n)
        if p.suffix in (".java", ".kt"):
            by_class[p.stem].append(n)
        if p.suffix == ".py":
            by_module[".".join(p.with_suffix("").parts)] = n
    edges = defaultdict(set)
    for n in names:
        full = root / n
        try:
            if full.stat().st_size > MAX_BYTES:
                continue
            text = full.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        suffix = PurePosixPath(n).suffix.lower()
        if suffix in (".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".vue"):
            for target in JS_IMPORT.findall(text):
                if target.startswith("."):
                    hit = resolve_relative(n, target, files)
                    if hit:
                        edges[n].add(hit)
        elif suffix in (".java", ".kt"):
            for target in JAVA_IMPORT.findall(text):
                for hit in by_class.get(target.split(".")[-1], []):
                    edges[n].add(hit)
        elif suffix == ".py":
            for a, b in PY_IMPORT.findall(text):
                module = a or b
                for key, hit in by_module.items():
                    if key.endswith(module):
                        edges[n].add(hit)
                        break
        elif suffix == ".dart":
            for target in DART_IMPORT.findall(text):
                if not target.startswith(("package:", "dart:")):
                    hit = resolve_relative(n, target, files)
                    if hit:
                        edges[n].add(hit)
    return files, edges


def dependency_reach(root: Path, classify_path):
    """{file: number of other files that depend on it directly or through one intermediate file (two hops)}."""
    files, edges = import_graph(root, classify_path)
    importers = defaultdict(set)
    for src, targets in edges.items():
        for t in targets:
            importers[t].add(src)
    result = {}
    for f in files:
        first = importers.get(f, set())
        second = set().union(*(importers.get(x, set()) for x in first)) if first else set()
        result[f] = len((first | second) - {f})
    return result
