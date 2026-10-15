"""DART sub-agent as a ReAct LangGraph.

Five-step protocol: Gather → Categorize → Consult → Respond → Resolve,
with conditional looping for RETRIEVE/REFINE actions (max 2 iterations).

    reason          pick the next protocol step
    execute_step    run the chosen step's tool function
    check_convergence  after resolve, decide whether to loop or finalize
    finalize        build the DartCaseResult

Safety: MAX_ITERATIONS caps reason→step loops, MAX_DART_ITERATIONS caps the
outer arbitration loop, and AGENT_TIMEOUT_SECONDS wraps the whole graph.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, datetime

from langgraph.graph import END, START, StateGraph

from app.agents.project_planning.schemas import (
    ArbitrateDartInput,
    DartCaseResult,
    DartCaseStatus,
    DartCategory,
    DartResolution,
    DartResolutionAction,
    DartTriggerReason,
)
from app.agents.project_planning.subagents.dart.state import DartState
from app.agents.project_planning.subagents.dart.tools import (
    categorize_issue,
    determine_resolution,
    execute_consultation,
    formulate_consultation,
    gather_traces,
)

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 15
MAX_DART_ITERATIONS = 2
AGENT_TIMEOUT_SECONDS = 60.0

STEP_GATHER = "gather"
STEP_CATEGORIZE = "categorize"
STEP_CONSULT = "consult"
STEP_RESPOND = "respond"
STEP_RESOLVE = "resolve"

_PROTOCOL_SEQUENCE = (STEP_GATHER, STEP_CATEGORIZE, STEP_CONSULT, STEP_RESPOND, STEP_RESOLVE)


# --- nodes ------------------------------------------------------------------


def reason(state: DartState) -> DartState:
    iterations = state.get("iterations", 0) + 1
    steps_run = state.get("steps_run", [])

    if iterations > MAX_ITERATIONS:
        return {"pending_step": None, "iterations": iterations}

    next_step = next((s for s in _PROTOCOL_SEQUENCE if s not in steps_run), None)
    return {"pending_step": next_step, "iterations": iterations}


async def execute_step(state: DartState) -> DartState:
    step = state.get("pending_step")
    steps_run = [*state.get("steps_run", [])]
    text = state["requirement_text"]

    def mark(name: str) -> None:
        if name not in steps_run:
            steps_run.append(name)

    if step == STEP_GATHER:
        mark(STEP_GATHER)
        traces = await gather_traces(text, state["source_stage"], state["source_result"])
        return {"traces": traces, "steps_run": steps_run}

    if step == STEP_CATEGORIZE:
        mark(STEP_CATEGORIZE)
        traces = state.get("traces", [])
        hypothesis = await categorize_issue(text, traces)
        return {"hypothesis": hypothesis, "steps_run": steps_run}

    if step == STEP_CONSULT:
        mark(STEP_CONSULT)
        hypothesis = state.get("hypothesis")
        traces = state.get("traces", [])
        if not hypothesis:
            return {"steps_run": steps_run}
        consultation = await formulate_consultation(text, hypothesis, traces)
        return {"consultation": consultation, "steps_run": steps_run}

    if step == STEP_RESPOND:
        mark(STEP_RESPOND)
        consultation = state.get("consultation")
        if not consultation:
            return {"steps_run": steps_run}
        response = await execute_consultation(text, consultation, state["source_stage"])
        return {"consultation_response": response, "steps_run": steps_run}

    if step == STEP_RESOLVE:
        mark(STEP_RESOLVE)
        hypothesis = state.get("hypothesis")
        consultation = state.get("consultation")
        response = state.get("consultation_response")
        traces = state.get("traces", [])
        dart_iteration = state.get("dart_iteration", 1)

        if not all([hypothesis, consultation, response]):
            resolution = DartResolution(
                action=DartResolutionAction.ESCALATE,
                rationale="Incomplete DART protocol — missing steps",
                actionable_feedback="This requirement needs instructor review.",
            )
        else:
            resolution = await determine_resolution(
                text, hypothesis, consultation, response, traces, dart_iteration,
            )
        return {"resolution": resolution, "steps_run": steps_run}

    return {}


def check_convergence(state: DartState) -> DartState:
    resolution = state.get("resolution")
    if not resolution:
        return {}

    dart_iteration = state.get("dart_iteration", 1)

    if resolution.action in (DartResolutionAction.RETRIEVE, DartResolutionAction.REFINE):
        if dart_iteration < MAX_DART_ITERATIONS:
            return {
                "dart_iteration": dart_iteration + 1,
                "steps_run": [STEP_GATHER],
                "hypothesis": None,
                "consultation": None,
                "consultation_response": None,
                "resolution": None,
            }
        resolution.action = DartResolutionAction.ESCALATE
        resolution.rationale += " (forced after max iterations)"
        return {"resolution": resolution}

    return {}


def finalize(state: DartState) -> DartState:
    resolution = state.get("resolution")
    hypothesis = state.get("hypothesis")

    if resolution and resolution.action == DartResolutionAction.ESCALATE:
        case_status = DartCaseStatus.ESCALATED
    else:
        case_status = DartCaseStatus.OPEN

    category = hypothesis.category if hypothesis else DartCategory.AMBIGUOUS
    trigger = DartTriggerReason.LOW_CONFIDENCE
    try:
        trigger = DartTriggerReason(state.get("trigger_reason", "low_confidence"))
    except ValueError:
        pass

    result = DartCaseResult(
        case_id=f"DART-{uuid.uuid4().hex[:8].upper()}",
        requirement_ref=state.get("requirement_id", ""),
        category=category,
        status=case_status,
        trigger_reason=trigger,
        source_stage=state.get("source_stage", "quality"),
        traces=state.get("traces", []),
        hypothesis=hypothesis,
        consultation=state.get("consultation"),
        response=state.get("consultation_response"),
        resolution=resolution,
        iteration=state.get("dart_iteration", 1),
        created_at=datetime.now(UTC).isoformat(),
    )
    return {"result": result}


# --- edges ------------------------------------------------------------------


def route_after_reason(state: DartState) -> str:
    return "execute_step" if state.get("pending_step") else "check_convergence"


def route_after_convergence(state: DartState) -> str:
    resolution = state.get("resolution")
    if not resolution:
        return "reason"
    if resolution.action in (DartResolutionAction.RETRIEVE, DartResolutionAction.REFINE) and state.get("dart_iteration", 1) < MAX_DART_ITERATIONS:
        return "reason"
    return "finalize"


def _build_graph():
    g = StateGraph(DartState)
    g.add_node("reason", reason)
    g.add_node("execute_step", execute_step)
    g.add_node("check_convergence", check_convergence)
    g.add_node("finalize", finalize)
    g.add_edge(START, "reason")
    g.add_conditional_edges("reason", route_after_reason, ["execute_step", "check_convergence"])
    g.add_edge("execute_step", "reason")
    g.add_conditional_edges("check_convergence", route_after_convergence, ["reason", "finalize"])
    g.add_edge("finalize", END)
    return g.compile()


_GRAPH = _build_graph()


async def run_dart_agent(payload: ArbitrateDartInput) -> DartCaseResult:
    """Run the five-step DART protocol; fall back to ESCALATE on timeout/error."""
    stories_dicts = [
        {"id": s.id, "title": s.title, "acceptance_criteria": s.acceptance_criteria}
        for s in payload.stories
    ]

    initial: DartState = {
        "requirement_id": payload.requirement.id,
        "requirement_text": payload.requirement.text,
        "trigger_reason": payload.trigger_reason.value,
        "source_stage": payload.source_stage,
        "source_result": payload.source_result,
        "stories": stories_dicts,
        "steps_run": [],
        "iterations": 0,
        "dart_iteration": 1,
    }

    try:
        final = await asyncio.wait_for(_GRAPH.ainvoke(initial), timeout=AGENT_TIMEOUT_SECONDS)
        result = final.get("result")
        if result is not None:
            return result
        logger.warning("DART graph produced no result for %s; escalating", payload.requirement.id)
    except Exception:
        logger.exception("DART agent failed for %s; escalating", payload.requirement.id)

    return DartCaseResult(
        case_id=f"DART-{uuid.uuid4().hex[:8].upper()}",
        requirement_ref=payload.requirement.id,
        category=DartCategory.AMBIGUOUS,
        status=DartCaseStatus.ESCALATED,
        trigger_reason=payload.trigger_reason,
        source_stage=payload.source_stage,
        resolution=DartResolution(
            action=DartResolutionAction.ESCALATE,
            rationale="DART agent timeout or internal error",
            actionable_feedback="This requirement needs instructor review — the automated arbitration could not complete.",
        ),
        created_at=datetime.now(UTC).isoformat(),
    )
