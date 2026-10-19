"""Picks real functions from the Python standard library as the code side of the Code Ownership dataset, and generates a question for each.

    python select_snippets.py <path to the Python standard library folder>

Why the standard library: it is real, public (PSF licence), reviewed code with the kind of logic a student writes, and using it means no student code and
no personal data are involved. The student code of the project is never read here.

Selection (fixed before looking at any function): at least MIN_LINES and at most MAX_LINES counted code lines (same counting as the Code Ownership factor),
not a trivial function (getter, setter, constructor shell), no nested functions, no generators, at most MAX_PRIVATE distinct private attributes or names (so the
function can be understood without the rest of a large library), at most PER_MODULE per module, and the docstring and comment-only lines are removed from the
displayed code (they would hand the answer over). Question types are balanced: PER_TYPE functions for each type that the tree supports. Order inside a type is a
hash order, so the choice does not depend on how good or bad a function looks.
"""
import ast
import csv
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FM = HERE.parents[2]  # factor_models/
sys.path.insert(0, str(FM))
sys.path.insert(0, str(HERE.parents[1]))
from evidence.lines import State, classify_line, style_for  # noqa: E402
import questions as Q  # noqa: E402
from quiz import display_code  # noqa: E402

MIN_LINES, MAX_LINES, PER_MODULE, PER_TYPE, MAX_PRIVATE = 9, 20, 1, 6, 1
SKIP_MODULES = {"antigravity", "this", "__hello__", "__phello__"}
SKIP_DIRS = {"asyncio", "unittest", "logging", "xmlrpc", "test", "tests", "idlelib", "lib2to3", "site-packages", "__pycache__", "turtledemo", "ensurepip", "pydoc_data", "tkinter", "venv", "_pyrepl", "encodings", "distutils", "msilib"}
TRIVIAL = ("__init__", "__repr__", "__str__", "__eq__", "__hash__", "__enter__", "__exit__")


def counted(lines, style):
    state = State()
    return sum(1 for ln in lines if classify_line(ln, style, state) == "code")


def private_refs(func):
    names = set()
    for n in ast.walk(func):
        if isinstance(n, ast.Attribute) and n.attr.startswith("_") and not n.attr.startswith("__"):
            names.add(n.attr)
        elif isinstance(n, ast.Name) and n.id.startswith("_") and not n.id.startswith("__"):
            names.add(n.id)
    return len(names)


def candidates(stdlib):
    out = []
    for path in sorted(Path(stdlib).glob("*.py")) + sorted(p for d in Path(stdlib).iterdir() if d.is_dir() and d.name not in SKIP_DIRS for p in d.glob("*.py")):
        if path.stem in SKIP_MODULES or path.parent.name in SKIP_DIRS:
            continue
        try:
            text = path.read_text(encoding="utf-8")
            tree = ast.parse(text)
        except (SyntaxError, UnicodeDecodeError):
            continue
        src_lines = text.splitlines()
        rel = path.relative_to(stdlib).as_posix()
        for node in tree.body + [n for c in tree.body if isinstance(c, ast.ClassDef) for n in c.body]:
            if not isinstance(node, ast.FunctionDef) or node.name in TRIVIAL or node.name.startswith(("_test", "__")) or node.decorator_list:
                continue
            if any(isinstance(n, (ast.Yield, ast.YieldFrom, ast.Global, ast.Nonlocal, ast.AsyncFunctionDef, ast.Lambda)) for n in ast.walk(node)) or any(isinstance(n, ast.FunctionDef) for n in ast.walk(node) if n is not node) or private_refs(node) > MAX_PRIVATE:
                continue
            code = display_code(node, src_lines)
            n = counted(code.splitlines(), style_for(path.name))
            if not MIN_LINES <= n <= MAX_LINES:
                continue
            fc = Q.facts(node)
            out.append({"module": rel, "name": node.name, "code": code, "counted_lines": n, "facts": fc, "types": Q.available_types(fc)})
    return out


def pick(cands):
    def key(c):
        return hashlib.sha256(f"{c['module']}::{c['name']}".encode()).hexdigest()
    chosen, per_module = [], {}
    for kind in Q.QUESTION_TYPES:
        pool = sorted((c for c in cands if kind in c["types"] and (kind != "purpose" or True) and not any(x is c for x, _ in chosen)), key=key)
        # prefer functions where the type is a real structural feature: purpose is used only for what is left over
        taken = 0
        for c in pool:
            if taken >= PER_TYPE:
                break
            if per_module.get(c["module"], 0) >= PER_MODULE or any(x is c for x, _ in chosen):
                continue
            chosen.append((c, kind))
            per_module[c["module"]] = per_module.get(c["module"], 0) + 1
            taken += 1
    return chosen


def main(stdlib):
    cands = candidates(stdlib)
    # structural types first so the leftover pool serves "purpose"
    chosen = pick(cands)
    rows = []
    for i, (c, kind) in enumerate(chosen, start=1):
        q, crit = Q.make_question(c["facts"], kind)
        rows.append({"snippet_id": f"K{i:03d}", "source": f"cpython/Lib/{c['module']}", "function": c["name"], "counted_lines": c["counted_lines"], "question_type": kind,
                     "code": c["code"], "question": q, "reference_criteria": json.dumps(crit), "facts": json.dumps(c["facts"])})
    out = HERE.parent / "dataset" / "snippets.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(len(cands), "candidate functions;", len(rows), "selected ->", out)
    from collections import Counter
    print(Counter(r["question_type"] for r in rows))


if __name__ == "__main__":
    main(sys.argv[1])
