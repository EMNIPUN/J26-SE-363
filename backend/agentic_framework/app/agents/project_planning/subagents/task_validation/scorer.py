"""Task-validation scoring — 0-4 quality score AND student feedback both
computed in code from the validator's evidence, with no extra LLM call (the
single task_validator call already produces per-task criteria and set-level
coverage; templating the score/feedback from that avoids a second round-trip,
mirroring decomposition/scorer.py's quota discipline)."""

from __future__ import annotations

from app.agents.project_planning.schemas import (
    QualityBand,
    TaskCriterionOutcome,
    TaskReadiness,
    TaskSetCoverage,
    TaskValidationItem,
    TaskValidationResult,
)

_TASK_CRITERIA = ("relevance", "scope", "actionability", "duplication")

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


def compute_quality_score(coverage: TaskSetCoverage, items: list[TaskValidationItem]) -> float:
    """0-4 score, traceable to concrete validator evidence. Feedback only —
    never overrides the readiness tier, but blends the coverage gap with
    per-task readiness so the two reinforce each other."""
    score = 4.0
    coverage_gap = max(0.0, (100.0 - coverage.coverage_percentage) / 100.0)  # 0..1
    score -= min(2.5, coverage_gap * 2.5)
    score -= min(0.5, len(coverage.missing_work_items) * 0.25)

    not_ready = sum(1 for i in items if not i.task_ready)
    score -= min(1.5, not_ready * (1.5 / max(len(items), 1)))

    note_only = sum(
        1
        for i in items
        if i.task_ready
        and any(getattr(i, c).result == TaskCriterionOutcome.NEEDS_IMPROVEMENT for c in _TASK_CRITERIA)
    )
    score -= min(0.5, note_only * 0.1)

    return max(0.0, round(score, 2))


_CRITERION_LABEL = {
    "relevance": "Relevance",
    "scope": "Scope",
    "actionability": "Actionability",
    "duplication": "Duplication",
}


def build_feedback(
    readiness: TaskReadiness,
    coverage: TaskSetCoverage,
    items: list[TaskValidationItem],
    *,
    analysis_failed: bool = False,
    failure_reason: str | None = None,
) -> list[str]:
    """Actionable feedback bullets, ORDERED by priority — missing-coverage
    items first, then per-task criterion issues. The frontend shows the
    first 3 prominently and the rest on request, so this function's ordering
    IS the prioritization. No LLM call."""
    if analysis_failed:
        # The task list below is a placeholder state, not a real finding -
        # lead with the actual cause instead of misleading per-task bullets.
        return [
            (
                "Task validation could not be completed due to a system error "
                f"({failure_reason or 'the AI service was unavailable'}). This is not "
                "a real evaluation of your tasks — please re-run validation once the "
                "issue is resolved."
            ),
        ]

    feedback: list[str] = []

    # 1. Set-level coverage — the story's main work, prioritized first.
    for item_desc in coverage.missing_work_items:
        feedback.append(f"Missing from your task list: {item_desc}")

    # 2. Per-task criteria — improvement guidance, not a blocker. Skip
    # "Cannot Assess" (nothing actionable to say).
    for item in items:
        failing = [
            c for c in _TASK_CRITERIA
            if getattr(item, c).result == TaskCriterionOutcome.FAIL
        ]
        notes = [
            c for c in _TASK_CRITERIA
            if getattr(item, c).result == TaskCriterionOutcome.NEEDS_IMPROVEMENT
        ]
        if failing:
            detail = "; ".join(
                f"{_CRITERION_LABEL[c]} — {getattr(item, c).note.strip().rstrip('.')}"
                for c in failing
                if getattr(item, c).note
            ) or ", ".join(_CRITERION_LABEL[c] for c in failing)
            feedback.append(f"{item.task_id}: could be improved on {detail}.")
        elif notes:
            detail = ", ".join(_CRITERION_LABEL[c] for c in notes)
            feedback.append(f"{item.task_id}: minor polish suggested on {detail}.")

    if not feedback:
        if readiness == TaskReadiness.VALID:
            feedback.append("Your task breakdown looks solid — ready for effort estimation.")
        else:
            feedback.append(
                "No specific issues were flagged, but the readiness tier suggests a second look."
            )
    return feedback


def build_result(
    story_ref: str,
    coverage: TaskSetCoverage,
    items: list[TaskValidationItem],
    readiness: TaskReadiness,
    readiness_reason: str,
    student_feedback: list[str],
    *,
    analysis_failed: bool = False,
    failure_reason: str | None = None,
    confidence: float = 0.8,
) -> TaskValidationResult:
    # A failed validation run produces a placeholder 0% coverage state that
    # compute_quality_score would otherwise turn into a plausible-looking but
    # meaningless number - force 0.0 so nothing downstream mistakes it for a
    # real score.
    score = 0.0 if analysis_failed else compute_quality_score(coverage, items)
    return TaskValidationResult(
        story_ref=story_ref,
        coverage=coverage,
        tasks=items,
        quality_score=score,
        quality_band=quality_band(score),
        readiness=readiness,
        readiness_reason=readiness_reason,
        student_feedback=student_feedback,
        confidence=max(0.0, min(1.0, confidence)),
        analysis_failed=analysis_failed,
        failure_reason=failure_reason,
    )
