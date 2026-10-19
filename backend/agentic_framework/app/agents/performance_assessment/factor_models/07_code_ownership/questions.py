"""Deterministic comprehension questions from a function's syntax tree (proposal 3.1.8: "AST analysis and static analysis ... generate a comprehension question
specifically relevant to that code").

No language model is involved. The facts come from the tree, the question from a template that names those facts, and the reference criteria are the same facts
in words, so what a good answer must contain is checkable. Static, structure-based questions only: the proposal's own benchmark (Jask) shows such questions are
answerable reliably, while execution-tracing questions are not.

Python only: the standard library `ast` is used. Other languages need a parser the project does not have yet (see ../PROTOCOL.md).
"""
import ast

QUESTION_TYPES = ("guard", "handler", "early_return", "loop", "purpose", "return_value")


def _u(node):
    return ast.unparse(node)


def _short(text, n=70):
    text = " ".join(text.split())
    return text if len(text) <= n else text[: n - 3] + "..."


class _Facts(ast.NodeVisitor):
    def __init__(self, name):
        self.name = name
        self.guards, self.handlers, self.early_returns, self.loops, self.calls, self.returns = [], [], [], [], [], []
        self.recursive = False

    def visit_If(self, node):
        body_raise = [s for s in node.body if isinstance(s, ast.Raise)]
        if body_raise and body_raise[0].exc is not None:
            exc = body_raise[0].exc
            kind = _u(exc.func) if isinstance(exc, ast.Call) else _u(exc)
            self.guards.append({"cond": _u(node.test), "raises": kind})
        elif node.body and isinstance(node.body[0], ast.Return) and node.body[0].value is not None:
            self.early_returns.append({"cond": _u(node.test), "value": _u(node.body[0].value)})
        self.generic_visit(node)

    def visit_Try(self, node):
        for h in node.handlers:
            what = _u(h.type) if h.type is not None else "any exception"
            then = "re-raises" if any(isinstance(s, ast.Raise) for s in h.body) else ("returns " + _u(h.body[0].value) if h.body and isinstance(h.body[0], ast.Return) and h.body[0].value else "carries on")
            self.handlers.append({"exc": what, "then": then})
        self.generic_visit(node)

    visit_TryStar = visit_Try

    def visit_For(self, node):
        self.loops.append({"target": _u(node.target), "iter": _u(node.iter)})
        self.generic_visit(node)

    visit_AsyncFor = visit_For

    def visit_While(self, node):
        self.loops.append({"target": None, "iter": _u(node.test)})
        self.generic_visit(node)

    def visit_Return(self, node):
        if node.value is not None:
            self.returns.append(_u(node.value))
        self.generic_visit(node)

    def visit_Call(self, node):
        name = _u(node.func)
        if name == self.name:
            self.recursive = True
        elif not name.startswith(("isinstance", "len", "range", "str", "int", "list", "dict", "set", "tuple", "sorted", "enumerate", "zip", "min", "max", "sum", "any", "all")):
            self.calls.append(name)
        self.generic_visit(node)


def facts(func):
    f = _Facts(func.name)
    for stmt in func.body:
        f.visit(stmt)
    params = [a.arg for a in func.args.posonlyargs + func.args.args + func.args.kwonlyargs if a.arg not in ("self", "cls")]
    calls = [c for c in dict.fromkeys(f.calls) if not c.endswith(("Error", "Exception", "Warning"))]
    return {"name": func.name, "params": params, "guards": f.guards, "handlers": f.handlers, "early_returns": f.early_returns, "loops": f.loops,
            "calls": calls, "returns": list(dict.fromkeys(f.returns)), "recursive": f.recursive}


def available_types(fc):
    out = []
    if fc["guards"]:
        out.append("guard")
    if fc["handlers"]:
        out.append("handler")
    if fc["early_returns"]:
        out.append("early_return")
    if fc["loops"]:
        out.append("loop")
    if fc["returns"] and (fc["calls"] or fc["loops"]):
        out.append("return_value")
    out.append("purpose")
    return out


def make_question(fc, kind):
    """(question, reference criteria) for one question type, or None when the facts do not support it."""
    n = fc["name"]
    if kind == "guard" and fc["guards"]:
        g = fc["guards"][0]
        return (f"In {n}, what happens when `{_short(g['cond'])}` is true, and why is that case rejected?",
                [f"Says that {g['raises']} is raised when {_short(g['cond'])}", "Explains why that input cannot be processed or would give a wrong result"])
    if kind == "handler" and fc["handlers"]:
        h = fc["handlers"][0]
        return (f"Why does {n} catch {h['exc']}, and what happens to the call after it is caught?",
                [f"Says what situation raises {h['exc']}", f"Says that the function {h['then']} afterwards"])
    if kind == "early_return" and fc["early_returns"]:
        e = fc["early_returns"][0]
        return (f"What does {n} return when `{_short(e['cond'])}` holds, and why can it return at that point?",
                [f"Says that it returns {_short(e['value'])} in that case", "Explains why nothing more has to be done in that case"])
    if kind == "loop" and fc["loops"]:
        lp = fc["loops"][0]
        what = f"`for {lp['target']} in {_short(lp['iter'])}`" if lp["target"] else f"`while {_short(lp['iter'])}`"
        return (f"What does the loop {what} in {n} do, and what is left behind when it finishes?",
                ["Says what each pass over the loop does", "Says what the loop has produced or changed when it ends"])
    if kind == "return_value" and fc["returns"]:
        return (f"Describe what {n} returns on its normal path and how that value is built up.",
                [f"Says that it returns {_short(fc['returns'][-1])}", "Explains how that value is produced from the inputs"] + ([f"Mentions that it calls {fc['calls'][0]}"] if fc["calls"] else []))
    if kind == "purpose":
        ps = ", ".join(fc["params"][:3]) or "its arguments"
        return (f"In your own words, what does {n} do, and what do {ps} control?",
                ["Says what the function is for", "Says what each named parameter changes about the result"])
    return None
