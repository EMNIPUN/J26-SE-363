"""Running the team graph for one run, and the events that continue a student's assessment later.

    await run_assessment(sv, run_id)                       start (or run again after a failure)
    await run_assessment(sv, run_id, resume={...})         continue after the lecturer's identity mapping
    await refuse_student(sv, team_ref, sprint_id, sid)     a quiz answer arrived or expired: Code Ownership changes, the mark is composed again
    await sweep_quizzes(sv)                                move overdue quizzes to their second window or to 'expired' and re-compose the students whose quiz expired

A run's graph state is kept by ``sv.checkpointer`` (``postgres_checkpointer`` in the worker, in memory in tests).
"""
import asyncio
import os
import traceback

from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from app.agents.performance_assessment.assessment import audit, factors, justify, quiz_flow
from app.agents.performance_assessment.assessment import events as events_mod
from app.agents.performance_assessment.assessment.events import Events
from app.agents.performance_assessment.assessment.fusion import fuse
from app.agents.performance_assessment.assessment.graph import TeamGraph
from app.agents.performance_assessment.com_agent.config.settings_loader import settings


RUN_TIMEOUT = float(os.environ.get("ASSESSMENT_RUN_TIMEOUT", 7200))  # seconds a whole run may take; a run that is not finished by then is stopped and marked failed


def postgres_checkpointer_cm(dsn: str):
    """Async context manager for LangGraph's PostgreSQL checkpointer (tables are created on first use): ``async with postgres_checkpointer_cm(dsn) as saver: sv.checkpointer = saver``."""
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    return AsyncPostgresSaver.from_conn_string(dsn)


async def run_assessment(sv, run_id: str, resume=None, options=None) -> dict:
    store = sv.store
    run = store.get_run(run_id)
    if run is None:
        raise ValueError(f"unknown run {run_id}")
    if sv.checkpointer is None:
        sv.checkpointer = MemorySaver()
    graph = TeamGraph(sv).build(sv.checkpointer)
    config = {"configurable": {"thread_id": f"{run['thread_id']}:{run_id}"}}
    ev = Events(store, run_id)
    await asyncio.to_thread(store.update_run, run_id, status="running")
    ev.emit("run_start" if resume is None else "run_resume", f"{run['mode']} run for team {run['team_ref']}, sprint {run['sprint_id']}")
    if resume is None:
        # the first thing the live trace shows, so it is busy from the first second (the plan is what the run does, nothing guessed)
        ev.thinking("team", "Planning the assessment", thinking=(
            f"{str(run['mode']).capitalize()} assessment of team {run['team_ref']} for {run['sprint_id']}.\n\n"
            "1. Read the repository and the Scrum board for the sprint.\n"
            "2. Match each student's commits and tasks to them.\n"
            "3. Score effort, consistency, requirement fulfillment, collaboration and task complexity.\n"
            "4. Check my own results, then write the explanation for each student."))
    try:
        try:
            if resume is not None:
                out = await asyncio.wait_for(graph.ainvoke(Command(resume=resume), config), RUN_TIMEOUT)
            else:
                init_state = {"run_id": run_id, "team_ref": run["team_ref"], "sprint_id": run["sprint_id"], "mode": run["mode"]}
                if options:
                    init_state["options"] = options
                out = await asyncio.wait_for(graph.ainvoke(init_state, config), RUN_TIMEOUT)
        except asyncio.CancelledError:
            await asyncio.to_thread(store.update_run, run_id, status="cancelled")
            ev.emit("run_end", "cancelled", level="warn")
            raise
        except asyncio.TimeoutError:
            message = f"the run did not finish within {RUN_TIMEOUT:.0f} s and was stopped"
            await asyncio.to_thread(store.update_run, run_id, status="failed", error={"type": "Timeout", "message": message})
            ev.emit("run_end", f"failed: {message}", level="error")
            return {"status": "failed", "error": message}
        except Exception as e:
            await asyncio.to_thread(store.update_run, run_id, status="failed", error={"type": type(e).__name__, "message": str(e)[:500], "trace": traceback.format_exc()[-1500:]})
            ev.emit("run_end", f"failed: {type(e).__name__}: {str(e)[:200]}", level="error")
            return {"status": "failed", "error": str(e)}
        if out.get("__interrupt__"):
            await asyncio.to_thread(store.update_run, run_id, status="waiting_human")
            ev.emit("run_waiting", "waiting for the lecturer's identity mapping", level="warn")
            return {"status": "waiting_human"}
        await asyncio.to_thread(store.update_run, run_id, status="succeeded", current_node="")
        ev.emit("run_end", "succeeded")
        return {"status": "succeeded"}
    finally:
        await asyncio.to_thread(events_mod.close, store, run_id)  # write the queued events before the job ends
        sv._data.pop(run_id, None)  # the evidence of a finished run is not kept in memory; a run that waits for a person loads it from its folder again


# ---- later events ---------------------------------------------------------------------------------------------------------------------

def _from_rows(rows):
    return {r["factor"]: {"factor": r["factor"], "score": r["score"], "status": r["status"], "interval": r["interval"], "warnings": r["warnings"] or [], "versions": r["versions"] or {},
                          "features": r["features"] or {}, "provisional": r["provisional"], "removed": {}, "tasks": None, "model": None} for r in rows if r["factor"] != "behavioral_pattern"}


async def refuse_student(sv, team_ref: str, sprint_id: str, student_id: str) -> dict | None:
    """Compose one student's mark again after their quiz changed state. Uses the stored factor results of the latest final run; the other factors are not recomputed."""
    store = sv.store
    runs = [r for r in store.list_runs(team_ref, sprint_id) if r["mode"] == "final" and r["status"] in ("succeeded", "waiting_human")]
    if not runs:
        return None
    run = runs[0]
    results = _from_rows(store.list_factor_results(run["id"], student_id))
    if not results:
        return None
    ev = Events(store, run["id"])
    path = f"student:{student_id}/ownership_quiz"
    async with ev.node(path) as n:
        quiz = store.list_quizzes(team_ref, sprint_id, student_id)
        r = await quiz_flow.factor_for(store, quiz)
        results["code_ownership"] = r
        store.save_factor_result(run["id"], student_id, "code_ownership", score=r["score"], status=r["status"], interval=r["interval"], provisional=r["provisional"], features=r["features"],
                                 warnings=r["warnings"], versions=r["versions"])
        behavioral = factors.run_behavioral(results, provisional=False)
        fused = fuse(results, behavioral)
        found = audit.findings(results, None, None, fused["mark"])
        summary = {k: {"score": x["score"], "status": x["status"]} for k, x in results.items()}
        reasoning = await asyncio.to_thread(audit.llm_decide, sv.llm, found, sv.cards, summary)
        actions = audit.decide(found, reasoning)
        open_reviews = {(x.get("evidence") or {}).get("finding") for x in store.list_reviews(None, run["id"]) if x.get("student_id") == student_id}
        for a in actions:
            if a["action"] == "escalate" and a["id"] not in open_reviews:
                store.create_review(run["id"], "audit", f"{a['message']} | {a['reason']}", student_id=student_id, evidence={"finding": a["id"], "factor": a["factor"], "mark": fused["mark"], "scores": summary})
        status = "pending_review" if any(a["action"] == "escalate" for a in actions) else ("final" if not fused["pending"] else "provisional")
        just = justify.explain(student_id, results, fused, {}, sv.cards, actions, status)
        just["audit"] = {"actions": [{k: a[k] for k in ("id", "factor", "severity", "action", "reason")} for a in actions], "summary": (reasoning or {}).get("summary"), "model": (reasoning or {}).get("model")}
        compact = {k: {"score": x["score"], "status": x["status"], "interval": x["interval"], "provisional": x["provisional"]} for k, x in results.items()}
        compact["behavioral_pattern"] = {"persona": behavioral.get("persona"), "applied": behavioral.get("applied"), "modifier": behavioral.get("modifier")}
        store.save_assessment_result(run["id"], team_ref, sprint_id, student_id, mark=fused["mark"], mark_interval=fused["mark_interval"], status=status, factors=compact, justification=just, flags=just["flags"])
        s = dict(run.get("summary") or {})
        s["marks"] = {**(s.get("marks") or {}), student_id: fused["mark"]}
        s["pending_code_ownership"] = sorted(set(s.get("pending_code_ownership") or []) - ({student_id} if not fused["pending"] else set()))
        store.update_run(run["id"], summary=s)
        n.log(f"Code Ownership {r['status']}; mark {fused['mark'] if fused['mark'] is None else round(fused['mark'], 1)} ({status})")
        n.result(status=status)
    await asyncio.to_thread(events_mod.close, store, run["id"])
    return {"student_id": student_id, "mark": fused["mark"], "status": status}


async def answer_quiz(sv, quiz_id: str, student_id: str, answer: str, now=None) -> dict:
    """The student's answer. Returns ``{"accepted": bool, ...}``; an accepted answer re-composes the student's mark."""
    store = sv.store
    quiz = next((q for q in store.list_student_quizzes(student_id) if q["id"] == quiz_id), None)
    if quiz is None:
        return {"accepted": False, "reason": "no such quiz for this student"}
    row = store.submit_quiz_answer(quiz_id, answer, now)
    if row is None:
        return {"accepted": False, "reason": "the answer windows have passed or the quiz was already answered"}
    after = await refuse_student(sv, quiz["team_ref"], quiz["sprint_id"], student_id)
    return {"accepted": True, "in_extension": row["in_extension"], "result": after}


async def sweep_quizzes(sv, now=None) -> dict:
    cfg = settings.quiz_timeout
    changed = sv.store.advance_quiz_windows(cfg.extra_time_hours, now)
    expired = [q for q in changed if q["status"] == "expired"]
    for q in expired:
        await refuse_student(sv, q["team_ref"], q["sprint_id"], q["student_id"])
    return {"extended": sum(1 for q in changed if q["status"] == "extended"), "expired": len(expired)}
