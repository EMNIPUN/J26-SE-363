"""Decomposition Analysis sub-agent as a ReAct LangGraph.

Same shape as the Quality agent: reason -> execute_tool -> reflect -> finalize,
with conditional edges for adaptive depth. Evaluates the student's user stories
against the parent requirement using INVEST validation + coverage analysis.
"""

from __future__ import annotations

import asyncio
import logging

from langgraph.graph import END, START, StateGraph

from app.agents.project_planning.knowledge import query_patterns
from app.agents.project_planning.llm import get_llm_client
from app.agents.project_planning.schemas import (
    AnalyzeDecompositionInput,
    DecompositionResult,
)
from app.agents.project_planning.subagents.decomposition.coverage import (
    analyze_coverage,
)
from app.agents.project_planning.subagents.decomposition.invest import validate_invest
from app.agents.project_planning.subagents.decomposition.prompts import (
    REFLECT_SYSTEM,
    build_reflect_prompt,
)
from app.agents.project_planning.subagents.decomposition.scorer import (
    build_result,
    heuristic_result,
    request_decomposition_score,
)
from app.agents.project_planning.subagents.decomposition.state import DecompositionState

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 10
MAX_REFLECT = 1
AGENT_TIMEOUT_SECONDS = 180.0

TOOL_INVEST_VALIDATOR = "invest_validator"
TOOL_COVERAGE_ANALYZER = "coverage_analyzer"
TOOL_PATTERN_RETRIEVER = "pattern_retriever"
TOOL_DECOMPOSITION_SCORER = "decomposition_scorer"

_GATHER_TOOLS = (
    TOOL_COVERAGE_ANALYZER,
    TOOL_INVEST_VALIDATOR,
    TOOL_PATTERN_RETRIEVER,
)


# --- nodes ------------------------------------------------------------------

def reason(state: DecompositionState) -> DecompositionState:
    iterations = state.get("iterations", 0) + 1
    tools_run = state.get("tools_run", [])

    pending: str | None
    if iterations > MAX_ITERATIONS:
        pending = None
    elif next_gather := next((t for t in _GATHER_TOOLS if t not in tools_run), None):
        pending = next_gather
    elif TOOL_DECOMPOSITION_SCORER not in tools_run or state.get("reflection_note"):
        pending = TOOL_DECOMPOSITION_SCORER
    else:
        pending = None

    return {"pending_tool": pending, "iterations": iterations}


async def execute_tool(state: DecompositionState) -> DecompositionState:
    tool = state.get("pending_tool")
    tools_run = [*state.get("tools_run", [])]

    def mark(name: str) -> None:
        if name not in tools_run:
            tools_run.append(name)

    if tool == TOOL_COVERAGE_ANALYZER:
        mark(TOOL_COVERAGE_ANALYZER)
        try:
            result = await analyze_coverage(
                state["requirement_text"],
                state.get("stories", []),
            )
            return {
                "coverage": result["coverage"],
                "aspects": result["aspects"],
                "tools_run": tools_run,
            }
        except Exception:
            logger.exception("coverage_analyzer failed for %s", state.get("requirement_id"))
            return {"coverage": 0.0, "aspects": [], "tools_run": tools_run}

    if tool == TOOL_INVEST_VALIDATOR:
        mark(TOOL_INVEST_VALIDATOR)
        try:
            results = await validate_invest(state.get("stories", []))
            return {"invest_results": results, "tools_run": tools_run}
        except Exception:
            logger.exception("invest_validator failed for %s", state.get("requirement_id"))
            return {"invest_results": [], "tools_run": tools_run}

    if tool == TOOL_PATTERN_RETRIEVER:
        mark(TOOL_PATTERN_RETRIEVER)
        try:
            patterns = await asyncio.to_thread(query_patterns, state["requirement_text"], 3)
            return {"retrieved_patterns": patterns, "tools_run": tools_run}
        except Exception:
            logger.exception("pattern_retriever failed for %s", state.get("requirement_id"))
            return {"retrieved_patterns": [], "tools_run": tools_run}

    if tool == TOOL_DECOMPOSITION_SCORER:
        mark(TOOL_DECOMPOSITION_SCORER)
        try:
            invest_dicts = [r.model_dump() for r in state.get("invest_results", [])]
            gaps = [a for a in state.get("aspects", []) if not a.get("covered")]
            data = await request_decomposition_score(
                state["requirement_text"],
                state.get("coverage", 0.0),
                gaps,
                invest_dicts,
                state.get("retrieved_patterns"),
                state.get("reflection_note"),
            )
            return {"score_raw": data, "tools_run": tools_run, "reflection_note": None}
        except Exception:
            logger.exception("decomposition_scorer failed for %s", state.get("requirement_id"))
            return {"scoring_failed": True, "tools_run": tools_run, "reflection_note": None}

    return {}


async def reflect(state: DecompositionState) -> DecompositionState:
    if state.get("scoring_failed") or not state.get("score_raw"):
        return {"reflection_note": None}

    reflect_count = state.get("reflect_count", 0) + 1
    client = get_llm_client()
    data = state["score_raw"]
    score = int(data.get("overall_score", 50))
    confidence = float(data.get("confidence", 0.8) or 0.8)
    coverage = state.get("coverage", 0.0)

    needs_reflection = confidence < 0.85
    if not needs_reflection or not client.configured or reflect_count > MAX_REFLECT:
        return {"reflect_count": reflect_count, "reflection_note": None}

    invest_results = state.get("invest_results", [])
    passing = sum(1 for r in invest_results if r.overall_pass)
    invest_summary = f"{passing}/{len(invest_results)} stories pass all INVEST criteria"

    try:
        verdict = await client.complete_json(
            REFLECT_SYSTEM,
            build_reflect_prompt(
                state["requirement_text"],
                coverage,
                invest_summary,
                score,
                str(data.get("summary", "")),
            ),
            max_tokens=300,
        )
    except Exception:
        logger.exception("reflect step failed for %s", state.get("requirement_id"))
        return {"reflect_count": reflect_count, "reflection_note": None}

    ref_confidence = float(verdict.get("confidence", 0.8) or 0.8)
    consistent = bool(verdict.get("consistent", True))
    issue = str(verdict.get("issue", "") or "")

    if not consistent and issue:
        return {"reflect_count": reflect_count, "reflection_note": issue, "reflection_confidence": ref_confidence}
    return {"reflect_count": reflect_count, "reflection_note": None, "reflection_confidence": ref_confidence}


def finalize(state: DecompositionState) -> DecompositionState:
    req_id = state["requirement_id"]
    threshold = state.get("threshold", 75)
    invest_results = state.get("invest_results", [])
    coverage = state.get("coverage", 0.0)
    aspects = state.get("aspects", [])
    patterns = state.get("retrieved_patterns", [])

    if state.get("scoring_failed") or not state.get("score_raw"):
        return {"result": heuristic_result(req_id, invest_results, coverage, aspects, threshold)}

    return {
        "result": build_result(
            req_id,
            invest_results,
            coverage,
            aspects,
            patterns,
            state["score_raw"],
            threshold,
            confidence_override=state.get("reflection_confidence"),
        )
    }


# --- edges ------------------------------------------------------------------

def route_after_reason(state: DecompositionState) -> str:
    return "execute_tool" if state.get("pending_tool") else "reflect"


def route_after_reflect(state: DecompositionState) -> str:
    return "reason" if state.get("reflection_note") else "finalize"


def _build_graph():
    g = StateGraph(DecompositionState)
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


async def run_decomposition_agent(
    payload: AnalyzeDecompositionInput,
) -> DecompositionResult:
    """Run the ReAct loop for one decomposition analysis; fall back to heuristic on error/timeout."""
    stories_dicts = [{"id": s.id, "title": s.title, "acceptance_criteria": s.acceptance_criteria} for s in payload.stories]

    initial: DecompositionState = {
        "requirement_id": payload.requirement.id,
        "requirement_text": payload.requirement.text,
        "stories": stories_dicts,
        "threshold": payload.options.threshold,
        "tools_run": [],
        "iterations": 0,
        "reflect_count": 0,
    }
    try:
        final = await asyncio.wait_for(_GRAPH.ainvoke(initial), timeout=AGENT_TIMEOUT_SECONDS)
        result = final.get("result")
        if result is not None:
            return result
        logger.warning("Decomposition graph produced no result for %s; falling back", payload.requirement.id)
    except Exception:
        logger.exception("Decomposition ReAct graph failed for %s; falling back to heuristic", payload.requirement.id)

    invest_results = await validate_invest(stories_dicts)
    return heuristic_result(payload.requirement.id, invest_results, 0.0, [], payload.options.threshold)
