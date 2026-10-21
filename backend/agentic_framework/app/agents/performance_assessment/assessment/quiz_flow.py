"""The Code Ownership quiz as a flow that never blocks a graph thread.

    issue(...)      the final run creates the student's quiz for the sprint (one per student and sprint) from files the student wrote
    factor_for(...) the quiz's current state as a factor result: pending until answered, a real 0 after both windows, scored (and capped in the second window) once answered
    score_answer    the Code Ownership package rates the answer; the cap and the timeout policy come from com_agent/config/quiz_timeout_settings.yaml (48 h + 48 h, cap 0.50)

The student answers through the API (``submit_answer``); the answer, an expired window or a lecturer's decision re-fuses that one student (runner.refuse_student). Until then the student's mark
is provisional and Code Ownership is listed as pending, so a student who is slow to answer never holds up a team run.
"""
import asyncio
import json
import re
from datetime import datetime, timedelta, timezone

from app.agents.performance_assessment.assessment.factors import _as_result
from app.agents.performance_assessment.com_agent import factor_bridge
from app.agents.performance_assessment.com_agent.config.settings_loader import settings

MAX_FILES = 25
MAX_FILE_CHARS = 60_000


def _now():
    return datetime.now(timezone.utc)


def pending(reason):
    return {"factor": "code_ownership", "score": None, "status": "pending", "interval": None, "warnings": [reason], "versions": {}, "features": {}, "provisional": True, "removed": {}, "tasks": None, "model": None}


def not_available(reason):
    return {**pending(reason), "status": "not_available", "provisional": False}


def student_files(ws, repo_url, rev, evidence, token=None):
    """Source files the student added lines to in the sprint, as ``[{"path", "text"}]`` read from the repository at the sprint's last revision (read-only)."""
    weight = {}
    for c in evidence.get("commits", []):
        for f in c.get("files", []):
            if f.get("kind") in ("code", "test") and f.get("added", 0) > 0:
                weight[f["path"]] = weight.get(f["path"], 0) + f["added"]
    out = []
    for path, _n in sorted(weight.items(), key=lambda kv: -kv[1])[:MAX_FILES]:
        try:
            text = ws.read(repo_url, "show", f"{rev}:{path}", token=token)
        except Exception:  # the file may have been deleted again
            continue
        if text and len(text) <= MAX_FILE_CHARS:
            out.append({"path": path, "text": text})
    return out


QUESTIONS_PER_STUDENT = 10          # at least this many questions a student gets when the code they wrote allows it
CURRENT_VERSION = "ko_quiz/2"


def _valid_question(text):
    return isinstance(text, str) and 25 <= len(text.strip()) <= 360 and "```" not in text and "<" not in text


def refine_questions(llm, quizzes, batch=5):
    """The agent writes the question for each snippet that only has the generic template (code that is not Python): one that names things in the snippet and asks for a different kind of understanding each time.
    A reply that is missing, malformed or not about the snippet leaves the template question in place. Python questions are built from the syntax tree and are not touched (the answer scorer was trained on them)."""
    if llm is None:
        return quizzes
    todo = [q for q in quizzes if (q.get("ast_metadata") or {}).get("language") != "python"]
    kinds = ["what it does and why", "what is returned or changed when the input is unusual or empty", "what could go wrong, and how the code copes", "why it is written this way and not another way", "what is true about the result after it runs"]
    for start in range(0, len(todo), batch):
        group = todo[start:start + batch]
        items = [{"id": i, "file": q["file_path"], "code": q["code_snippet"][:1800], "ask_about": kinds[(start + i) % len(kinds)]} for i, q in enumerate(group)]
        try:
            reply = llm.chat([{"role": "system", "content": "You write one oral-exam question for each code snippet, to check that its author understands it. The question must refer to specific names, values or steps in that snippet, "
                                                           "ask for an explanation in a few sentences (not yes or no), follow the 'ask_about' hint, and not give the answer away. Also give 2 or 3 short points a correct answer would cover. "
                                                           "Reply with JSON {\"questions\": [{\"id\": 0, \"question\": \"...\", \"criteria\": [\"...\", \"...\"]}]}."},
                              {"role": "user", "content": json.dumps(items)}], max_tokens=1800, temperature=0.3, tag="quiz_questions", json_mode=True)
            rows = json.loads(getattr(reply, "text", "") or "{}").get("questions", [])
        except Exception:
            continue
        for row in rows if isinstance(rows, list) else []:
            if not isinstance(row, dict) or not isinstance(row.get("id"), int) or not 0 <= row["id"] < len(group) or not _valid_question(row.get("question")):
                continue
            q = group[row["id"]]
            names = {w for w in re.findall(r"[A-Za-z_$][\w$]{3,}", q["code_snippet"])}
            if not any(n in row["question"] for n in names):
                continue  # not about this code
            q["question"] = row["question"].strip()
            crit = [c.strip() for c in row.get("criteria", []) if isinstance(c, str) and c.strip()][:3]
            if crit:
                q["reference_criteria"] = crit
            q["question_type"] = "purpose"
            q["generated_by"] = getattr(llm, "model", None)
    return quizzes


async def issue(store, ws, repo_url, rev, team_ref, sprint_id, student_id, evidence, run_id, token=None, now=None, llm=None):
    """The student's quiz for this sprint: the existing one, or a new one. ``None`` when no file has code worth asking about.
    A batch nobody has touched that was made by an older generator is replaced; one with any answer is never changed."""
    existing = await asyncio.to_thread(store.list_quizzes, team_ref, sprint_id, student_id)
    if existing:
        stale = all(q["status"] == "open" for q in existing) and any((q.get("meta") or {}).get("quiz_version") != CURRENT_VERSION for q in existing)
        if not stale or not await asyncio.to_thread(store.delete_open_quizzes, team_ref, sprint_id, student_id):
            return existing
    if not rev:
        return None
    files = await asyncio.to_thread(student_files, ws, repo_url, rev, evidence, token)
    team = await asyncio.to_thread(store.get_tracked_team, team_ref)
    count = max(QUESTIONS_PER_STUDENT, int(((team or {}).get("config") or {}).get("questions_per_student") or QUESTIONS_PER_STUDENT))
    quizzes = await factor_bridge.generate_quizzes_via_bridge({"files": files, "student_id": student_id, "sprint_id": sprint_id, "count": count}) if files else []
    if not quizzes:
        return None
    quizzes = await asyncio.to_thread(refine_questions, llm, quizzes)
    cfg = settings.quiz_timeout
    out = []
    batch_id = f"{team_ref}:{sprint_id}:{student_id}:{run_id}"
    for n, quiz in enumerate(quizzes, 1):
        meta = {**(quiz.get("ast_metadata") or {}), "question_type": quiz.get("question_type"), "reference_criteria": quiz.get("reference_criteria"), "facts": quiz.get("facts"), "warnings": quiz.get("warnings", []), "quiz_version": quiz.get("version"), "generated_by": quiz.get("generated_by")}
        out.append(await asyncio.to_thread(store.create_quiz, team_ref, sprint_id, student_id, n=n, of=len(quizzes), type=quiz.get("question_type", "explain_behaviour"), batch_id=batch_id, question=quiz["question"], snippet=quiz["code_snippet"], file_path=quiz["file_path"], line_range=quiz["line_range"], meta=meta, deadline_at=(now or _now()) + timedelta(hours=cfg.time_window_hours), run_id=run_id))
    return out


async def score_answer(quiz: dict) -> dict:
    """Rate an answered quiz with the Code Ownership package; an answer given in the second window cannot score above the configured ceiling."""
    meta = quiz.get("meta") or {}
    payload = {"student_response": quiz["answer"], "generated_question": quiz["question"], "code_snippet": quiz["snippet"], "file_path": quiz.get("file_path"), "ast_metadata": meta, "facts": meta.get("facts"),
               "is_extension_period": bool(quiz.get("in_extension"))}
    out = _as_result("code_ownership", await factor_bridge.evaluate_factor("code_ownership", payload=payload, context={}))
    if out["status"] == "completed" and quiz.get("in_extension"):
        ceiling = settings.quiz_timeout.capped_score_ceiling
        if out["score"] > ceiling:
            out["warnings"].append(f"answered in the second window: score capped at {ceiling:.2f} (was {out['score']:.2f})")
            out["score"] = ceiling
            out["interval"] = None if out["interval"] is None else [min(out["interval"][0], ceiling), ceiling]
    return out


async def factor_for(store, quiz: dict | list[dict] | None) -> dict:
    """The Code Ownership result for a student, from the quiz's state. Scored once; the result is kept with the quiz."""
    quizzes = quiz if isinstance(quiz, list) else ([quiz] if quiz else [])
    if not quizzes:
        return not_available("no function worth asking about was found in the student's code, or the code is not available")
    scores, warnings, open_count = [], [], 0
    for q in quizzes:
        if q["status"] == "answered":
            result = q.get("result")
            if not result:
                result = await score_answer(q)
                await asyncio.to_thread(store.set_quiz_result, q["id"], result)
            scores.append(result.get("score", 0.0) or 0.0)
            warnings.extend(result.get("warnings", []))
        elif q["status"] == "expired":
            scores.append(0.0)
        else:
            open_count += 1
    if open_count:
        return pending(f"{open_count} code question(s) still awaiting an answer")
    score = sum(scores) / len(scores) if scores else 0.0
    return {**pending(""), "factor": "code_ownership", "score": score, "status": "completed", "interval": None, "provisional": False,
            "warnings": warnings, "features": {"ko_raw_score": score, "quiz_count": len(quizzes), "answered_count": sum(q["status"] == "answered" for q in quizzes)}, "versions": {}}
