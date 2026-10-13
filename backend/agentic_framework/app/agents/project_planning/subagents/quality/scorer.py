"""The ``dimension_scorer`` tool: score one requirement on the six IEEE 830 dims.

Primary path: Groq LLM (JSON mode), grounded by the deterministic smell detector.
Fallback path: a transparent heuristic so the component still works (degraded,
clearly flagged) when no key is set or Groq is unreachable — the demo never
hard-crashes.
"""

from __future__ import annotations

import logging

from app.agents.project_planning.llm import get_groq_client
from app.agents.project_planning.orchestrator.gates import evaluate_gate
from app.agents.project_planning.schemas import (
    QUALITY_DIMENSIONS,
    DimensionScore,
    RequirementInput,
    RequirementQualityResult,
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


async def score_requirement(
    req: RequirementInput,
    other_texts: list[str],
    threshold: int,
) -> RequirementQualityResult:
    smells = detect_smells(req.text)
    client = get_groq_client()

    if client.configured:
        try:
            data = await client.complete_json(
                SYSTEM_PROMPT,
                build_user_prompt(req.text, [s.span or s.type for s in smells], other_texts),
            )
            return _result_from_llm(req, smells, data, threshold)
        except Exception:
            logger.exception("Groq scoring failed for %s; using heuristic fallback", req.id)

    return _heuristic_result(req, smells, threshold)


def _result_from_llm(
    req: RequirementInput,
    smells: list[Smell],
    data: dict,
    threshold: int,
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
    confidence = float(data.get("confidence", 0.8) or 0.8)
    confidence = max(0.0, min(1.0, confidence))
    status, action, dart = evaluate_gate(overall, confidence, threshold)

    return RequirementQualityResult(
        id=req.id,
        overall_score=overall,
        status=status,
        gate_action=action,
        dimension_scores=dimension_scores,
        smells=smells,
        suggested_rewrite=(data.get("suggested_rewrite") or None),
        confidence=confidence,
        dart_triggered=dart,
    )


# --- deterministic fallback -------------------------------------------------

_SMELL_PENALTY = {
    "vague_term": 12,
    "weak_word": 10,
    "unbounded_quantifier": 8,
    "unquantified": 8,
    "passive_voice": 6,
    "no_obligation": 15,
}


def _heuristic_result(
    req: RequirementInput,
    smells: list[Smell],
    threshold: int,
) -> RequirementQualityResult:
    penalty = sum(_SMELL_PENALTY.get(s.type, 5) for s in smells)
    base = max(30, 95 - penalty)

    # Spread the penalty across the dimensions the smells most affect.
    note = "Heuristic fallback (LLM unavailable); scores are approximate."
    dimension_scores = {
        dim: DimensionScore(score=base, rationale=note, issues=[s.span for s in smells if s.span][:3])
        for dim in QUALITY_DIMENSIONS
    }
    overall = base
    confidence = 0.5  # deliberately low: this path is degraded
    status, action, dart = evaluate_gate(overall, confidence, threshold)

    return RequirementQualityResult(
        id=req.id,
        overall_score=overall,
        status=status,
        gate_action=action,
        dimension_scores=dimension_scores,
        smells=smells,
        suggested_rewrite=None,
        confidence=confidence,
        dart_triggered=dart,
    )
