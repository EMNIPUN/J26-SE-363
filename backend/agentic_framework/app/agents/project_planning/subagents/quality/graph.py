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
import re

from langgraph.graph import END, START, StateGraph

from app.agents.project_planning.knowledge import (
    cross_req_check,
    query_exemplars,
    query_standards,
)
from app.agents.project_planning.llm import get_llm_client
from app.agents.project_planning.schemas import (
    RequirementInput,
    RequirementQualityResult,
    RetrievalEvidence,
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
TOOL_STANDARD_RETRIEVER = "standard_retriever"
TOOL_EXEMPLAR_RETRIEVER = "exemplar_retriever"
TOOL_CROSS_REQ_CHECKER = "cross_req_checker"
TOOL_DIMENSION_SCORER = "dimension_scorer"

_TOKEN_RE = re.compile(r"[a-z0-9]{3,}")
_COMMON_TOKENS = {
    "shall", "must", "will", "system", "user", "users", "application",
    "software", "data", "from", "with", "when", "then", "that", "this",
}


def _meaningful_tokens(text: str) -> set[str]:
    return {
        token for token in _TOKEN_RE.findall(text.lower())
        if token not in _COMMON_TOKENS
    }


def _has_overlap_candidate(requirement_text: str, other_texts: list[str]) -> bool:
    """Cheap pre-filter for the expensive semantic cross-requirement checker.

    The checker is useful only when another requirement shares a substantial
    domain/action vocabulary. Generic SRS words ("system", "shall") do not
    count, so a batch of unrelated requirements does not invoke it N times.
    """
    source = _meaningful_tokens(requirement_text)
    if len(source) < 2:
        return False
    for other in other_texts:
        candidate = _meaningful_tokens(other)
        overlap = source & candidate
        if len(overlap) >= 2 and len(overlap) / min(len(source), len(candidate) or 1) >= 0.4:
            return True
    return False


def _needs_standards(smell_types: set[str]) -> bool:
    """Retrieve standards only when they are needed to explain a detected gap."""
    return bool(smell_types)


def _needs_exemplars(smell_types: set[str]) -> bool:
    """Examples help students revise wording/measurement problems, not clean text."""
    return bool(smell_types & {"vague_term", "weak_word", "unquantified", "no_obligation", "passive_voice"})


# --- nodes ------------------------------------------------------------------


def reason(state: QualityState) -> QualityState:
    """Select only the next evidence tool justified by the requirement's signals."""
    iterations = state.get("iterations", 0) + 1
    tools_run = state.get("tools_run", [])

    pending: str | None
    if iterations > MAX_ITERATIONS:
        pending = None  # safety: stop gathering, go reflect/finalize
    elif TOOL_SMELL_DETECTOR not in tools_run:
        # Always cheap, deterministic, and provides the signals used to choose
        # any optional RAG tools.
        pending = TOOL_SMELL_DETECTOR
    else:
        smell_types = {smell.type for smell in state.get("smells", [])}
        if _needs_standards(smell_types) and TOOL_STANDARD_RETRIEVER not in tools_run:
            pending = TOOL_STANDARD_RETRIEVER
        elif _needs_exemplars(smell_types) and TOOL_EXEMPLAR_RETRIEVER not in tools_run:
            pending = TOOL_EXEMPLAR_RETRIEVER
        elif (
            TOOL_CROSS_REQ_CHECKER not in tools_run
            and _has_overlap_candidate(state["requirement_text"], state.get("other_texts", []))
        ):
            pending = TOOL_CROSS_REQ_CHECKER
        elif TOOL_DIMENSION_SCORER not in tools_run or state.get("reflection_note"):
            # Every requirement is scored; retrieval augments this call only
            # when the preceding signals made it useful.
            pending = TOOL_DIMENSION_SCORER
        else:
            pending = None

    return {"pending_tool": pending, "iterations": iterations}


async def execute_tool(state: QualityState) -> QualityState:
    """Run the tool the reason step selected, writing its observation into state."""
    tool = state.get("pending_tool")
    tools_run = [*state.get("tools_run", [])]
    text = state["requirement_text"]

    def mark(name: str) -> None:
        if name not in tools_run:
            tools_run.append(name)

    if tool == TOOL_SMELL_DETECTOR:
        mark(TOOL_SMELL_DETECTOR)
        smells = detect_smells(text)
        return {"smells": smells, "smell_spans": [s.span or s.type for s in smells], "tools_run": tools_run}

    if tool == TOOL_STANDARD_RETRIEVER:
        mark(TOOL_STANDARD_RETRIEVER)
        return {"retrieved_standards": await _safe_retrieve(query_standards, text, state), "tools_run": tools_run}

    if tool == TOOL_EXEMPLAR_RETRIEVER:
        mark(TOOL_EXEMPLAR_RETRIEVER)
        return {"retrieved_exemplars": await _safe_retrieve(query_exemplars, text, state), "tools_run": tools_run}

    if tool == TOOL_CROSS_REQ_CHECKER:
        mark(TOOL_CROSS_REQ_CHECKER)
        try:
            hits = await asyncio.to_thread(cross_req_check, text, state.get("other_texts", []))
        except Exception:
            logger.exception("cross_req_checker failed for %s", state.get("requirement_id"))
            hits = []
        return {"cross_req_hits": hits, "tools_run": tools_run}

    if tool == TOOL_DIMENSION_SCORER:
        mark(TOOL_DIMENSION_SCORER)
        try:
            data = await request_dimension_scores(
                text,
                state.get("smell_spans", []),
                requirement_id=state.get("requirement_id", ""),
                standards=state.get("retrieved_standards"),
                exemplars=state.get("retrieved_exemplars"),
                cross_hits=state.get("cross_req_hits"),
                other_requirements=state.get("other_texts"),
                reflection_note=state.get("reflection_note"),
            )
            return {"dimensions_raw": data, "tools_run": tools_run, "reflection_note": None}
        except Exception:
            logger.exception("dimension_scorer tool failed for %s", state.get("requirement_id"))
            return {"scoring_failed": True, "tools_run": tools_run, "reflection_note": None}

    return {}  # no-op


async def _safe_retrieve(fn, text: str, state: QualityState) -> list[dict]:
    """Run a sync retrieval tool off the event loop; degrade to [] on failure."""
    try:
        return await asyncio.to_thread(fn, text, 3)
    except Exception:
        logger.exception("%s failed for %s", fn.__name__, state.get("requirement_id"))
        return []


async def reflect(state: QualityState) -> QualityState:
    """LLM self-evaluation: are the scores consistent with the evidence?

    May set a reflection_note (→ one re-score) and always records a calibrated
    confidence used by the gate.
    """
    if state.get("scoring_failed") or not state.get("dimensions_raw"):
        return {"reflection_note": None}

    reflect_count = state.get("reflect_count", 0) + 1
    client = get_llm_client()
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
                data,
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

    retrieval = RetrievalEvidence(
        standards=state.get("retrieved_standards") or [],
        exemplars=state.get("retrieved_exemplars") or [],
        cross_req_hits=state.get("cross_req_hits") or [],
    )

    if state.get("scoring_failed") or not state.get("dimensions_raw"):
        result = heuristic_result(
            req_id,
            smells,
            threshold,
            req_text=state.get("requirement_text", ""),
            other_texts=state.get("other_texts"),
            retrieval=retrieval,
        )
        result.tools_used = [*state.get("tools_run", []), "heuristic_scorer"]
        return {"result": result}

    result = build_result(
        req_id,
        smells,
        state["dimensions_raw"],
        threshold,
        confidence_override=state.get("reflection_confidence"),
        retrieval=retrieval,
    )
    result.tools_used = state.get("tools_run", [])
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
