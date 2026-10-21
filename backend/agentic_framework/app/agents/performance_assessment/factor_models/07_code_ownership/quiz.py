"""Phase 1 of Code Ownership: choose a piece of the student's own code and generate the comprehension question (proposal 3.1.8).

    generate(files, student_id, sprint_id) -> {file_path, line_range, code_snippet, question, question_type, reference_criteria, facts, ast_metadata, warnings}

``files`` are the source files where the student holds surviving counted lines (the ``owned_files`` of the ownership summary, from Effort's counted lines):
``[{"path": "src/orders.py", "text": "<file content>"}, ...]``. The choice is deterministic: a hash of student, sprint and function, so it can be repeated and the
student cannot shop for an easy snippet. Candidates are real logic only (cleaning.snippet_candidates: at least 8 counted lines, no getters, setters or shells).

Python functions get a structural question built from the syntax tree (questions.py). Other languages have no parser in the project yet, so they get the general
"what does it do and what do its parameters control" question, with a warning: the scorer was trained on Python and its quality on other languages is not measured.
"""
import ast
import hashlib
import importlib.util
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load(name, file):
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


cleaning = _load("ko_cleaning", "cleaning.py")
questions = _load("ko_questions", "questions.py")
QUIZ_VERSION = "ko_quiz/2"
MAX_SNIPPET_LINES = 60  # longer functions are asked about last: a student should be able to read the code in a minute
PARAMS = re.compile(r"\(([^()]*)\)")


def _h(text):
    return hashlib.sha256(text.encode()).hexdigest()


def display_code(func, src_lines):
    """Source text of a function without its docstring and comment-only lines (they would hand over the answer; also what the scorer was trained on)."""
    start, end = func.lineno, func.end_lineno
    lines = src_lines[start - 1:end]
    body = list(func.body)
    if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant) and isinstance(body[0].value.value, str):
        d0, d1 = body[0].lineno - start, body[0].end_lineno - start
        lines = lines[:d0] + lines[d1 + 1:]
    return "\n".join(ln for ln in lines if not ln.lstrip().startswith("#"))


def cyclomatic_complexity(func):
    return 1 + sum(isinstance(n, (ast.If, ast.For, ast.While, ast.ExceptHandler, ast.IfExp, ast.comprehension, ast.With, ast.Assert)) or (isinstance(n, ast.BoolOp) and len(n.values) - 1 > 0)
                   for n in ast.walk(func))


def _python_functions(text):
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return {}
    return {(n.name, n.lineno): n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}


def _generic_question(name, header):
    m = PARAMS.search(header or "")
    params = [p.strip().split("=")[0].split(":")[-1].split()[-1] for p in (m.group(1).split(",") if m else []) if p.strip() and p.strip().split()]
    ps = ", ".join(params[:3]) or "its arguments"
    return (f"In your own words, what does {name} do, and what do {ps} control?", ["Says what the function is for", "Says what each named parameter changes about the result"])


def candidates(files, blocks=False):
    """Whole functions the student wrote; with ``blocks`` also runs of real code in the same files that are not inside one of those functions (used when there are too few functions)."""
    out = []
    for f in files:
        path, text = f["path"], f.get("text", "")
        found = cleaning.snippet_candidates(path, text)
        for c in found:
            out.append({**c, "path": path, "text": text})
        if blocks:
            for b in cleaning.block_candidates(path, text):
                if not any(b["start"] < c["end"] and c["start"] < b["end"] for c in found):
                    out.append({**b, "path": path, "text": text})
    return out


def generate(files, student_id="", sprint_id="", salt="", forced_kind=None):
    """The quiz for one student and sprint, or ``None`` when no file has a function worth asking about."""
    cands = candidates(files)
    if not cands:
        return None
    cands.sort(key=lambda c: _h(f"{student_id}|{sprint_id}|{salt}|{c['path']}|{c['name']}|{c['start']}"))
    return _build(cands[0], student_id, sprint_id, salt, forced_kind)


def _build(c, student_id, sprint_id, salt="", forced_kind=None):
    """The question for one chosen candidate."""
    lines = c["text"].splitlines()
    warnings = []
    if c["path"].endswith(".py"):
        node = _python_functions(c["text"]).get((c["name"], c["start"]))
        if node is None:  # decorated or oddly placed definition: take the first function of that name
            node = next((n for (nm, _), n in _python_functions(c["text"]).items() if nm == c["name"]), None)
        if node is not None:
            facts = questions.facts(node)
            kinds = questions.available_types(facts)
            kind = forced_kind if forced_kind in kinds else sorted(kinds, key=lambda k: _h(f"{student_id}|{sprint_id}|{salt}|{k}"))[0]
            q, crit = questions.make_question(facts, kind)
            code = display_code(node, lines)
            meta = {"node_type": "FunctionDef", "name": c["name"], "cyclomatic_complexity": cyclomatic_complexity(node), "token_count": len(re.findall(r"\w+|[^\w\s]", code)), "language": "python"}
            return {"file_path": c["path"], "line_range": [node.lineno, node.end_lineno], "code_snippet": code, "question": q, "question_type": kind, "reference_criteria": crit,
                    "facts": facts, "ast_metadata": meta, "warnings": warnings, "version": QUIZ_VERSION}
    code = "\n".join(lines[c["start"] - 1:c["end"]])
    q, crit = _generic_question(c["name"], lines[c["start"] - 1] if c["start"] - 1 < len(lines) else "")
    warnings.append("no parser for this language: general question only; the answer scorer was trained on Python and is not validated here")
    return {"file_path": c["path"], "line_range": [c["start"], c["end"]], "code_snippet": code, "question": q, "question_type": "purpose", "reference_criteria": crit, "facts": None,
            "ast_metadata": {"node_type": c.get("kind", "function"), "name": c["name"], "cyclomatic_complexity": None, "token_count": len(re.findall(r"\w+|[^\w\s]", code)), "language": "other"},
            "warnings": warnings, "version": QUIZ_VERSION}


def generate_many(files, student_id="", sprint_id="", count=10, salt=""):
    """Select distinct snippets of the student's own code, at most three per file; when the files have too few whole functions, runs of real code fill the rest so the count is met whenever the code allows it."""
    count = max(0, min(int(count), 20))
    kinds = ["explain_behaviour", "predict_output", "edge_case", "spot_risk", "why_design"]
    out, per_file, snippets = [], {}, set()
    for blocks, cap in ((False, 3), (True, 5)):
        ranked = candidates(files, blocks=blocks)
        ranked.sort(key=lambda c: (c.get("kind") == "block", c.get("lines", 0) > MAX_SNIPPET_LINES, -min(c.get("lines", 0), MAX_SNIPPET_LINES), _h(f"{student_id}|{sprint_id}|{c['path']}|{c['name']}|{c['start']}")))
        for c in ranked:
            if len(out) >= count:
                break
            if per_file.get(c["path"], 0) >= cap:
                continue
            q = _build(c, student_id, sprint_id, salt=f"{salt}:{len(out)}", forced_kind=kinds[len(out) % len(kinds)])
            if q and q["code_snippet"] not in snippets:
                out.append(q)
                snippets.add(q["code_snippet"])
                per_file[c["path"]] = per_file.get(c["path"], 0) + 1
        if len(out) >= count:
            break
    return out
