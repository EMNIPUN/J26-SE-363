"""Probe questions for confirmed findings, and a clearly labelled MOCK Tutor that scores the answer.

    python -m app.agents.security_assistant.questions <interpreted.json> <repo folder> [--threshold 0.7] [--out DIR]

The question agent is a bounded loop: GOAL a finding closed by the Tutor's comprehension score; STATE the attempts and scores of the
finding; ACTIONS (fixed, validated in code) ask_question, ask_followup, close_finding, escalate_to_lecturer. A score below the threshold
leads to a follow-up from a different angle with a higher hint level (it narrows what to look at, and never states the fix), up to a
limit (`max_retries` follow-ups, default 2, so 3 attempts); then the finding is escalated to lecturer review. Every decision is an audit
line and a row of the report's decision trail. See agent_loop.py for what a policy may and may not do.

One finding group (a package with several advisories is one group) gets one question to start with. The question is
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

from app.agents.security_assistant.agent_loop import Action, DecisionTrail, LoopConfig, Policy, RulePolicy, render_trail, select
from app.agents.security_assistant.interpreter.evidence import _safe_file
from app.agents.security_assistant.interpreter.redaction import redact_text
from app.agents.security_assistant.pii import PIIRedactor
from app.agents.security_assistant.report import upsert_section

SECTION_MARK = "<!-- probe-questions -->"
TRAIL_MARK = "<!-- decision-trail-questions -->"
QUESTION_ACTIONS = ("ask_question", "ask_followup", "close_finding", "escalate_to_lecturer")
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
    attempt: int = 1
    hint_level: int = 0  # 0 scenario, 1 locate the data and the line, 2 answer in three parts, 3 follow one example value through the code


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

    def __init__(self, scores: dict[str, float | list[float]] | None = None, default: float | None = None):
        """`scores[finding_key]` is one score for every attempt or a list with one score per attempt (the last one repeats)."""
        self._scores, self._default = scores or {}, default

    async def ask(self, question: Question) -> TutorResult:
        if question.finding_key in self._scores:
            given = self._scores[question.finding_key]
            score = given[min(question.attempt, len(given)) - 1] if isinstance(given, (list, tuple)) else given
        elif self._default is not None:
            score = self._default
        else:  # simulated: a base per finding, a little higher with every hint level, so a demo shows closes after follow-ups
            base = 0.30 + int(sha256(question.finding_key.encode()).hexdigest()[:6], 16) % 41 / 100
            score = min(0.95, base + 0.15 * question.hint_level)
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


def _followup(fix_pattern: str, level: int, where: str, fn: str, inputs: str, secret: str | None, package: str | None) -> str:
    """Follow-up questions, each from a different angle than the first. Level 1 narrows WHAT to look at (the data and the line), level 2
    asks for the answer in three parts, level 3 asks to follow one concrete value through the code. None of them says what to change."""
    if level >= 3:
        return (f"Pick one concrete value that someone outside could send to {fn} ({where}) and follow it through the code line by line, "
                "writing down what each line does with it, until you reach the result. What is that result?")
    if level == 2:
        return (f"Answer in three short parts about {where}: (1) which value does an outsider control, (2) which line uses it first, "
                "(3) what is the worst thing that could happen with a value they choose, and why does nothing in this code get in the way?")
    if fix_pattern in ("ownership-check", "deny-by-default", "add-spring-security"):
        return (f"Start from {inputs} in {fn} ({where}). Where does its value come from, which line first uses it to pick the data that is "
                "returned, and what does the code know about who is asking at that line?")
    if fix_pattern == "sql-injection":
        return (f"Find the line in {fn} where the query text is assembled ({where}). Which pieces come from {inputs} and which are text you typed in the code? "
                "Write the final text the database would receive for the input O'Brien, and then for the input ' OR '1'='1.")
    if fix_pattern == "command-injection":
        return (f"Find where the command string is assembled in {fn} ({where}). Which parts come from {inputs}? Write the exact command that "
                "would run if the value were  a; id")
    if fix_pattern == "xss":
        return (f"Find where {inputs} is placed into the page in {fn} ({where}). Write the exact HTML the browser would receive for the value "
                "<b>hi</b> and say what the browser does with it.")
    if fix_pattern == "path-traversal":
        return (f"Find where the file name is built from {inputs} ({where}). Write the exact path that would be opened for the value "
                "../secret.txt and say which folder that path starts from.")
    if fix_pattern == "weak-password-hash":
        return (f"Name the function used at {where}. What do you know about how fast it is, and whether two identical passwords give the "
                "same stored value? What does that mean for someone holding a copy of the stored values?")
    if fix_pattern == "token-expiry":
        return (f"List every claim or setting that the token at {where} carries. Does any of them limit how long it keeps working? "
                "What would you expect to find in the token if a limit existed?")
    if fix_pattern in ("cookie-flags", "csrf-protection"):
        return (f"Write down each browser-side setting at {where} with its name and value. For each one, what could a script on the page or "
                "someone watching the network do because of that setting?")
    if fix_pattern == "login-rate-limit":
        return (f"Count the lines in {fn} ({where}) between a request arriving and the password being compared. Is there anything there that "
                "remembers earlier attempts from the same person?")
    if fix_pattern in ("debug-and-actuator", "default-password"):
        return (f"List everything that {where} turns on. For each item, who could reach it from outside the machine, and what would they see?")
    if fix_pattern == "hardcoded-secret":
        name = f"`{secret}`" if secret else "the value on that line"
        return (f"Besides this file, where else could the value of {name} ({where}) be found: other branches, old commits, copies of the "
                "repository? Who has those copies?")
    if fix_pattern == "dependency-upgrade":
        return (f"Open {where} and find the exact version of {package or 'the package'}. Which of its functions does your code call, and with "
                "data that comes from where?")
    if fix_pattern.startswith("workflow"):
        return (f"List the events that start the workflow at {where} and the secrets it can read. Who can trigger each event?")
    return (f"Name the one value near {where} that an outsider controls and trace it line by line to the place where it could do the most harm.")


def question_text(fix_pattern: str, hint_level: int, where: str, fn: str, inputs: str, secret: str | None, package: str | None) -> str:
    if hint_level <= 0:
        return _ask(fix_pattern, where, fn, inputs, secret, package)
    return _followup(fix_pattern, hint_level, where, fn, inputs, secret, package)


def build_question(group: dict, repo: Path | None, pii: PIIRedactor | None = None, hint_level: int = 0, attempt: int = 1) -> Question:
    """One probe question for one confirmed group of `interpreted.json`. `hint_level` 0 is the first question; higher levels are the
    follow-ups of the question agent (a different angle, a narrower focus, never the fix)."""
    pii = pii if pii is not None else PIIRedactor.from_env(repo)
    rep = group["representative"]
    file_path, line = rep["file_path"], rep["line"]
    ex = extract(repo, file_path, line)
    where = f"{file_path}:{line}" if file_path and line else (file_path or group.get("package") or "the finding")
    where = pii.redact_path(where)
    fn = f"`{ex.name}`" if ex and ex.name else "this code"
    names = _names_on_line(ex, line or 0)
    shown = names or (ex.params[:2] if ex else [])
    inputs = ", ".join(f"`{n}`" for n in shown) if shown else "a value"
    text = question_text(rep.get("fix_pattern") or "", hint_level, where, fn, inputs, _secret_name(ex, line or 0), group.get("package"))
    # the wording is checked with neutral stand-ins, so a student's own file or variable names cannot trip the guard
    leaked = leaks_fix(question_text(rep.get("fix_pattern") or "", hint_level, "X", "X", "X", None, None))
    if leaked:  # a template must never give the answer; refuse to ship one that does
        raise ValueError(f"question for {rep.get('fix_pattern')} leaks the fix: {leaked!r}")
    code = render_excerpt(ex, line or 0, pii) if ex else ""
    return Question(id=f"Q-{rep['finding_key']}" + (f"-a{attempt}" if attempt > 1 else ""), finding_key=rep["finding_key"],
                    group_id=group["group_id"], category=rep["category"], fix_pattern=rep.get("fix_pattern") or "", file_path=file_path,
                    line=line, text=redact_text(text), code=code, code_source=ex.how if ex else "metadata-only", attempt=attempt,
                    hint_level=hint_level)


def question_options(attempts: list[dict], threshold: float, cfg: LoopConfig) -> list[Action]:
    """The actions that are valid for one finding in its current state. Closing is only valid at or above the threshold; a follow-up only
    while follow-ups are left; escalation whenever the finding is not closed. The first option is what the rule policy takes."""
    if not attempts:
        return [Action("ask_question", "level 0", "the first question, from the scenario angle")]
    last = attempts[-1]
    if last["score"] >= threshold:
        return [Action("close_finding", why=f"score {last['score']:.2f} reached the threshold {threshold:g} on attempt {last['attempt']}")]
    opts = []
    if len(attempts) <= cfg.max_retries:  # follow-ups used so far = attempts - 1
        level = len(attempts)
        opts.append(Action("ask_followup", f"level {level}", f"score {last['score']:.2f} is below {threshold:g}; a follow-up from a different "
                                                              f"angle (hint level {level}); it never states the fix"))
    opts.append(Action("escalate_to_lecturer", why=f"{len(attempts)} attempt(s), last score {last['score']:.2f} below {threshold:g}"
                                                   + ("" if opts else f"; the limit of {cfg.max_retries} follow-up(s) is reached")))
    return opts


async def generate(doc: dict, repo: Path | None, tutor: TutorChannel, threshold: float, pii: PIIRedactor | None = None, *,
                   config: LoopConfig | None = None, policy: Policy | None = None, audit=None) -> dict:
    """Run the question loop for every confirmed group. Returns the questions document (see render_section)."""
    pii = pii if pii is not None else PIIRedactor.from_env(repo)
    cfg = config or LoopConfig.from_env("QUESTION", max_steps=200, max_retries=2)
    policy, rules = policy or RulePolicy(), RulePolicy()
    trail = DecisionTrail("question agent", audit)
    items, steps = [], 0
    for g in doc["groups"]:
        if g["result"]["status"] != "confirmed":
            continue
        attempts: list[dict] = []
        status, escalation = "open", None
        last_q = last_r = None
        while status == "open":
            if steps >= cfg.max_steps:  # the budget is spent: the finding goes to a person, with the reason
                status, escalation = "escalated", f"step budget spent ({cfg.max_steps} steps) before this finding was closed"
                trail.outcome(trail.record(steps + 1, "budget", {"attempts": len(attempts)}, [], Action("escalate_to_lecturer"), escalation,
                                           subject=g["group_id"]), "escalated")
                break
            options = question_options(attempts, threshold, cfg)
            state = {"finding": g["group_id"], "attempts": len(attempts), "scores": [a["score"] for a in attempts], "threshold": threshold,
                     "steps_used": steps, "max_steps": cfg.max_steps}
            action, reason, rejected = select(policy, rules, state, options)
            entry = trail.record(steps + 1, policy.name if rejected is None else f"{policy.name} -> rules", state, options, action, reason,
                                 rejected, subject=g["group_id"])
            steps += 1
            if action.name in ("ask_question", "ask_followup"):
                level = len(attempts)
                last_q = build_question(g, repo, pii, hint_level=level, attempt=len(attempts) + 1)
                last_r = await tutor.ask(last_q)
                attempts.append({"attempt": last_q.attempt, "hint_level": level, "question_id": last_q.id, "text": last_q.text,
                                 "score": last_r.score, "result": decide(last_r.score, threshold)})
                trail.outcome(entry, f"attempt {last_q.attempt}: score {last_r.score:.2f} -> {attempts[-1]['result']}")
            elif action.name == "close_finding":
                status = "closed"
                trail.outcome(entry, f"closed after {len(attempts)} attempt(s)")
            else:
                status, escalation = "escalated", reason
                trail.outcome(entry, "escalated to lecturer review")
        if last_q is None:  # escalated by the budget before the first question: build it so the lecturer sees what was to be asked
            last_q = build_question(g, repo, pii)
            last_r = TutorResult(0.0, tutor.label, tutor.mock, "(not asked: the step budget was spent)")
        items.append({"question": asdict(last_q), "tutor_result": asdict(last_r), "threshold": threshold, "decision": status,
                      "attempts": attempts, "escalation_reason": escalation,
                      "state": {"attempts_used": len(attempts), "status": status, "scores": [a["score"] for a in attempts]}})
    closed = sum(i["decision"] == "closed" for i in items)
    return {"meta": {"threshold": threshold, "tutor": tutor.name, "tutor_label": tutor.label, "tutor_is_mock": tutor.mock,
                     "max_followups": cfg.max_retries, "max_steps": cfg.max_steps, "policy": policy.name,
                     "closed_means": "the student showed they understand the problem; not that the code was fixed"},
            "summary": {"questions": len(items), "closed": closed, "escalated": len(items) - closed,
                        "attempts": sum(len(i["attempts"]) for i in items), "steps": steps},
            "questions": items, "decision_trail": trail.entries}


# ---- output -------------------------------------------------------------------------------------------------------------------------
def _cell(text) -> str:
    return " ".join(str(text).split()).replace("|", "\\|")


def render_section(doc: dict) -> str:
    m, s = doc["meta"], doc["summary"]
    M = [SECTION_MARK, "## Probe questions and comprehension check", "",
         f"> **{m['tutor_label']}**" if m["tutor_is_mock"] else f"> Tutor: {m['tutor_label']}", ">",
         "> One question per confirmed finding, built from the student's own code; none states the fix. A finding is closed only "
         f"when the comprehension score reaches the threshold ({m['threshold']:g}). Closed means {m['closed_means']}. "
         f"Below the threshold the agent asks a follow-up from a different angle (a higher hint level, never the fix), up to "
         f"{m['max_followups']} time(s), and then escalates the finding to lecturer review.", "",
         f"- **Findings:** {s['questions']}; closed {s['closed']}, escalated to lecturer review {s['escalated']}; "
         f"{s['attempts']} question(s) asked", ""]
    for i in doc["questions"]:
        q, r = i["question"], i["tutor_result"]
        where = (q["file_path"] or "-") + (f":{q['line']}" if q["line"] else "")
        M += [f"### {q['group_id']} {q['category']} {_cell(where)}", ""]
        for a in i["attempts"] or [{"attempt": 1, "hint_level": 0, "text": q["text"], "score": r["score"], "result": "not asked"}]:
            M += [f"**Attempt {a['attempt']} (hint level {a['hint_level']})** - {a['text']}", "",
                  f"Score {a['score']:.2f} (threshold {i['threshold']:g}) -> {a['result']}" + (" - simulated by the mock Tutor" if r["mock"] else ""), ""]
        if q["code"]:
            M += ["```", q["code"], "```", ""]
        M += [f"**Result: {i['decision']}**" + (f" - {i['escalation_reason']}" if i.get("escalation_reason") else ""), ""]
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
    from app.agents.security_assistant.governance import AUDIT_FILE, AuditLog

    result = await generate(doc, args.repo, tutor or MockTutor(), threshold, audit=AuditLog(out / AUDIT_FILE, append=True))
    (out / "questions.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    upsert_section(out / "report.md", SECTION_MARK, render_section(result))
    upsert_section(out / "report.md", TRAIL_MARK, f"{TRAIL_MARK}\n" + render_trail({"Question Generation": result["decision_trail"]}))
    print(result["meta"]["tutor_label"])
    for i in result["questions"]:
        scores = ", ".join(f"{a['score']:.2f}" for a in i["attempts"])
        print(f"{i['question']['group_id']}  scores {scores}  threshold {threshold:g}  -> {i['decision']}")
    s = result["summary"]
    print(f"{s['questions']} finding(s): {s['closed']} closed, {s['escalated']} escalated to lecturer review, {s['attempts']} question(s) asked. "
          f"Wrote {out / 'questions.json'}")
    return 0


if __name__ == "__main__":
    import asyncio

    sys.exit(asyncio.run(main()))
