"""Task Validation sub-agent as a small LangGraph.

reason -> execute_tool (task_validator) -> finalize. Evaluates a story's
development tasks on four criteria (relevance, scope, actionability,
duplication) plus whether the task set as a whole covers the story's main
work, using a student-friendly, three-tier readiness classification (Valid /
Needs Improvement / Coverage Warning — see gate.py). Coverage dominates the
tier; per-task criteria are improvement guidance. Nothing hard-blocks
progression to effort estimation. Exactly ONE LLM call total per run.
"""

from __future__ import annotations

import asyncio
import logging

from langgraph.graph import END, START, StateGraph

from app.agents.project_planning.schemas import TaskSetCoverage, TaskValidationResult
from app.agents.project_planning.subagents.task_validation.gate import (
    classify_task_readiness,
)
from app.agents.project_planning.subagents.task_validation.scorer import (
    build_feedback,
    build_result,
)
from app.agents.project_planning.subagents.task_validation.state import (
    TaskValidationState,
)
from app.agents.project_planning.subagents.task_validation.validator import (
    validate_tasks,
)

logger = logging.getLogger(__name__)

AGENT_TIMEOUT_SECONDS = 180.0

TOOL_TASK_VALIDATOR = "task_validator"


# --- nodes ------------------------------------------------------------------

def reason(state: TaskValidationState) -> TaskValidationState:
    tools_run = state.get("tools_run", [])
    pending = TOOL_TASK_VALIDATOR if TOOL_TASK_VALIDATOR not in tools_run else None
    return {"pending_tool": pending}


async def execute_tool(state: TaskValidationState) -> TaskValidationState:
    tools_run = [*state.get("tools_run", []), TOOL_TASK_VALIDATOR]
    try:
        items, coverage, analysis_failed, failure_reason = await validate_tasks(
            state["story_ref"], state["story_text"], state.get("requirement_text", ""), state.get("tasks", [])
        )
    except Exception:
        logger.exception("task_validator failed for %s", state.get("story_ref"))
        items, coverage, analysis_failed, failure_reason = (
            [],
            None,
            True,
            "Task validation failed — please re-run validation.",
        )
    return {
        "items": items,
        "coverage": coverage,
        "analysis_failed": analysis_failed,
        "failure_reason": failure_reason,
        "tools_run": tools_run,
    }


def finalize(state: TaskValidationState) -> TaskValidationState:
    items = state.get("items", [])
    coverage = state.get("coverage") or TaskSetCoverage()
    analysis_failed = bool(state.get("analysis_failed"))
    failure_reason = state.get("failure_reason")

    readiness, readiness_reason = classify_task_readiness(
        coverage, items, analysis_failed=analysis_failed, failure_reason=failure_reason
    )
    feedback = build_feedback(
        readiness, coverage, items, analysis_failed=analysis_failed, failure_reason=failure_reason
    )
    # Transparency signal only (not a gate input): low when the run could not
    # actually be assessed (LLM unavailable/failed).
    confidence = 1.0 if items and not analysis_failed else 0.3

    return {
        "result": build_result(
            state["story_ref"],
            coverage,
            items,
            readiness,
            readiness_reason,
            feedback,
            analysis_failed=analysis_failed,
            failure_reason=failure_reason,
            confidence=confidence,
        )
    }


# --- edges ------------------------------------------------------------------

def route_after_reason(state: TaskValidationState) -> str:
    return "execute_tool" if state.get("pending_tool") else "finalize"


def _build_graph():
    g = StateGraph(TaskValidationState)
    g.add_node("reason", reason)
    g.add_node("execute_tool", execute_tool)
    g.add_node("finalize", finalize)
    g.add_edge(START, "reason")
    g.add_conditional_edges("reason", route_after_reason, ["execute_tool", "finalize"])
    g.add_edge("execute_tool", "reason")
    g.add_edge("finalize", END)
    return g.compile()


_GRAPH = _build_graph()


async def run_task_validation_agent(
    story_ref: str, story_text: str, requirement_text: str, tasks: list[dict]
) -> TaskValidationResult:
    """Run the validate-then-finalize graph for one task-validation run; fall
    back to a safe structural result (never a false Valid) on error/timeout."""
    initial: TaskValidationState = {
        "story_ref": story_ref,
        "story_text": story_text,
        "requirement_text": requirement_text,
        "tasks": tasks,
        "tools_run": [],
    }
    try:
        final = await asyncio.wait_for(_GRAPH.ainvoke(initial), timeout=AGENT_TIMEOUT_SECONDS)
        result = final.get("result")
        if result is not None:
            return result
        logger.warning("Task validation graph produced no result for %s; falling back", story_ref)
    except Exception:
        logger.exception("Task validation graph failed for %s; falling back", story_ref)

    coverage = TaskSetCoverage(coverage_percentage=0.0, missing_work_items=[])
    readiness, readiness_reason = classify_task_readiness(
        coverage, [], analysis_failed=True,
        failure_reason="Task validation failed — please re-run validation.",
    )
    feedback = build_feedback(
        readiness, coverage, [], analysis_failed=True,
        failure_reason="Task validation failed — please re-run validation.",
    )
    return build_result(
        story_ref, coverage, [], readiness, readiness_reason, feedback,
        analysis_failed=True,
        failure_reason="Task validation failed — please re-run validation.",
        confidence=0.0,
    )
