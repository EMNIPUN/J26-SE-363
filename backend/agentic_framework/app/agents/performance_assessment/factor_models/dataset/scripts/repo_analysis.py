"""Measurements that need the repositories themselves: the import graph at a point in time
(dependency reach, Task Complexity) and who wrote the code that survives at the final version
(Code Ownership). Results are cached in ``private/cache`` because blame is slow.
"""

import json
import re
import subprocess
from collections import defaultdict
from pathlib import PurePosixPath

from identity import PRIVATE

CACHE = PRIVATE / "cache"
SOURCE = re.compile(r"\.(jsx?|tsx?|mjs|cjs|py|java|kt|dart|vue)$", re.I)
SKIP = re.compile(r"(^|/)(node_modules|dist|build|target|\.next|vendor|coverage)/")
JS_IMPORT = re.compile(r"""(?:import\s[^'"]*?from\s*|import\s*\(|require\s*\(|import\s+)['"]([^'"]+)['"]""")
JAVA_IMPORT = re.compile(r"^\s*import\s+(?:static\s+)?([\w.]+)\s*;", re.M)
PY_IMPORT = re.compile(r"^\s*(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))", re.M)
DART_IMPORT = re.compile(r"""^\s*import\s+['"]([^'"]+)['"]""", re.M)


def git(path, *args, data=None):
    return subprocess.run(
        ["git", "-C", str(path), *args], input=data, capture_output=True, check=True
    ).stdout


def snapshot(path, before):
    """The newest commit on any branch made before ``before`` (an ISO date), or None."""
    out = git(path, "rev-list", "-1", "--all", f"--before={before}T00:00:00").decode().strip()
    return out or None


def source_files(path, rev):
    names = git(path, "ls-tree", "-r", "--name-only", rev).decode("utf-8", "replace").splitlines()
    return [n for n in names if SOURCE.search(n) and not SKIP.search(n)]


def read_files(path, rev, names):
    """Contents of many files at one revision through a single cat-file process."""
    request = "".join(f"{rev}:{n}\n" for n in names).encode()
    out = git(path, "cat-file", "--batch", data=request)
    contents, i = {}, 0
    for name in names:
        header_end = out.index(b"\n", i)
        header = out[i:header_end].split()
        if header[-1] == b"missing":
            i = header_end + 1
            continue
        size = int(header[2])
        start = header_end + 1
        contents[name] = out[start:start + size].decode("utf-8", "replace")
        i = start + size + 1
    return contents


def resolve_relative(base, target, files):
    folder = PurePosixPath(base).parent
    candidate = str(folder.joinpath(target))
    parts = []
    for part in candidate.split("/"):
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


def import_graph(path, rev):
    """file -> set of files it imports (inside the repository)."""
    names = source_files(path, rev)
    files = set(names)
    contents = read_files(path, rev, names)
    by_class = defaultdict(list)  # Java/Kotlin: class name -> files
    by_module = {}  # Python: dotted module -> file
    for n in names:
        p = PurePosixPath(n)
        if p.suffix in (".java", ".kt"):
            by_class[p.stem].append(n)
        if p.suffix == ".py":
            by_module[".".join(p.with_suffix("").parts)] = n
    edges = defaultdict(set)
    for n, text in contents.items():
        suffix = PurePosixPath(n).suffix.lower()
        if suffix in (".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".vue"):
            for target in JS_IMPORT.findall(text):
                if target.startswith("."):
                    hit = resolve_relative(n, target, files)
                    if hit:
                        edges[n].add(hit)
        elif suffix in (".java", ".kt"):
            for target in JAVA_IMPORT.findall(text):
                cls = target.split(".")[-1]
                for hit in by_class.get(cls, []):
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


def dependency_reach(path, before, cache_key):
    """For every source file that existed before ``before``: how many other files depend on it
    directly or through one intermediate file (two hops)."""
    cache = CACHE / f"reach_{cache_key}.json"
    if cache.exists():
        return json.loads(cache.read_text())
    rev = snapshot(path, before)
    result = {}
    if rev:
        files, edges = import_graph(path, rev)
        importers = defaultdict(set)
        for src, targets in edges.items():
            for t in targets:
                importers[t].add(src)
        for f in files:
            first = importers.get(f, set())
            second = set().union(*(importers.get(x, set()) for x in first)) if first else set()
            result[f] = len((first | second) - {f})
    CACHE.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(result))
    return result


def blame_owners(path, files, cache_key):
    """At the repository's final version: for each file, the commit that last wrote each line.
    Returns {file: {sha: line_count}}."""
    cache = CACHE / f"blame_{cache_key}.json"
    if cache.exists():
        return json.loads(cache.read_text())
    head = git(path, "rev-parse", "HEAD").decode().strip()
    existing = set(git(path, "ls-tree", "-r", "--name-only", head).decode("utf-8", "replace").splitlines())
    result = {}
    for f in sorted(set(files) & existing):
        try:
            out = git(path, "blame", "--line-porcelain", "-w", head, "--", f).decode("utf-8", "replace")
        except subprocess.CalledProcessError:
            continue
        counts = defaultdict(int)
        for line in out.splitlines():
            if len(line) >= 40 and re.match(r"^[0-9a-f]{40} \d+ \d+", line):
                counts[line[:40]] += 1
        result[f] = dict(counts)
    CACHE.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(result))
    return result
