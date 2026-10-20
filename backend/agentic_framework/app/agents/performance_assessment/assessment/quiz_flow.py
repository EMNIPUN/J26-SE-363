"""The Code Ownership quiz as a flow that never blocks a graph thread.

    issue(...)      the final run creates the student's quiz for the sprint (one per student and sprint) from files the student wrote
    factor_for(...) the quiz's current state as a factor result: pending until answered, a real 0 after both windows, scored (and capped in the second window) once answered
    score_answer    the Code Ownership package rates the answer; the cap and the timeout policy come from com_agent/config/quiz_timeout_settings.yaml (48 h + 48 h, cap 0.50)

The student answers through the API (``submit_answer``); the answer, an expired window or a lecturer's decision re-fuses that one student (runner.refuse_student). Until then the student's mark
is provisional and Code Ownership is listed as pending, so a student who is slow to answer never holds up a team run.
"""
from datetime import datetime, timedelta, timezone

from app.agents.performance_assessment.assessment.factors import _as_result
from app.agents.performance_assessment.com_agent import factor_bridge
from app.agents.performance_assessment.com_agent.config.settings_loader import settings

MAX_FILES = 15
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


async def issue(store, ws, repo_url, rev, team_ref, sprint_id, student_id, evidence, run_id, token=None, now=None):
    """The student's quiz for this sprint: the existing one, or a new one. ``None`` when no file has code worth asking about."""
    existing = store.get_quiz(team_ref, sprint_id, student_id)
    if existing:
        return existing
    if not rev:
        return None
    files = student_files(ws, repo_url, rev, evidence, token)
    quiz = await factor_bridge.generate_quiz_via_bridge({"files": files, "student_id": student_id, "sprint_id": sprint_id}) if files else None
    if not quiz:
        return None
    cfg = settings.quiz_timeout
    meta = {**(quiz.get("ast_metadata") or {}), "question_type": quiz.get("question_type"), "reference_criteria": quiz.get("reference_criteria"), "facts": quiz.get("facts"), "warnings": quiz.get("warnings", []),
            "quiz_version": quiz.get("version")}
    return store.create_quiz(team_ref, sprint_id, student_id, question=quiz["question"], snippet=quiz["code_snippet"], file_path=quiz["file_path"], line_range=quiz["line_range"], meta=meta,
                             deadline_at=(now or _now()) + timedelta(hours=cfg.time_window_hours), run_id=run_id)


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


async def factor_for(store, quiz: dict | None) -> dict:
    """The Code Ownership result for a student, from the quiz's state. Scored once; the result is kept with the quiz."""
    if quiz is None:
        return not_available("no function worth asking about was found in the student's code, or the code is not available")
    if quiz["status"] == "answered":
        if not quiz.get("result"):
            quiz = store.set_quiz_result(quiz["id"], await score_answer(quiz)) or quiz
        return quiz["result"]
    if quiz["status"] == "expired":
        return {**pending(""), "factor": "code_ownership", "score": 0.0, "status": "completed", "interval": [0.0, 0.0], "provisional": False,
                "warnings": [f"no answer within the {settings.quiz_timeout.time_window_hours:.0f} h and {settings.quiz_timeout.extra_time_hours:.0f} h windows: counted as 0 (the course policy)"],
                "features": {"ko_raw_score": 0.0, "timeout": True}}
    return pending("the student has not answered the code question yet" + (" (second window)" if quiz["status"] == "extended" else ""))
