"""
Performance Assessment Tasks — registered with the Procrastinate job queue.

Each function decorated with @app.task is a trigger point the server can enqueue.
The worker process (agentic_framework/worker.py) picks these up and runs them.

Queue: "performance"
Task names:
  - performance.assess_student
  - performance.parse_rubric
  - performance.generate_ownership_quiz
  - performance.ingest_git_commits
"""

import logging
from typing import Any

from procrastinate.exceptions import AlreadyEnqueued
from shared.queue import app

logger = logging.getLogger(__name__)


@app.task(name="performance.assess_student", queue="performance")
async def assess_student(payload: dict[str, Any]) -> dict[str, Any]:
    """Run the full LangGraph multi-factor evaluation + AHP fusion pipeline.

    Expected payload keys:
        student_id  (str)  — e.g. "IT21098765"
        batch_id    (str)  — e.g. "2026-REG-Y4S1"
        sprint_id   (str)  — e.g. "sprint-2"
        repo_url    (str)  — GitHub repository URL (optional)
        rubric_id   (str)  — assessment rubric identifier (optional)
    """
    # Heavy imports stay inside the function so the server process never loads them
    # from app.agents.performance_assessment.agent import run_evaluation
    logger.info(f"[performance] assess_student started: student={payload.get('student_id')}")

    # --- YOUR REAL AGENT CODE GOES HERE ---
    # result = await run_evaluation(
    #     student_id=payload["student_id"],
    #     sprint_id=payload.get("sprint_id", "sprint-1"),
    # )
    # return result

    return {
        "student_id": payload.get("student_id"),
        "sprint_id": payload.get("sprint_id"),
        "final_score": 87.5,
        "factor_scores": {"effort": 88.0, "consistency": 85.0, "code_ownership": 90.0},
    }


@app.task(name="performance.parse_rubric", queue="performance")
async def parse_rubric(payload: dict[str, Any]) -> dict[str, Any]:
    """Parse an uploaded rubric PDF/Word into structured criteria weights.

    Expected payload keys:
        project_id  (str)  — project identifier
        file_path   (str)  — path/URL to rubric file
    """
    logger.info(f"[performance] parse_rubric: project={payload.get('project_id')}")

    return {
        "project_id": payload.get("project_id"),
        "criteria": ["code_quality", "collaboration", "delivery", "problem_solving"],
        "weights": [0.30, 0.25, 0.25, 0.20],
    }


@app.task(name="performance.generate_ownership_quiz", queue="performance")
async def generate_ownership_quiz(payload: dict[str, Any]) -> dict[str, Any]:
    """Generate code-ownership quiz questions for a student's ambiguous commits.

    Expected payload keys:
        student_id   (str)  — student identifier
        commit_hash  (str)  — Git commit hash to quiz on
    """
    logger.info(f"[performance] generate_ownership_quiz: student={payload.get('student_id')}")

    return {
        "student_id": payload.get("student_id"),
        "commit_hash": payload.get("commit_hash"),
        "questions": [
            {
                "question": "What does the function `calculate_score()` do in this commit?",
                "options": ["Calculates AHP weights", "Fetches GitHub data", "Renders a chart", "Sends an email"],
                "correct_index": 0,
            }
        ],
    }


@app.task(name="performance.ingest_git_commits", queue="performance")
async def ingest_git_commits(payload: dict[str, Any]) -> dict[str, Any]:
    """Sandbox-clone a repo and compute commit regularity + authorship metrics.

    Expected payload keys:
        student_id  (str)  — student identifier
        repo_url    (str)  — GitHub HTTPS clone URL
        branch      (str)  — branch name (default: "main")
    """
    logger.info(f"[performance] ingest_git_commits: student={payload.get('student_id')}")

    return {
        "student_id": payload.get("student_id"),
        "repo_url": payload.get("repo_url"),
        "total_commits": 47,
        "lines_added": 3821,
        "lines_deleted": 512,
        "commit_regularity_score": 92.0,
    }


# ======================================================================================================================================
# Assessment agent jobs (see app/agents/performance_assessment/assessment/ and plan.md).
# The Core API creates the run row and defers these; the worker does the work. A run is one team and one sprint; students are assessed inside it.
# ======================================================================================================================================

import hashlib
from datetime import date, datetime, timedelta, timezone

SNAPSHOT_WINDOW_SECONDS = 3 * 3600  # nightly snapshots are spread over this long so 250 students' teams do not start at the same minute

_services = None


def _get_services():
    global _services
    if _services is None:
        # Heavy imports stay inside the function so the server process never loads them
        from app.agents.performance_assessment.assessment.services import Services

        _services = Services.from_environment()
    return _services


async def _with_checkpointer(sv, fn):
    """Run ``fn()`` with LangGraph's PostgreSQL checkpointer attached (tables are created on first use)."""
    from shared.queue import get_dsn

    from app.agents.performance_assessment.assessment.runner import postgres_checkpointer_cm

    async with postgres_checkpointer_cm(get_dsn()) as saver:
        await saver.setup()
        previous, sv.checkpointer = sv.checkpointer, saver
        try:
            return await fn()
        finally:
            sv.checkpointer = previous


@app.task(name="performance.assess_team", queue="performance")
async def assess_team(payload: dict[str, Any]) -> dict[str, Any]:
    """Run the team graph for one run row (snapshot or final). payload: {run_id, options?}.

    When a *final* run succeeds the task automatically queues final runs for any
    sprint that still has no succeeded or active run, so the agent self-chains
    through all configured sprints without any manual intervention.
    """
    from app.agents.performance_assessment.assessment.runner import run_assessment

    sv = _get_services()
    blocker = _blocking_sprint(sv, payload["run_id"])
    if blocker:
        # A sprint is assessed only after the ones before it: the agent carries what it learned from them (marks, flags, trends) into the next. While an earlier sprint is waiting for a person or has failed, this one waits too.
        run = sv.store.get_run(payload["run_id"])
        if not any(e["type"] == "run_blocked" and blocker[0] in e["message"] for e in sv.store.list_events(payload["run_id"], limit=200)):
            sv.store.add_event(payload["run_id"], "run_blocked", f"waiting for {blocker[0]} ({blocker[1]}) to be evaluated first", level="warn")
        await assess_team.configure(lock=run["team_ref"], schedule_in={"seconds": 60}).defer_async(payload=payload)
        return {"status": "blocked", "waiting_for": blocker[0]}
    result = await _with_checkpointer(sv, lambda: run_assessment(sv, payload["run_id"], options=payload.get("options")))

    # Auto-chain: if this final run succeeded, start runs for every sprint that
    # has not yet been assessed (no succeeded / running / queued / waiting_human run).
    if result.get("status") == "succeeded":
        await _enqueue_missing_sprints(sv, payload["run_id"])

    return result


def _blocking_sprint(sv, run_id: str):
    """(sprint id, state) of the earliest earlier sprint that has final runs but none finished, or None when this run may go ahead. Only final runs are ordered; an earlier sprint nobody has run does not block."""
    run = sv.store.get_run(run_id)
    if not run or run.get("mode") != "final" or run.get("status") != "queued":
        return None
    team = sv.store.get_tracked_team(run["team_ref"])
    sprints = sorted(((team or {}).get("config") or {}).get("sprints") or [], key=lambda x: x.get("start", ""))
    mine = next((x for x in sprints if x["id"] == run["sprint_id"]), None)
    if not mine:
        return None
    for sp in sprints:
        if sp.get("start", "") >= mine.get("start", ""):
            break
        finals = [r for r in sv.store.list_runs(run["team_ref"], sp["id"]) if r["mode"] == "final"]
        if finals and not any(r["status"] == "succeeded" for r in finals):
            return sp["id"], finals[0]["status"].replace("_", " ")
    return None


# ---- Sprint auto-chaining ---------------------------------------------------------------------------------------------------------------

#: States that mean a sprint is already covered — don't start another run for it.
_ACTIVE_OR_DONE = {"succeeded", "running", "queued", "waiting_human"}


async def _enqueue_missing_sprints(sv, completed_run_id: str) -> None:
    """Queue a final run for every sprint that has no succeeded or active run yet.

    Called automatically after a final run succeeds so the agent chains through
    all configured sprints without the lecturer having to click 'run' for each one.
    Snapshot runs are never chained — only final runs trigger the chain.
    """
    from shared.performance import RunAlreadyActive

    run = sv.store.get_run(completed_run_id)
    if not run or run.get("mode") != "final":
        return  # snapshots do not trigger chaining

    team_ref = run["team_ref"]
    team = sv.store.get_tracked_team(team_ref)
    if not team or team.get("status") != "active":
        return

    configured_sprints = (team.get("config") or {}).get("sprints", [])
    if not configured_sprints:
        return

    queued = 0
    for sprint in configured_sprints:
        sprint_id = sprint["id"]
        if sprint_id == run["sprint_id"]:
            continue  # the one we just finished — skip

        existing = sv.store.list_runs(team_ref, sprint_id)
        if any(r["status"] in _ACTIVE_OR_DONE for r in existing):
            continue  # already has an active or completed run — skip

        try:
            new_run = sv.store.create_run(team_ref, sprint_id, "final", requested_by="agent")
        except RunAlreadyActive:
            continue  # race condition: another worker just created it

        try:
            # The team lock ensures only one sprint runs at a time; the others wait in the queue.
            await assess_team.configure(lock=team_ref).defer_async(payload={"run_id": str(new_run["id"])})
            queued += 1
            logger.info("[performance] auto-chained sprint %s for team %s (run %s)", sprint_id, team_ref, new_run["id"])
        except Exception:
            logger.exception("[performance] could not queue sprint %s for team %s", sprint_id, team_ref)

    if queued:
        logger.info("[performance] %d sprint(s) auto-queued for team %s after run %s", queued, team_ref, completed_run_id)


@app.task(name="performance.queue_ping", queue="performance")
async def queue_ping(payload: dict[str, Any]) -> dict[str, Any]:
    """A harmless check that the queue and the worker are connected: appends the payload to the file named in it. payload: {file, n, note?}."""
    import json
    import os
    from pathlib import Path

    path = Path(payload["file"])
    if path.suffix != ".log" or "queue-ping" not in path.name or Path(os.environ.get("TEMP", "/tmp")) not in path.parents:
        return {"ok": False, "reason": "only queue-ping .log files in the temp folder"}  # the task writes nowhere else
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"n": payload.get("n"), "note": payload.get("note"), "at": datetime.now(timezone.utc).isoformat()}) + chr(10))
    return {"ok": True, "n": payload.get("n")}


@app.task(name="performance.resume_run", queue="performance")
async def resume_run(payload: dict[str, Any]) -> dict[str, Any]:
    """Continue a run that waited for the lecturer's identity mapping. payload: {run_id, resume}."""
    from app.agents.performance_assessment.assessment.runner import run_assessment

    sv = _get_services()
    result = await _with_checkpointer(sv, lambda: run_assessment(sv, payload["run_id"], resume=payload.get("resume") or {}))
    if result.get("status") == "succeeded":
        await _enqueue_missing_sprints(sv, payload["run_id"])
    return result


@app.task(name="performance.refuse_student", queue="performance")
async def refuse_student_task(payload: dict[str, Any]) -> dict[str, Any]:
    """A quiz answer arrived: compose that student's mark again. payload: {team_ref, sprint_id, student_id}."""
    from app.agents.performance_assessment.assessment.runner import refuse_student

    out = await refuse_student(_get_services(), payload["team_ref"], payload["sprint_id"], payload["student_id"])
    return out or {}


@app.task(name="performance.sync_team", queue="performance", pass_context=False)
async def sync_team(payload: dict[str, Any]) -> dict[str, Any]:
    """Cheap evidence sync (no language model): fetch the repository into the read-only mirror. payload: {team_ref}."""
    import asyncio

    sv = _get_services()
    team = sv.store.get_tracked_team(payload["team_ref"])
    if not team or team["status"] != "active":
        return {"skipped": True}
    await asyncio.to_thread(sv.ws.ensure_mirror, team["repo_url"], token=sv.token)
    heads = await asyncio.to_thread(sv.ws.read, team["repo_url"], "rev-list", "--all", "--count", token=sv.token)
    sv.store.update_tracked_config(team["team_ref"], {**(team.get("config") or {}), "last_sync": {"at": datetime.now(timezone.utc).isoformat(), "commits": int(heads.strip() or 0)}})
    return {"team_ref": team["team_ref"], "commits": int(heads.strip() or 0)}


def _active_sprints(team: dict, today: date) -> list[dict]:
    return [s for s in (team.get("config") or {}).get("sprints", []) if date.fromisoformat(s["start"]) <= today <= date.fromisoformat(s["end"])]


@app.periodic(cron="0 */2 * * *")
@app.task(name="performance.sync_all", queue="performance")
async def sync_all(timestamp: int) -> dict[str, Any]:
    """Every two hours: sync each active team that has a sprint in progress (the webhook does the same on a push)."""
    sv = _get_services()
    today = datetime.now(timezone.utc).date()
    n = 0
    for team in sv.store.list_tracked_teams("active"):
        if _active_sprints(team, today):
            try:
                await sync_team.configure(queueing_lock=f"sync:{team['team_ref']}").defer_async(payload={"team_ref": team["team_ref"]})
                n += 1
            except AlreadyEnqueued:  # a sync of this team is already waiting
                pass
    return {"teams": n}


@app.periodic(cron="30 19 * * *")  # 19:30 UTC = 01:00 in Sri Lanka
@app.task(name="performance.snapshot_all", queue="performance")
async def snapshot_all(timestamp: int) -> dict[str, Any]:
    """Nightly: a provisional snapshot of every team whose sprint is in progress, each started at its own offset inside the window."""
    from shared.performance import RunAlreadyActive

    sv = _get_services()
    today = datetime.now(timezone.utc).date()
    started = 0
    for team in sv.store.list_tracked_teams("active"):
        for sprint in _active_sprints(team, today):
            offset = int(hashlib.sha256(team["team_ref"].encode()).hexdigest(), 16) % SNAPSHOT_WINDOW_SECONDS
            try:
                run = sv.store.create_run(team["team_ref"], sprint["id"], "snapshot", requested_by="schedule")
            except RunAlreadyActive:
                continue
            await assess_team.configure(lock=team["team_ref"], schedule_in={"seconds": offset}).defer_async(payload={"run_id": str(run["id"])})
            started += 1
    return {"started": started}


@app.periodic(cron="5 * * * *")
@app.task(name="performance.quiz_sweep", queue="performance")
async def quiz_sweep(timestamp: int) -> dict[str, Any]:
    """Hourly: quizzes whose window has passed move to their second window or expire (a missed second window counts as 0)."""
    from app.agents.performance_assessment.assessment.runner import sweep_quizzes

    return await sweep_quizzes(_get_services())
