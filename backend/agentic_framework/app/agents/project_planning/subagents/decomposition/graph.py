"""Decomposition Analysis sub-agent as a small LangGraph.

reason -> execute_tool (coverage_analyzer, invest_validator, pattern_retriever)
-> finalize. Evaluates the student's user stories against the parent
requirement using a student-friendly, three-tier readiness classification
(Ready / Ready with Improvements / Needs Attention — see gate.py). Coverage/
traceability (C1-C10) dominates the tier; INVEST is improvement guidance.
Nothing hard-blocks progression to effort estimation. The readiness/score/
feedback pipeline makes exactly TWO LLM calls total per run (one
coverage_analyzer call, one batched invest_validator call covering all
stories) — see scorer.py's module docstring for why the scorer and reflect
LLM calls that used to run here were removed (they were the dominant source
of Gemini free-tier quota exhaustion).
"""

from __future__ import annotations

import asyncio
import logging

from langgraph.graph import END, START, StateGraph

from app.agents.project_planning.knowledge import query_patterns
from app.agents.project_planning.schemas import (
    AnalyzeDecompositionInput,
    CoverageAnalysis,
    DecompositionResult,
    InvestGateResult,
    StoryInvest,
)
from app.agents.project_planning.subagents.decomposition.coverage import (
    _unavailable_analysis,
    analyze_coverage,
)
from app.agents.project_planning.subagents.decomposition.gate import classify_readiness
from app.agents.project_planning.subagents.decomposition.invest import validate_invest
from app.agents.project_planning.subagents.decomposition.scorer import (
    build_feedback,
    build_result,
)
from app.agents.project_planning.subagents.decomposition.state import DecompositionState

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 10
AGENT_TIMEOUT_SECONDS = 180.0

TOOL_INVEST_VALIDATOR = "invest_validator"
TOOL_COVERAGE_ANALYZER = "coverage_analyzer"
TOOL_PATTERN_RETRIEVER = "pattern_retriever"

_GATHER_TOOLS = (
    TOOL_COVERAGE_ANALYZER,
    TOOL_INVEST_VALIDATOR,
    TOOL_PATTERN_RETRIEVER,
)


def _invest_gate(invest_results: list[StoryInvest]) -> InvestGateResult:
    failed = [r.story_id for r in invest_results if not r.story_ready]
    return InvestGateResult(all_stories_ready=not failed, failed_stories=failed)


# --- nodes ------------------------------------------------------------------

def reason(state: DecompositionState) -> DecompositionState:
    iterations = state.get("iterations", 0) + 1
    tools_run = state.get("tools_run", [])
    next_gather = next((t for t in _GATHER_TOOLS if t not in tools_run), None)
    pending = next_gather if iterations <= MAX_ITERATIONS else None
    return {"pending_tool": pending, "iterations": iterations}


async def execute_tool(state: DecompositionState) -> DecompositionState:
    tool = state.get("pending_tool")
    tools_run = [*state.get("tools_run", [])]

    def mark(name: str) -> None:
        if name not in tools_run:
            tools_run.append(name)

    if tool == TOOL_COVERAGE_ANALYZER:
        mark(TOOL_COVERAGE_ANALYZER)
        coverage = await analyze_coverage(
            state["requirement_id"], state["requirement_text"], state.get("stories", [])
        )
        return {"coverage": coverage, "tools_run": tools_run}

    if tool == TOOL_INVEST_VALIDATOR:
        mark(TOOL_INVEST_VALIDATOR)
        try:
            results = await validate_invest(state["requirement_id"], state.get("stories", []))
        except Exception:
            logger.exception("invest_validator failed for %s", state.get("requirement_id"))
            results = []
        return {
            "invest_results": results,
            "invest_gate": _invest_gate(results),
            "tools_run": tools_run,
        }

    if tool == TOOL_PATTERN_RETRIEVER:
        mark(TOOL_PATTERN_RETRIEVER)
        try:
            patterns = await asyncio.to_thread(query_patterns, state["requirement_text"], 3)
        except Exception:
            logger.exception("pattern_retriever failed for %s", state.get("requirement_id"))
            patterns = []
        return {"retrieved_patterns": patterns, "tools_run": tools_run}

    return {}


def finalize(state: DecompositionState) -> DecompositionState:
    coverage: CoverageAnalysis = state.get("coverage") or _unavailable_analysis(
        "Coverage was not assessed."
    )
    invest_results = state.get("invest_results", [])
    invest_gate = state.get("invest_gate") or _invest_gate(invest_results)
    patterns = state.get("retrieved_patterns", [])

    readiness, readiness_reason = classify_readiness(coverage, invest_results)
    feedback = build_feedback(readiness, coverage, invest_results)
    # Transparency signal only (not a gate input): low when coverage could not
    # actually be assessed (LLM unavailable/failed).
    confidence = 1.0 if coverage.elements else 0.3

    return {
        "result": build_result(
            state["requirement_id"],
            coverage,
            invest_results,
            invest_gate,
            readiness,
            readiness_reason,
            coverage.needs_review_reason,
            feedback,
            patterns,
            confidence=confidence,
        )
    }


# --- edges ------------------------------------------------------------------

def route_after_reason(state: DecompositionState) -> str:
    return "execute_tool" if state.get("pending_tool") else "finalize"


def _build_graph():
    g = StateGraph(DecompositionState)
    g.add_node("reason", reason)
    g.add_node("execute_tool", execute_tool)
    g.add_node("finalize", finalize)
    g.add_edge(START, "reason")
    g.add_conditional_edges("reason", route_after_reason, ["execute_tool", "finalize"])
    g.add_edge("execute_tool", "reason")
    g.add_edge("finalize", END)
    return g.compile()


_GRAPH = _build_graph()


async def run_decomposition_agent(
    payload: AnalyzeDecompositionInput,
) -> DecompositionResult:
    """Run the gather-then-finalize graph for one decomposition analysis; fall
    back to a safe structural result (never a false COMPLETE) on error/timeout."""
    stories_dicts = [
        {
            "id": s.id,
            "title": s.title,
            "description": s.description,
            "linked_parent_requirement": s.linked_parent_requirement or payload.requirement.id,
        }
        for s in payload.stories
    ]

    initial: DecompositionState = {
        "requirement_id": payload.requirement.id,
        "requirement_text": payload.requirement.text,
        "stories": stories_dicts,
        "threshold": payload.options.threshold,
        "tools_run": [],
        "iterations": 0,
    }
    try:
        final = await asyncio.wait_for(_GRAPH.ainvoke(initial), timeout=AGENT_TIMEOUT_SECONDS)
        result = final.get("result")
        if result is not None:
            return result
        logger.warning(
            "Decomposition graph produced no result for %s; falling back", payload.requirement.id
        )
    except Exception:
        logger.exception(
            "Decomposition graph failed for %s; falling back", payload.requirement.id
        )

    # Fail-safe fallback: never silently claim COMPLETE when the graph itself
    # errored out. INVEST rule signals are cheap/local, so still run them for
    # partial, useful feedback even though coverage couldn't be assessed.
    try:
        invest_results = await validate_invest(payload.requirement.id, stories_dicts)
    except Exception:
        logger.exception("INVEST fallback also failed for %s", payload.requirement.id)
        invest_results = []

    coverage = _unavailable_analysis("Decomposition analysis failed — please re-run analysis.")
    invest_gate = _invest_gate(invest_results)
    readiness, readiness_reason = classify_readiness(coverage, invest_results)
    feedback = build_feedback(readiness, coverage, invest_results)
    return build_result(
        payload.requirement.id,
        coverage,
        invest_results,
        invest_gate,
        readiness,
        readiness_reason,
        coverage.needs_review_reason,
        feedback,
        [],
        confidence=0.0,
    )
