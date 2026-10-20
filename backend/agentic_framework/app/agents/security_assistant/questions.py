"""Probe questions for confirmed findings, and a clearly labelled MOCK Tutor that scores the answer.

    python -m app.agents.security_assistant.questions <interpreted.json> <repo folder> [--threshold 0.7] [--out DIR]

One question per confirmed finding (a package with several advisories is one finding group, so one question). The question is
built from the student's own code: Python with the `ast` module (the function that contains the flagged line), Java and
JS/TS with a simple text search for the enclosing function. Secrets and personal data are redacted first. The question asks
the student to reason about what the code does with outside input; it never states the fix (a guard checks the wording).

The Tutor is an interface (`TutorChannel`). The only implementation here is `MockTutor`, which returns a simulated
comprehension score and says so in every record: no real student has answered anything. A finding is "closed" only when the
score reaches the threshold; below it the finding stays "open". "Closed" means the student showed they understand the
problem; it is not a claim that the code was fixed. Every score and decision is logged in questions.json.

Exit code: 0 ok, 3 usage error.
"""

import argparse
import ast
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
from typing import Protocol

from app.agents.security_assistant.interpreter.evidence import _safe_file
from app.agents.security_assistant.interpreter.redaction import redact_text
from app.agents.security_assistant.pii import PIIRedactor
from app.agents.security_assistant.report import upsert_section

SECTION_MARK = "<!-- probe-questions -->"
DEFAULT_THRESHOLD = 0.7
MAX_EXCERPT_LINES = 14
WINDOW = 5

# Words that would tell the student the answer. The templates below avoid them; the guard makes sure it stays that way.
_LEAKS = re.compile(
    r"parameteri[sz]|prepared statement|bind variable|placeholder|bcrypt|argon2|scrypt|pbkdf2|sanitis|sanitiz|escap(?:e|ing)|"
    r"allow-?list|white-?list|environment variable|secrets? manager|vault|should (?:use|add|check|replace|move|set|be)|"
    r"you (?:should|must|need to|can fix)|instead of|replace (?:it )?with|upgrade to|rotate|pin(?:ned)? to|"
    r"\bfix(?:ed|es)?\b|\bremedia|\bmitigat|csrf token|rate.?limit(?:er|ing)? (?:should|to)|check (?:the )?owner|ownership check",
    re.I)


class TutorChannel(Protocol):
    """Where a probe question goes and where the comprehension score comes back from."""

    name: str
    label: str
    mock: bool

    async def ask(self, question: "Question") -> "TutorResult": ...


@dataclass
class Question:
    id: str
    finding_key: str
    group_id: str
    category: str
    fix_pattern: str
    file_path: str | None
    line: int | None
    text: str
    code: str  # the student's own code, redacted, with line numbers; "" when it could not be read
    code_source: str  # "ast" | "text-search" | "window" | "metadata-only"


@dataclass
class TutorResult:
    score: float  # 0..1 comprehension
    label: str
    mock: bool
    answer_summary: str


class MockTutor:
    """A stand-in for the real Tutor agent. It does NOT read or grade any answer: the score is simulated, deterministic for
    a finding (so runs can be compared), or fixed per finding key with `scores`."""

    name = "mock-tutor"
    label = "MOCK TUTOR (simulated; no student answered and nothing was graded)"
    mock = True

    def __init__(self, scores: dict[str, float] | None = None, default: float | None = None):
        self._scores, self._default = scores or {}, default

    async def ask(self, question: Question) -> TutorResult:
        if question.finding_key in self._scores:
            score = self._scores[question.finding_key]
        elif self._default is not None:
            score = self._default
        else:  # spread over 0.30 .. 0.95 so a demo shows both decisions
            score = 0.30 + int(sha256(question.finding_key.encode()).hexdigest()[:6], 16) % 66 / 100
        return TutorResult(round(score, 2), self.label, True, "(simulated answer: none was given)")


def threshold_from_env() -> float:
    try:
        value = float(os.environ.get("SECURITY_ASSISTANT_COMPREHENSION_THRESHOLD", DEFAULT_THRESHOLD))
    except ValueError:
        return DEFAULT_THRESHOLD
    return value if 0.0 <= value <= 1.0 else DEFAULT_THRESHOLD


def decide(score: float, threshold: float) -> str:
    """A finding closes only at or above the threshold."""
    return "closed" if score >= threshold else "open"


def leaks_fix(text: str) -> str | None:
    m = _LEAKS.search(text)
    return m.group(0) if m else None


# ---- extracting the student's code -------------------------------------------------------------------------------------------
@dataclass
class Excerpt:
    name: str | None  # enclosing function or method
    params: list[str]
    start: int
    lines: list[str]
    how: str


def _python_excerpt(source: str, line: int) -> Excerpt | None:
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return None
    best = None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.lineno <= line <= (node.end_lineno or node.lineno):
            if best is None or node.lineno >= best.lineno:
                best = node
    if best is None:
        return None
    params = [a.arg for a in [*best.args.posonlyargs, *best.args.args, *best.args.kwonlyargs] if a.arg not in ("self", "cls")]
    first = min([best.lineno, *(d.lineno for d in best.decorator_list)])
    return Excerpt(best.name, params, first, source.splitlines()[first - 1:best.end_lineno], "ast")


_DECL = re.compile(
    r"(?:function\s+(?P<a>\w+)\s*\((?P<pa>[^)]*)\))"
    r"|(?:(?:const|let|var)\s+(?P<b>\w+)\s*=\s*(?:async\s*)?\((?P<pb>[^)]*)\)\s*=>)"
    r"|(?:\b(?:app|router)\.(?:get|post|put|delete|patch|use)\(\s*['\"`](?P<c>[^'\"`]+)['\"`])"
    r"|(?:(?:public|private|protected)\s+(?:static\s+)?[\w<>\[\], ?]+\s+(?P<d>\w+)\s*\((?P<pd>[^)]*)\)\s*(?:throws [\w, .]+)?\s*\{?)")


def _braces_excerpt(lines: list[str], line: int) -> Excerpt | None:
    for i in range(line - 1, max(-1, line - 41), -1):
        m = _DECL.search(lines[i])
        if not m:
            continue
        name = m.group("a") or m.group("b") or m.group("c") or m.group("d")
        raw = m.group("pa") or m.group("pb") or m.group("pd") or ""
        params = [p.strip().split()[-1].split(":")[0].strip("?") for p in raw.split(",") if p.strip()]
        depth, seen, end = 0, False, min(len(lines), i + 60)
        for j in range(i, min(len(lines), i + 60)):
            depth += lines[j].count("{") - lines[j].count("}")
            seen = seen or "{" in lines[j]
            if seen and depth <= 0:
                end = j + 1
                break
        if end >= line:
            return Excerpt(name, params, i + 1, lines[i:end], "text-search")
        break
    return None


def extract(repo: Path | None, file_path: str | None, line: int | None) -> Excerpt | None:
    path = _safe_file(Path(repo), file_path) if repo is not None else None
    if path is None or not line:
        return None
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    if not 1 <= line <= len(lines):
        return None
    found = _python_excerpt(text, line) if path.suffix == ".py" else _braces_excerpt(lines, line) if path.suffix in (
        ".java", ".kt", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs") else None
    if found is not None:
        return found
    lo, hi = max(1, line - WINDOW), min(len(lines), line + WINDOW)
    return Excerpt(None, [], lo, lines[lo - 1:hi], "window")


def render_excerpt(ex: Excerpt, target: int, pii: PIIRedactor) -> str:
    lines, start = ex.lines, ex.start
    if len(lines) > MAX_EXCERPT_LINES:  # keep the part around the flagged line
        lo = max(0, min(target - start - MAX_EXCERPT_LINES // 2, len(lines) - MAX_EXCERPT_LINES))
        lines, start = lines[lo:lo + MAX_EXCERPT_LINES], start + lo
    numbered = "\n".join(f"{'>>' if start + i == target else '  '} {start + i:>4}  {text}" for i, text in enumerate(lines))
    return redact_text(pii.redact_numbered(numbered))


# ---- the questions ------------------------------------------------------------------------------------------------------------
def _names_on_line(ex: Excerpt | None, line: int) -> list[str]:
    """Parameters of the enclosing function that are used on the flagged line: what outside input reaches it."""
    if ex is None or not 0 <= line - ex.start < len(ex.lines):
        return []
    text = ex.lines[line - ex.start]
    return [p for p in ex.params if re.search(rf"\b{re.escape(p)}\b", text)]


def _secret_name(ex: Excerpt | None, line: int) -> str | None:
    if ex is None or not 0 <= line - ex.start < len(ex.lines):
        return None
    m = re.match(r"\s*(?:(?:export|const|let|var|final|static|private|public)\s+)*(?:[\w<>\[\]]+\s+)?([A-Za-z_]\w*)\s*[:=]", ex.lines[line - ex.start])
    return m.group(1) if m else None


def _ask(fix_pattern: str, where: str, fn: str, inputs: str, secret: str | None, package: str | None) -> str:
    """Question templates. Each one asks what the code does with outside input or who can reach it; none says what to change."""
    if fix_pattern in ("ownership-check", "deny-by-default", "add-spring-security"):
        return (f"In {fn} ({where}), {inputs} comes from the request. Suppose two different customers, A and B, are both "
                "logged in and A types B's identifier into the address. Walk through the code line by line: what does it "
                "return, and which line, if any, tells A apart from B?")
    if fix_pattern == "sql-injection":
        return (f"On {where}, the text of a database query is put together in {fn} using {inputs}. If that value contained a "
                "quote character followed by more SQL, what exactly would the database receive? Which part of the statement "
                "could the person typing it change?")
    if fix_pattern == "command-injection":
        return (f"{fn} ({where}) builds an operating-system command with {inputs}. If that value contained a semicolon "
                "and another command, what would run, and with which permissions?")
    if fix_pattern == "xss":
        return (f"In {fn} ({where}), {inputs} ends up in the page. If it contained a script tag, whose browser would run it, "
                "and what could that script read?")
    if fix_pattern == "path-traversal":
        return (f"{fn} ({where}) chooses a file from {inputs}. If the value contained ../ segments, which files could "
                "be reached, and how would you notice from the code?")
    if fix_pattern == "weak-password-hash":
        return (f"{where} stores a value derived from the password. If an attacker got a copy of the stored values and could "
                "try a billion guesses per second, what could they learn, and how long would it take? Explain your reasoning "
                "about the function used here.")
    if fix_pattern == "token-expiry":
        return (f"A token is created at {where}. Suppose one is stolen on Monday. Using only this code, until when can the "
                "thief use it, and who or what could stop them?")
    if fix_pattern in ("cookie-flags", "csrf-protection"):
        return (f"{where} configures how the browser handles the session. Describe an attack by a malicious web page or a "
                "person on the same Wi-Fi that this configuration allows. What would the victim see?")
    if fix_pattern == "login-rate-limit":
        return (f"{fn} ({where}) accepts login attempts. How many passwords per minute could one person try against one "
                "account with this code, and what in the code would slow them down?")
    if fix_pattern in ("debug-and-actuator", "default-password"):
        return (f"{where} sets how the application starts. If this ran on the public internet, what could a stranger see or "
                "do without logging in, and why?")
    if fix_pattern == "hardcoded-secret":
        name = f"`{secret}`" if secret else "the value on that line"
        return (f"{name} ({where}) is written in the code. Who can read it today, including people who only have an old copy "
                "of the repository, and what could they do with it?")
    if fix_pattern == "dependency-upgrade":
        return (f"The project depends on {package or 'a package'} ({where}). Which of your features call into it, and what "
                "would an attacker gain if that package had a flaw that runs code when it reads their input?")
    if fix_pattern.startswith("workflow"):
        return (f"{where} defines an automated workflow. Who can start it, which secrets or token permissions does it have "
                "while it runs, and what could a stranger's pull request make it do?")
    return (f"Look at {where} in {fn}. Which values here can an outsider control, and what is the worst thing that "
            "could happen with them?")


def build_question(group: dict, repo: Path | None, pii: PIIRedactor | None = None) -> Question:
    """One probe question for one confirmed group of `interpreted.json`."""
    pii = pii if pii is not None else PIIRedactor.from_env()
    rep = group["representative"]
    file_path, line = rep["file_path"], rep["line"]
    ex = extract(repo, file_path, line)
    where = f"{file_path}:{line}" if file_path and line else (file_path or group.get("package") or "the finding")
    where = pii.redact_path(where)
    fn = f"`{ex.name}`" if ex and ex.name else "this code"
    names = _names_on_line(ex, line or 0)
    shown = names or (ex.params[:2] if ex else [])
    inputs = ", ".join(f"`{n}`" for n in shown) if shown else "a value"
    text = _ask(rep.get("fix_pattern") or "", where, fn, inputs, _secret_name(ex, line or 0), group.get("package"))
    # the wording is checked with neutral stand-ins, so a student's own file or variable names cannot trip the guard
    leaked = leaks_fix(_ask(rep.get("fix_pattern") or "", "X", "X", "X", None, None))
    if leaked:  # a template must never give the answer; refuse to ship one that does
        raise ValueError(f"question for {rep.get('fix_pattern')} leaks the fix: {leaked!r}")
    code = render_excerpt(ex, line or 0, pii) if ex else ""
    return Question(id=f"Q-{rep['finding_key']}", finding_key=rep["finding_key"], group_id=group["group_id"],
                    category=rep["category"], fix_pattern=rep.get("fix_pattern") or "", file_path=file_path, line=line,
                    text=redact_text(text), code=code, code_source=ex.how if ex else "metadata-only")


async def generate(doc: dict, repo: Path | None, tutor: TutorChannel, threshold: float,
                   pii: PIIRedactor | None = None) -> dict:
    pii = pii if pii is not None else PIIRedactor.from_env()
    items = []
    for g in doc["groups"]:
        if g["result"]["status"] != "confirmed":
            continue
        q = build_question(g, repo, pii)
        result = await tutor.ask(q)
        items.append({"question": asdict(q), "tutor_result": asdict(result), "threshold": threshold,
                      "decision": decide(result.score, threshold)})
    closed = sum(i["decision"] == "closed" for i in items)
    return {"meta": {"threshold": threshold, "tutor": tutor.name, "tutor_label": tutor.label, "tutor_is_mock": tutor.mock,
                     "closed_means": "the student showed they understand the problem; not that the code was fixed"},
            "summary": {"questions": len(items), "closed": closed, "open": len(items) - closed},
            "questions": items}


# ---- output -------------------------------------------------------------------------------------------------------------------------
def _cell(text) -> str:
    return " ".join(str(text).split()).replace("|", "\\|")


def render_section(doc: dict) -> str:
    m, s = doc["meta"], doc["summary"]
    M = [SECTION_MARK, "## Probe questions and comprehension check", "",
         f"> **{m['tutor_label']}**" if m["tutor_is_mock"] else f"> Tutor: {m['tutor_label']}", ">",
         "> One question per confirmed finding, built from the student's own code; none states the fix. A finding is closed only "
         f"when the comprehension score reaches the threshold ({m['threshold']:g}). Closed means {m['closed_means']}.", "",
         f"- **Questions:** {s['questions']}; closed {s['closed']}, still open {s['open']}", ""]
    for i in doc["questions"]:
        q, r = i["question"], i["tutor_result"]
        where = (q["file_path"] or "-") + (f":{q['line']}" if q["line"] else "")
        M += [f"### {q['group_id']} {q['category']} {_cell(where)}", "", q["text"], ""]
        if q["code"]:
            M += ["```", q["code"], "```", ""]
        M += [f"Score {r['score']:.2f} (threshold {i['threshold']:g}) -> **{i['decision']}**"
              + (" - simulated by the mock Tutor" if r["mock"] else ""), ""]
    return "\n".join(M) + "\n"


async def main(argv: list[str] | None = None, tutor: TutorChannel | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("interpreted", type=Path)
    ap.add_argument("repo", type=Path)
    ap.add_argument("--threshold", type=float)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args(argv)
    try:
        doc = json.loads(args.interpreted.read_text(encoding="utf-8"))
        doc["groups"]
    except (OSError, ValueError, KeyError) as exc:
        print(f"cannot read the input: {exc}", file=sys.stderr)
        return 3
    threshold = args.threshold if args.threshold is not None else threshold_from_env()
    if not 0.0 <= threshold <= 1.0 or not args.repo.is_dir():
        print("the threshold must be between 0 and 1 and the repo must be a folder", file=sys.stderr)
        return 3
    out = args.out or args.interpreted.parent
    out.mkdir(parents=True, exist_ok=True)
    result = await generate(doc, args.repo, tutor or MockTutor(), threshold)
    (out / "questions.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    upsert_section(out / "report.md", SECTION_MARK, render_section(result))
    print(result["meta"]["tutor_label"])
    for i in result["questions"]:
        print(f"{i['question']['group_id']}  score {i['tutor_result']['score']:.2f}  threshold {threshold:g}  -> {i['decision']}")
    s = result["summary"]
    print(f"{s['questions']} question(s): {s['closed']} closed, {s['open']} open. Wrote {out / 'questions.json'}")
    return 0


if __name__ == "__main__":
    import asyncio

    sys.exit(asyncio.run(main()))
