"""Public entrypoints and triggers for the performance assessment agent (com_agent).

Strictly aligned with:
- BOARD.md Phase 7 (T7.1.1 - T7.1.4)
- PLAN.md Section 2 (The Four Execution Triggers)
- PLAN.md Section 3 (Per-Student Isolation Model & Cohort Baselines)
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional

from app.agents.performance_assessment.com_agent.graph import (
    build_com_agent_graph,
    build_initial_state,
    make_thread_config,
    Command,
)

logger = logging.getLogger(__name__)

# Global default compiled graph instance for thread lifecycle management
_default_graph: Optional[Any] = None


def get_default_graph() -> Any:
    """Retrieve or lazily construct the default compiled StateGraph instance."""
    global _default_graph
    if _default_graph is None:
        _default_graph = build_com_agent_graph()
    return _default_graph


def reset_default_graph() -> None:
    """Reset the default graph (primarily for isolated test fixtures)."""
    global _default_graph
    _default_graph = None


async def trigger_sprint_end(
    sprint_id: str,
    student_ids: Optional[List[str]] = None,
    graph: Optional[Any] = None,
    custom_contexts: Optional[Dict[str, Dict[str, Any]]] = None,
) -> List[str]:
    """Trigger 1: Automated Sprint End Trigger (Primary Entrypoint).

    T7.1.1:
    - Pre-computes cohort baselines or loads mock contexts.
    - Spawns independent per-student LangGraph threads concurrently.
    - Runs Stage 1 passive factors, extracts code slice, generates AST question.
    - Pauses at await_quiz_response_node.
    - Returns list of thread IDs paused at quiz interrupt.
    """
    runner = graph or get_default_graph()
    target_student_ids = student_ids if student_ids is not None else ["STU-001"]

    async def _run_for_student(stu_id: str) -> str:
        cfg = make_thread_config(sprint_id, stu_id)
        ctx = {"student_id": stu_id, "sprint_id": sprint_id}
        if custom_contexts and stu_id in custom_contexts:
            ctx.update(custom_contexts[stu_id])
        
        # Non-lossy evidence ingestion & multi-factor preparation pool
        try:
            from app.agents.performance_assessment.com_agent.ingestion.evidence_preparer import (
                ingest_and_pool_evidence,
            )
            pooled = await ingest_and_pool_evidence(
                student_id=stu_id,
                sprint_id=sprint_id,
                team_id=ctx.get("team_id", "TEAM-A"),
                repo_url=ctx.get("repo_url", "https://github.com/org/repo"),
                force_refresh=False,
                custom_context=ctx,
            )
            ctx["prepared_factor_payloads"] = pooled.get("factor_payloads")
            ctx["has_committed_dependencies"] = (
                pooled.get("factor_payloads", {})
                .get("effort", {})
                .get("has_committed_dependencies", False)
            )
        except Exception as e:
            logger.warning(f"Evidence pooling fallback for {stu_id}: {e}")

        initial_state = build_initial_state(ctx)
        await runner.ainvoke(initial_state, config=cfg)
        return cfg["configurable"]["thread_id"]

    # Concurrently execute all student threads
    tasks = [_run_for_student(s_id) for s_id in target_student_ids]
    thread_ids = await asyncio.gather(*tasks)
    return list(thread_ids)


async def submit_quiz_response(
    thread_id: str,
    student_response: str,
    graph: Optional[Any] = None,
) -> str:
    """Trigger 2: Student Quiz Submission Trigger (Resumption Event).

    T7.1.2:
    - Resumes thread via ainvoke(Command(resume={'student_response': ...})).
    - Evaluates Code Ownership, classifies Behavioral Pattern, executes fusion, checks discrepancies.
    - Returns 'pending_lecturer_review' if review interrupt is triggered, else 'evaluation_complete'.
    """
    runner = graph or get_default_graph()
    cfg = {"configurable": {"thread_id": thread_id}}
    cmd = Command(resume={"student_response": student_response})

    state = await runner.ainvoke(cmd, config=cfg)
    step = state.get("current_step")

    if state.get("requires_human_review") or step in ["discrepancy_checked", "pending_lecturer_review"]:
        return "pending_lecturer_review"
    elif step == "export_complete":
        return "evaluation_complete"
    return "evaluation_complete"


async def trigger_on_demand(
    sprint_id: str,
    student_id: str,
    graph: Optional[Any] = None,
    student_context: Optional[Dict[str, Any]] = None,
    force_refresh: bool = False,
) -> str:
    """Trigger 3: On-Demand Lecturer Trigger (Manual Dashboard Trigger).

    T7.1.3:
    - Starts a fresh assessment run for a single student.
    - Ingests or reuses non-lossy evidence pool (honoring force_refresh).
    - Runs until quiz interrupt or completion.
    - Returns thread_id.
    """
    runner = graph or get_default_graph()
    cfg = make_thread_config(sprint_id, student_id)
    ctx = {"student_id": student_id, "sprint_id": sprint_id}
    if student_context:
        ctx.update(student_context)

    # Ingest or reuse evidence pool
    try:
        from app.agents.performance_assessment.com_agent.ingestion.evidence_preparer import (
            ingest_and_pool_evidence,
        )
        pooled = await ingest_and_pool_evidence(
            student_id=student_id,
            sprint_id=sprint_id,
            team_id=ctx.get("team_id", "TEAM-A"),
            repo_url=ctx.get("repo_url", "https://github.com/org/repo"),
            force_refresh=force_refresh,
            custom_context=ctx,
        )
        ctx["prepared_factor_payloads"] = pooled.get("factor_payloads")
        ctx["has_committed_dependencies"] = (
            pooled.get("factor_payloads", {})
            .get("effort", {})
            .get("has_committed_dependencies", False)
        )
    except Exception as e:
        logger.warning(f"On-demand evidence pooling fallback for {student_id}: {e}")

    initial_state = build_initial_state(ctx)
    await runner.ainvoke(initial_state, config=cfg)
    return cfg["configurable"]["thread_id"]


async def check_expired_quiz_timeouts(
    graph: Optional[Any] = None,
    now_iso: Optional[str] = None,
) -> List[str]:
    """Finds threads waiting at quiz interrupt whose deadlines have elapsed, and wakes them up with timeout=True."""
    from datetime import datetime, timezone
    runner = graph or get_default_graph()
    current_time = datetime.fromisoformat(now_iso) if now_iso else datetime.now(timezone.utc)
    expired_threads = []

    if hasattr(runner, "checkpointer") and runner.checkpointer is not None:
        storage = getattr(runner.checkpointer, "storage", None)
        if isinstance(storage, dict):
            for thread_id, saved_state in storage.items():
                step = saved_state.get("current_step")
                if step in ["quiz_generated", "quiz_extended_waiting"]:
                    av = saved_state.get("active_verification")
                    deadline_str = getattr(av, "quiz_extension_deadline", None) if hasattr(av, "quiz_extension_deadline") else (av.get("quiz_extension_deadline") if isinstance(av, dict) else None)
                    if not deadline_str:
                        deadline_str = saved_state.get("quiz_deadline")
                    if deadline_str:
                        try:
                            dl = datetime.fromisoformat(deadline_str)
                            if current_time >= dl:
                                expired_threads.append(thread_id)
                        except Exception:
                            pass

    for tid in expired_threads:
        cfg = {"configurable": {"thread_id": tid}}
        await runner.ainvoke(Command(resume={"timeout": True}), config=cfg)

    return expired_threads


async def submit_lecturer_review(
    thread_id: str,
    override_score: Optional[float] = None,
    reason: Optional[str] = None,
    lecturer_id: Optional[str] = None,
    graph: Optional[Any] = None,
) -> str:
    """Trigger 4: Lecturer Review / Override Resumption Trigger.

    T7.1.4:
    - Resumes lecturer review interrupt.
    - Finalizes report generation, persistence, and exports.
    - Returns 'finalized' when export completes.
    """
    runner = graph or get_default_graph()
    cfg = {"configurable": {"thread_id": thread_id}}
    cmd = Command(
        resume={
            "override_score": override_score,
            "reason": reason,
            "comments": reason,
            "lecturer_id": lecturer_id or "LEC-001",
        }
    )

    state = await runner.ainvoke(cmd, config=cfg)
    if state.get("current_step") == "export_complete":
        return "finalized"
    return "finalized"


def get_assessment_status(
    thread_id: str,
    graph: Optional[Any] = None,
) -> Optional[Dict[str, Any]]:
    """Retrieve the current saved AssessmentState snapshot for a thread."""
    runner = graph or get_default_graph()
    cfg = {"configurable": {"thread_id": thread_id}}
    if hasattr(runner, "checkpointer") and runner.checkpointer is not None:
        return runner.checkpointer.get(cfg)
    return None
