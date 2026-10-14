"""Quality scoring primitives, shared by the ReAct graph and the direct fallback.

- ``request_dimension_scores``: the LLM call behind the ``dimension_scorer`` tool.
- ``build_result``: turn raw LLM dimensions into a gated RequirementQualityResult.
- ``score_requirement``: single-shot direct path — the fallback used when the ReAct
  graph times out or errors, with a deterministic heuristic if the LLM is unavailable.
"""

from __future__ import annotations

import logging

from app.agents.project_planning.llm import get_llm_client
from app.agents.project_planning.orchestrator.gates import evaluate_gate
from app.agents.project_planning.schemas import (
    QUALITY_DIMENSIONS,
    DimensionScore,
    RequirementInput,
    RequirementQualityResult,
    RetrievalEvidence,
    Smell,
)
from app.agents.project_planning.subagents.quality.prompts import (
    SYSTEM_PROMPT,
    build_user_prompt,
)
from app.agents.project_planning.subagents.quality.smells import detect_smells

logger = logging.getLogger(__name__)


def _clamp_score(value: object) -> int:
    try:
        return max(0, min(100, round(float(value))))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 60


async def request_dimension_scores(
    requirement_text: str,
    smell_spans: list[str],
    *,
    standards: list[dict] | None = None,
    exemplars: list[dict] | None = None,
    cross_hits: list[dict] | None = None,
    reflection_note: str | None = None,
) -> dict:
    """Call the LLM for the six-dimension scores, grounded in the retrieved
    standards/exemplars/cross-requirement evidence. Returns the parsed JSON dict
    ({dimensions, confidence, suggested_rewrite}). Raises on failure/misconfig."""
    client = get_llm_client()
    return await client.complete_json(
        SYSTEM_PROMPT,
        build_user_prompt(requirement_text, smell_spans, standards, exemplars, cross_hits, reflection_note),
        max_tokens=2500,
    )


def build_result(
    req_id: str,
    smells: list[Smell],
    data: dict,
    threshold: int,
    confidence_override: float | None = None,
    retrieval: RetrievalEvidence | None = None,
) -> RequirementQualityResult:
    dims_in = data.get("dimensions", {})
    dimension_scores: dict[str, DimensionScore] = {}
    for dim in QUALITY_DIMENSIONS:
        raw = dims_in.get(dim, {}) if isinstance(dims_in, dict) else {}
        dimension_scores[dim] = DimensionScore(
            score=_clamp_score(raw.get("score")),
            rationale=str(raw.get("rationale", "")),
            issues=[str(i) for i in raw.get("issues", []) if i],
        )

    overall = round(sum(d.score for d in dimension_scores.values()) / len(dimension_scores))
    confidence = (
        confidence_override
        if confidence_override is not None
        else float(data.get("confidence", 0.8) or 0.8)
    )
    confidence = max(0.0, min(1.0, confidence))
    status, action, dart = evaluate_gate(overall, confidence, threshold)

    return RequirementQualityResult(
        id=req_id,
        overall_score=overall,
        status=status,
        gate_action=action,
        dimension_scores=dimension_scores,
        smells=smells,
        suggested_rewrite=(data.get("suggested_rewrite") or None),
        confidence=confidence,
        dart_triggered=dart,
        retrieval=retrieval,
    )


async def score_requirement(
    req: RequirementInput,
    other_texts: list[str],
    threshold: int,
) -> RequirementQualityResult:
    """Direct single-shot scoring (the ReAct graph's fallback)."""
    smells = detect_smells(req.text)
    client = get_llm_client()

    if client.configured:
        try:
            data = await request_dimension_scores(
                req.text, [s.span or s.type for s in smells]
            )
            return build_result(req.id, smells, data, threshold)
        except Exception:
            logger.exception("LLM scoring failed for %s; using heuristic fallback", req.id)

    return heuristic_result(req.id, smells, threshold)


# --- deterministic fallback -------------------------------------------------

_SMELL_PENALTY = {
    "vague_term": 12,
    "weak_word": 10,
    "unbounded_quantifier": 8,
    "unquantified": 8,
    "passive_voice": 6,
    "no_obligation": 15,
}


def heuristic_result(
    req_id: str,
    smells: list[Smell],
    threshold: int,
    retrieval: RetrievalEvidence | None = None,
) -> RequirementQualityResult:
    """Transparent, LLM-free scoring so the component degrades instead of crashing."""
    penalty = sum(_SMELL_PENALTY.get(s.type, 5) for s in smells)
    base = max(30, 95 - penalty)

    note = "Heuristic fallback (LLM unavailable); scores are approximate."
    dimension_scores = {
        dim: DimensionScore(score=base, rationale=note, issues=[s.span for s in smells if s.span][:3])
        for dim in QUALITY_DIMENSIONS
    }
    status, action, dart = evaluate_gate(base, 0.5, threshold)

    return RequirementQualityResult(
        id=req_id,
        overall_score=base,
        status=status,
        gate_action=action,
        dimension_scores=dimension_scores,
        smells=smells,
        suggested_rewrite=None,
        confidence=0.5,
        dart_triggered=dart,
        retrieval=retrieval,
    )
