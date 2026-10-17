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
    DecompositionGateStatus,
    DecompositionResult,
    InvestGateResult,
    InvestResult,
    QualityBand,
    StoryInvest,
)

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
    overrides the gate decision."""
    score = 4.0
    failed_checks = sum(1 for c in coverage.gate.checks.values() if c.result == CheckResult.FAIL)
    score -= min(2.0, failed_checks * 0.3)
    score -= min(1.0, len(coverage.gate.duplicate_elements) * 0.2)
    score -= min(1.0, len(coverage.gate.orphan_stories) * 0.3)

    not_ready = sum(1 for s in stories if not s.story_ready)
    score -= min(1.5, not_ready * (1.5 / max(len(stories), 1)))

    note_only = sum(
        1
        for s in stories
        if s.story_ready
        and any(getattr(s, c).result == InvestResult.PASS_WITH_NOTE for c in _INVEST_CRITERIA)
    )
    score -= min(0.5, note_only * 0.1)

    return max(0.0, round(score, 2))


def build_feedback(
    gate_status: DecompositionGateStatus,
    coverage: CoverageAnalysis,
    stories: list[StoryInvest],
) -> list[str]:
    """Specific, actionable feedback bullets built directly from the coverage/
    INVEST evidence — one bullet per failing check (citing its own rationale,
    already written by the coverage LLM call) and one per not-ready story
    (citing exactly which criteria failed). No LLM call."""
    if coverage.analysis_failed:
        # The per-check "Fail" rows below are a placeholder state, not real
        # findings - lead with the actual cause instead of 10 duplicate lines.
        return [
            "Coverage analysis could not be completed due to a system error "
            f"({coverage.failure_reason or 'the AI service was unavailable'}). "
            "This is not a real evaluation of your stories — please re-run "
            "analysis once the issue is resolved.",
        ]
    feedback: list[str] = []
    for check in coverage.gate.checks.values():
        if check.result == CheckResult.FAIL and check.rationale:
            feedback.append(f"{check.check_id}: {check.rationale}")
    for story in stories:
        if not story.story_ready:
            failing = [
                c for c in _INVEST_CRITERIA
                if getattr(story, c).result not in (InvestResult.PASS, InvestResult.PASS_WITH_NOTE)
            ]
            feedback.append(f"{story.story_id} is not ready — failing: {', '.join(failing)}")
    if not feedback:
        if gate_status == DecompositionGateStatus.COMPLETE:
            feedback.append("Coverage and story readiness both look solid — ready for effort estimation.")
        elif gate_status == DecompositionGateStatus.NEEDS_REVIEW:
            feedback.append("Coverage and story readiness look solid, but this requirement needs a human judgment call — see the reason above.")
        else:
            feedback.append("No specific issues were flagged, but the gate did not pass — please review the checklist and re-run analysis.")
    return feedback


def build_result(
    requirement_ref: str,
    coverage: CoverageAnalysis,
    stories: list[StoryInvest],
    invest_gate: InvestGateResult,
    gate_status: DecompositionGateStatus,
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
    return DecompositionResult(
        requirement_ref=requirement_ref,
        coverage=coverage,
        stories=stories,
        invest_gate=invest_gate,
        decomposition_quality_score=score,
        quality_band=quality_band(score),
        gate_status=gate_status,
        needs_review_reason=needs_review_reason,
        student_feedback=student_feedback,
        patterns=patterns,
        confidence=max(0.0, min(1.0, confidence)),
        dart_triggered=gate_status == DecompositionGateStatus.NEEDS_REVIEW,
        analysis_failed=coverage.analysis_failed,
        failure_reason=coverage.failure_reason,
        retrieval={"patterns": patterns},
    )
