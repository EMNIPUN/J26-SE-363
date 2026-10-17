"""Decomposition scoring — 0-4 quality score AND student feedback both computed
in code from the coverage/INVEST evidence, with no LLM call. The research
methodology only requires the feedback to be specific and reference story/
element IDs; the coverage and INVEST LLM calls already produce exactly that
evidence (check rationale, per-criterion notes), so templating it avoids a
third LLM round-trip per analysis run with no loss of required information —
this was also the dominant source of Gemini free-tier quota exhaustion
(coverage + 1-per-story INVEST + this scorer call + a self-review call added
up fast; INVEST is now batched in invest.py and this call is removed
entirely, cutting a 3-story run from ~6 LLM calls down to 2)."""

from __future__ import annotations

from app.agents.project_planning.schemas import (
    CheckResult,
    CoverageAnalysis,
    DecompositionReadiness,
    DecompositionResult,
    InvestGateResult,
    InvestResult,
    QualityBand,
    StoryInvest,
)
from app.agents.project_planning.subagents.decomposition.gate import legacy_gate_status

_INVEST_CRITERIA = ("independent", "negotiable", "valuable", "estimable", "small", "testable")

_BAND_THRESHOLDS: tuple[tuple[float, QualityBand], ...] = (
    (3.5, QualityBand.EXCELLENT),
    (2.5, QualityBand.GOOD),
    (1.5, QualityBand.MODERATE),
    (0.5, QualityBand.POOR),
    (0.0, QualityBand.VERY_POOR),
)


def quality_band(score: float) -> QualityBand:
    for threshold, band in _BAND_THRESHOLDS:
        if score >= threshold:
            return band
    return QualityBand.VERY_POOR


def compute_quality_score(coverage: CoverageAnalysis, stories: list[StoryInvest]) -> float:
    """0-4 score, traceable to concrete gate artifacts. Feedback only — never
    overrides the readiness tier, but blends failed-check COUNT with raw
    coverage PERCENTAGE so the two reinforce each other (a requirement with
    several failed checks AND low coverage should score low on both signals,
    not just one) — keeps the score roughly consistent with the readiness
    tier from gate.py even though they're computed independently."""
    score = 4.0
    failed_checks = sum(1 for c in coverage.gate.checks.values() if c.result == CheckResult.FAIL)
    coverage_gap = max(0.0, (100.0 - coverage.coverage_percentage) / 100.0)  # 0..1
    score -= min(3.0, failed_checks * 0.25 + coverage_gap * 2.0)
    score -= min(0.5, len(coverage.gate.duplicate_elements) * 0.15)
    score -= min(0.5, len(coverage.gate.orphan_stories) * 0.2)

    not_ready = sum(1 for s in stories if not s.story_ready)
    score -= min(1.2, not_ready * (1.2 / max(len(stories), 1)))

    note_only = sum(
        1
        for s in stories
        if s.story_ready
        and any(getattr(s, c).result == InvestResult.PASS_WITH_NOTE for c in _INVEST_CRITERIA)
    )
    score -= min(0.5, note_only * 0.1)

    return max(0.0, round(score, 2))


_CRITERION_LABEL = {
    "independent": "Independent",
    "negotiable": "Negotiable",
    "valuable": "Valuable",
    "estimable": "Estimable",
    "small": "Small",
    "testable": "Testable",
}


def build_feedback(
    readiness: DecompositionReadiness,
    coverage: CoverageAnalysis,
    stories: list[StoryInvest],
) -> list[str]:
    """Actionable feedback bullets, ORDERED by priority — coverage/
    traceability issues first (per-check rationale + a concrete suggestion),
    then INVEST improvement notes per story (guidance, not gate failures).
    The frontend shows the first 3 prominently and the rest on request, so
    this function's ordering IS the prioritization — put the most important
    items first. No LLM call."""
    if coverage.analysis_failed:
        # The per-check "Fail" rows below are a placeholder state, not real
        # findings - lead with the actual cause instead of 10 duplicate lines.
        return [
            (
                "Coverage analysis could not be completed due to a system error "
                f"({coverage.failure_reason or 'the AI service was unavailable'}). "
                "This is not a real evaluation of your stories — please re-run "
                "analysis once the issue is resolved."
            ),
        ]

    feedback: list[str] = []

    # 1. Coverage/traceability — prioritized per the student-friendly gate
    # rules. Sorted by check_id for a stable, predictable order (C1 first).
    failed_checks = sorted(
        (c for c in coverage.gate.checks.values() if c.result == CheckResult.FAIL),
        key=lambda c: c.check_id,
    )
    for check in failed_checks:
        if not check.rationale:
            continue
        bullet = f"{check.check_id}: {check.rationale}"
        if check.suggestion:
            bullet += f" → {check.suggestion}"
        feedback.append(bullet)

    # 2. INVEST — improvement guidance per story, not a blocker. Skip
    # "Cannot Assess" (nothing actionable to say) and only surface real
    # Fail/note-worthy criteria.
    for story in stories:
        failing = [
            c for c in _INVEST_CRITERIA
            if getattr(story, c).result == InvestResult.FAIL
        ]
        notes = [
            c for c in _INVEST_CRITERIA
            if getattr(story, c).result == InvestResult.PASS_WITH_NOTE
        ]
        if failing:
            detail = "; ".join(
                f"{_CRITERION_LABEL[c]} — {getattr(story, c).note.strip().rstrip('.')}"
                for c in failing
                if getattr(story, c).note
            ) or ", ".join(_CRITERION_LABEL[c] for c in failing)
            feedback.append(f"{story.story_id}: could be improved on {detail}.")
        elif notes:
            detail = ", ".join(_CRITERION_LABEL[c] for c in notes)
            feedback.append(f"{story.story_id}: minor polish suggested on {detail}.")

    if not feedback:
        if readiness == DecompositionReadiness.READY:
            feedback.append("Coverage and story readiness both look solid — ready for effort estimation.")
        else:
            feedback.append("No specific issues were flagged, but the readiness tier suggests a second look — please review the checklist.")
    return feedback


def build_result(
    requirement_ref: str,
    coverage: CoverageAnalysis,
    stories: list[StoryInvest],
    invest_gate: InvestGateResult,
    readiness: DecompositionReadiness,
    readiness_reason: str,
    needs_review_reason: str | None,
    student_feedback: list[str],
    patterns: list[dict],
    confidence: float = 0.8,
) -> DecompositionResult:
    # A failed coverage analysis produces an all-Fail placeholder state that
    # compute_quality_score would otherwise turn into a plausible-looking but
    # meaningless number (e.g. "0.5/4") - force 0.0 so nothing downstream can
    # mistake it for a real score.
    score = 0.0 if coverage.analysis_failed else compute_quality_score(coverage, stories)
    needs_review = readiness == DecompositionReadiness.NEEDS_ATTENTION and bool(coverage.needs_review)
    gate_status = legacy_gate_status(readiness, needs_review)
    return DecompositionResult(
        requirement_ref=requirement_ref,
        coverage=coverage,
        stories=stories,
        invest_gate=invest_gate,
        decomposition_quality_score=score,
        quality_band=quality_band(score),
        readiness=readiness,
        readiness_reason=readiness_reason,
        gate_status=gate_status,
        needs_review_reason=needs_review_reason,
        student_feedback=student_feedback,
        patterns=patterns,
        confidence=max(0.0, min(1.0, confidence)),
        dart_triggered=needs_review,
        analysis_failed=coverage.analysis_failed,
        failure_reason=coverage.failure_reason,
        retrieval={"patterns": patterns},
    )
