"""Decomposition scoring — LLM overall judgment + gate application + heuristic fallback."""

from __future__ import annotations

import logging

from app.agents.project_planning.llm import get_llm_client
from app.agents.project_planning.orchestrator.gates import evaluate_gate
from app.agents.project_planning.schemas import (
    CoverageAspect,
    DecompositionResult,
    StoryInvest,
)
from app.agents.project_planning.subagents.decomposition.prompts import (
    SCORER_SYSTEM,
    build_scorer_prompt,
)

logger = logging.getLogger(__name__)


def _clamp(value: object, lo: int = 0, hi: int = 100) -> int:
    try:
        return max(lo, min(hi, round(float(value))))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 50


async def request_decomposition_score(
    requirement_text: str,
    coverage: float,
    gaps: list[dict],
    invest_results: list[dict],
    patterns: list[dict] | None = None,
    reflection_note: str | None = None,
) -> dict:
    client = get_llm_client()
    return await client.complete_json(
        SCORER_SYSTEM,
        build_scorer_prompt(requirement_text, coverage, gaps, invest_results, patterns, reflection_note),
        max_tokens=400,
    )


def build_result(
    requirement_ref: str,
    invest_results: list[StoryInvest],
    coverage: float,
    aspects: list[dict],
    patterns: list[dict],
    score_data: dict,
    threshold: int,
    confidence_override: float | None = None,
) -> DecompositionResult:
    overall = _clamp(score_data.get("overall_score", 50))
    confidence = confidence_override if confidence_override is not None else float(score_data.get("confidence", 0.8) or 0.8)
    confidence = max(0.0, min(1.0, confidence))
    status, action, dart = evaluate_gate(overall, confidence, threshold)

    covered_aspects = [CoverageAspect(id=a["id"], label=a["label"], covered=True) for a in aspects if a.get("covered")]
    gap_aspects = [CoverageAspect(id=a["id"], label=a["label"], covered=False) for a in aspects if not a.get("covered")]

    return DecompositionResult(
        requirement_ref=requirement_ref,
        overall_score=overall,
        status=status,
        gate_action=action,
        coverage=round(coverage, 3),
        aspects=covered_aspects + gap_aspects,
        gaps=gap_aspects,
        stories=invest_results,
        patterns=patterns,
        summary=str(score_data.get("summary", "")),
        confidence=confidence,
        dart_triggered=dart,
        retrieval={"patterns": patterns},
    )


def heuristic_result(
    requirement_ref: str,
    invest_results: list[StoryInvest],
    coverage: float,
    aspects: list[dict],
    threshold: int,
) -> DecompositionResult:
    """Deterministic fallback using the mock's formula: coverage*60 + invest_pass_rate*40."""
    pass_rate = (
        sum(1 for r in invest_results if r.overall_pass) / len(invest_results)
        if invest_results
        else 0.0
    )
    score = round(coverage * 60 + pass_rate * 40)

    if coverage >= 0.8 and pass_rate == 1.0:
        summary = "Coverage and story quality both look solid — ready to move forward."
    elif coverage < 0.8 and pass_rate == 1.0:
        summary = "Your existing stories are individually well-formed, but the decomposition is incomplete."
    elif coverage >= 0.8 and pass_rate < 1.0:
        summary = "Coverage looks complete, but at least one story needs to be better-formed first."
    else:
        summary = "Both a coverage gap and story-formation issues need attention."

    status, action, dart = evaluate_gate(score, 0.5, threshold)

    covered_aspects = [CoverageAspect(id=a["id"], label=a["label"], covered=True) for a in aspects if a.get("covered")]
    gap_aspects = [CoverageAspect(id=a["id"], label=a["label"], covered=False) for a in aspects if not a.get("covered")]

    return DecompositionResult(
        requirement_ref=requirement_ref,
        overall_score=score,
        status=status,
        gate_action=action,
        coverage=round(coverage, 3),
        aspects=covered_aspects + gap_aspects,
        gaps=gap_aspects,
        stories=invest_results,
        patterns=[],
        summary=summary,
        confidence=0.5,
        dart_triggered=dart,
        retrieval={},
    )
