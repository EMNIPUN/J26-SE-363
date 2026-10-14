"""Quality Analysis sub-agent as a ReAct LangGraph.

Shape (proposal section 3.2.2): reason -> execute_tool -> reflect -> finalize,
with conditional edges that let the agent loop until it has consistent evidence.
This is what makes it an *agent* (adaptive, self-reflecting) rather than a fixed
pipeline, and it produces the reasoning trace DART will later consume.

    reason      decide the next tool, or move to reflection when evidence is gathered
    execute_tool  run the chosen tool (smell_detector, dimension_scorer)
    reflect     LLM checks the scores are internally consistent; may request a re-score
    finalize    apply the quality gate and emit the structured result

Safety: a max iteration count and a per-agent timeout both fall back to direct
scoring, so the loop is always bounded.
"""

from __future__ import annotations

import asyncio
import logging

from langgraph.graph import END, START, StateGraph

from app.agents.project_planning.llm import get_groq_client
from app.agents.project_planning.schemas import (
    RequirementInput,
    RequirementQualityResult,
)
from app.agents.project_planning.subagents.quality.prompts import (
    REFLECT_SYSTEM_PROMPT,
    build_reflect_prompt,
)
from app.agents.project_planning.subagents.quality.scorer import (
    build_result,
    heuristic_result,
    request_dimension_scores,
    score_requirement,
)
from app.agents.project_planning.subagents.quality.smells import detect_smells
from app.agents.project_planning.subagents.quality.state import QualityState

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 10   # hard cap on reason->tool loops
MAX_REFLECT = 1       # at most one reflect-driven re-score
AGENT_TIMEOUT_SECONDS = 150.0  # generous: allows for 429 rate-limit back-offs

TOOL_SMELL_DETECTOR = "smell_detector"
TOOL_DIMENSION_SCORER = "dimension_scorer"


# --- nodes ------------------------------------------------------------------


def reason(state: QualityState) -> QualityState:
    """Pick the next tool, or signal (pending_tool=None) to move on to reflection."""
    iterations = state.get("iterations", 0) + 1
    tools_run = state.get("tools_run", [])

    pending: str | None
    if iterations > MAX_ITERATIONS:
        pending = None  # safety: stop gathering, go reflect/finalize
    elif TOOL_SMELL_DETECTOR not in tools_run:
        pending = TOOL_SMELL_DETECTOR
    elif TOOL_DIMENSION_SCORER not in tools_run or state.get("reflection_note"):
        pending = TOOL_DIMENSION_SCORER  # score, or re-score after a reflection note
    else:
        pending = None

    return {"pending_tool": pending, "iterations": iterations}


async def execute_tool(state: QualityState) -> QualityState:
    """Run the tool the reason step selected, writing its observation into state."""
    tool = state.get("pending_tool")
    tools_run = [*state.get("tools_run", [])]

    if tool == TOOL_SMELL_DETECTOR:
        smells = detect_smells(state["requirement_text"])
        if TOOL_SMELL_DETECTOR not in tools_run:
            tools_run.append(TOOL_SMELL_DETECTOR)
        return {
            "smells": smells,
            "smell_spans": [s.span or s.type for s in smells],
            "tools_run": tools_run,
        }

    if tool == TOOL_DIMENSION_SCORER:
        if TOOL_DIMENSION_SCORER not in tools_run:
            tools_run.append(TOOL_DIMENSION_SCORER)
        try:
            data = await request_dimension_scores(
                state["requirement_text"],
                state.get("smell_spans", []),
                state.get("other_texts", []),
                state.get("reflection_note"),
            )
            return {"dimensions_raw": data, "tools_run": tools_run, "reflection_note": None}
        except Exception:
            logger.exception("dimension_scorer tool failed for %s", state.get("requirement_id"))
            return {"scoring_failed": True, "tools_run": tools_run, "reflection_note": None}

    return {}  # no-op


async def reflect(state: QualityState) -> QualityState:
    """LLM self-evaluation: are the scores consistent with the evidence?

    May set a reflection_note (→ one re-score) and always records a calibrated
    confidence used by the gate.
    """
    if state.get("scoring_failed") or not state.get("dimensions_raw"):
        return {"reflection_note": None}

    reflect_count = state.get("reflect_count", 0) + 1
    client = get_groq_client()
    data = state["dimensions_raw"]
    first_pass_confidence = float(data.get("confidence", 0.8) or 0.8)
    has_smells = bool(state.get("smell_spans"))

    # Adaptive depth (ReAct): only spend a reflect call when the result is
    # uncertain or the requirement has smells worth double-checking. Clearly
    # clean, high-confidence requirements skip reflection (shallower analysis).
    needs_reflection = first_pass_confidence < 0.85 or has_smells
    if not needs_reflection or not client.configured or reflect_count > MAX_REFLECT:
        return {"reflect_count": reflect_count, "reflection_note": None}

    try:
        verdict = await client.complete_json(
            REFLECT_SYSTEM_PROMPT,
            build_reflect_prompt(
                state["requirement_text"],
                data.get("dimensions", {}),
                state.get("smell_spans", []),
            ),
            max_tokens=300,
        )
    except Exception:
        logger.exception("reflect step failed for %s", state.get("requirement_id"))
        return {"reflect_count": reflect_count, "reflection_note": None}

    confidence = float(verdict.get("confidence", 0.8) or 0.8)
    consistent = bool(verdict.get("consistent", True))
    issue = str(verdict.get("issue", "") or "")

    if not consistent and issue:
        return {"reflect_count": reflect_count, "reflection_note": issue, "reflection_confidence": confidence}
    return {"reflect_count": reflect_count, "reflection_note": None, "reflection_confidence": confidence}


def finalize(state: QualityState) -> QualityState:
    """Apply the quality gate and emit the structured result."""
    req_id = state["requirement_id"]
    smells = state.get("smells", [])
    threshold = state.get("threshold", 75)

    if state.get("scoring_failed") or not state.get("dimensions_raw"):
        return {"result": heuristic_result(req_id, smells, threshold)}

    result = build_result(
        req_id,
        smells,
        state["dimensions_raw"],
        threshold,
        confidence_override=state.get("reflection_confidence"),
    )
    return {"result": result}


# --- edges ------------------------------------------------------------------


def route_after_reason(state: QualityState) -> str:
    return "execute_tool" if state.get("pending_tool") else "reflect"


def route_after_reflect(state: QualityState) -> str:
    return "reason" if state.get("reflection_note") else "finalize"


def _build_graph():
    g = StateGraph(QualityState)
    g.add_node("reason", reason)
    g.add_node("execute_tool", execute_tool)
    g.add_node("reflect", reflect)
    g.add_node("finalize", finalize)
    g.add_edge(START, "reason")
    g.add_conditional_edges("reason", route_after_reason, ["execute_tool", "reflect"])
    g.add_edge("execute_tool", "reason")
    g.add_conditional_edges("reflect", route_after_reflect, ["reason", "finalize"])
    g.add_edge("finalize", END)
    return g.compile()


_GRAPH = _build_graph()


async def run_quality_agent(
    req: RequirementInput,
    other_texts: list[str],
    threshold: int,
) -> RequirementQualityResult:
    """Run the ReAct loop for one requirement; fall back to direct scoring on error/timeout."""
    initial: QualityState = {
        "requirement_id": req.id,
        "requirement_text": req.text,
        "other_texts": other_texts,
        "threshold": threshold,
        "tools_run": [],
        "iterations": 0,
        "reflect_count": 0,
    }
    try:
        final = await asyncio.wait_for(_GRAPH.ainvoke(initial), timeout=AGENT_TIMEOUT_SECONDS)
        result = final.get("result")
        if result is not None:
            return result
        logger.warning("Quality graph produced no result for %s; falling back", req.id)
    except Exception:  # includes asyncio timeout — any failure degrades to direct scoring
        logger.exception("Quality ReAct graph failed for %s; falling back to direct scoring", req.id)

    return await score_requirement(req, other_texts, threshold)
