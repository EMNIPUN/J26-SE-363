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
    """Run the team graph for one run row (snapshot or final). payload: {run_id}."""
    from app.agents.performance_assessment.assessment.runner import run_assessment

    sv = _get_services()
    return await _with_checkpointer(sv, lambda: run_assessment(sv, payload["run_id"]))


@app.task(name="performance.resume_run", queue="performance")
async def resume_run(payload: dict[str, Any]) -> dict[str, Any]:
    """Continue a run that waited for the lecturer's identity mapping. payload: {run_id, resume}."""
    from app.agents.performance_assessment.assessment.runner import run_assessment

    sv = _get_services()
    return await _with_checkpointer(sv, lambda: run_assessment(sv, payload["run_id"], resume=payload.get("resume") or {}))


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
