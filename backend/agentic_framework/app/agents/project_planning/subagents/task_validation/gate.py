"""The task-validation sub-agent's student-friendly, three-tier readiness
classification. Mirrors decomposition/gate.py exactly, scoped to one story's
task set:
  - Coverage (does the task set cover the story's main work) dominates the
    tier. A significant coverage gap -> Coverage Warning, regardless of how
    clean the individual tasks are.
  - Per-task criteria (relevance/scope/actionability/duplication) are
    improvement guidance. They can at most downgrade Valid -> Needs
    Improvement; they never force Coverage Warning on their own.
  - ALL THREE tiers allow the student to proceed to effort estimation. There
    is no hard block.
"""

from __future__ import annotations

from app.agents.project_planning.schemas import (
    TaskReadiness,
    TaskSetCoverage,
    TaskValidationItem,
)

# A task set this small tolerates a slightly lower coverage estimate before
# it counts as a "major" gap - a single missing step on a 2-task story is
# proportionally worse than on an 8-task one, but LLM coverage estimates are
# noisier than the deterministic coverage % used in decomposition, so the
# cutoffs here are intentionally a bit more forgiving.
_MAJOR_GAP_COVERAGE_PCT = 55.0
_MINOR_GAP_COVERAGE_PCT = 80.0


def classify_task_readiness(
    coverage: TaskSetCoverage,
    items: list[TaskValidationItem],
    *,
    analysis_failed: bool = False,
    failure_reason: str | None = None,
) -> tuple[TaskReadiness, str]:
    """Return (readiness, readiness_reason). Never raises, never blocks."""
    if analysis_failed:
        return (
            TaskReadiness.COVERAGE_WARNING,
            failure_reason or "Task validation could not be completed — see the system error below.",
        )

    if not items:
        return (
            TaskReadiness.COVERAGE_WARNING,
            "No tasks have been written yet for this story.",
        )

    coverage_pct = coverage.coverage_percentage
    not_ready_count = sum(1 for i in items if not i.task_ready)

    major_coverage_gap = coverage_pct < _MAJOR_GAP_COVERAGE_PCT or len(coverage.missing_work_items) >= 2
    minor_coverage_gap = (
        _MAJOR_GAP_COVERAGE_PCT <= coverage_pct < _MINOR_GAP_COVERAGE_PCT
        or len(coverage.missing_work_items) == 1
    )

    if major_coverage_gap:
        return (
            TaskReadiness.COVERAGE_WARNING,
            (
                f"Coverage is {coverage_pct:.0f}% — the task list is missing work the "
                "story needs. See the missing items below."
            ),
        )

    if minor_coverage_gap:
        return (
            TaskReadiness.NEEDS_IMPROVEMENT,
            f"Coverage is {coverage_pct:.0f}% — mostly there, a few gaps remain.",
        )

    # Coverage is solid at this point; per-task criteria only ever downgrade
    # one tier, same as INVEST does for decomposition readiness.
    if not_ready_count > 0:
        return (
            TaskReadiness.NEEDS_IMPROVEMENT,
            (
                f"Coverage is solid ({coverage_pct:.0f}%), but {not_ready_count} of "
                f"{len(items)} task{'' if len(items) == 1 else 's'} could be improved "
                "— see the suggestions below."
            ),
        )

    return (
        TaskReadiness.VALID,
        f"Coverage is {coverage_pct:.0f}% and every task is estimation-ready.",
    )
