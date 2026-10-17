"""The decomposition sub-agent's student-friendly, three-tier readiness
classification.

Replaces the old two-level MANDATORY pass/fail gate (Coverage Gate C1-C10 then
INVEST Gate, either of which could hard-block progression). That gate could
deadlock a student: a borderline requirement with a stubborn tool failure, or
stories that were reasonable but imperfect on all ten checks plus all six
INVEST criteria, had no way forward except an indefinite block.

The new rule:
  - Coverage/traceability (C1-C10) is prioritized and dominates the tier,
    since it answers "does the decomposition actually cover the parent
    requirement" - the question that matters most before estimation.
  - INVEST is reduced to IMPROVEMENT GUIDANCE. It can at most downgrade
    Ready -> Ready with Improvements; it never forces Needs Attention on its
    own, and never blocks anything.
  - ALL THREE tiers allow the student to proceed to effort estimation. There
    is no hard block - Needs Attention is a loud warning with an explanation
    of what's missing, not a wall.
"""

from __future__ import annotations

from app.agents.project_planning.schemas import (
    CheckResult,
    CoverageAnalysis,
    DecompositionGateStatus,
    DecompositionReadiness,
    StoryInvest,
)

# A requirement this size or smaller tolerates 1 failed check before it counts
# as a "major" gap - a single missing element on a 3-element requirement is
# proportionally worse than on a 10-element one.
_MAJOR_GAP_FAILED_CHECKS = 3
_MAJOR_GAP_COVERAGE_PCT = 60.0
_MINOR_GAP_COVERAGE_PCT = 85.0


def classify_readiness(
    coverage: CoverageAnalysis,
    stories: list[StoryInvest],
) -> tuple[DecompositionReadiness, str]:
    """Return (readiness, readiness_reason). Never raises, never blocks."""
    if coverage.analysis_failed:
        return (
            DecompositionReadiness.NEEDS_ATTENTION,
            "Coverage analysis could not be completed — see the system error below.",
        )

    if not stories:
        return (
            DecompositionReadiness.NEEDS_ATTENTION,
            "No user stories have been written yet for this requirement.",
        )

    failed_checks = sum(1 for c in coverage.gate.checks.values() if c.result == CheckResult.FAIL)
    coverage_pct = coverage.coverage_percentage
    not_ready_count = sum(1 for s in stories if not s.story_ready)

    major_coverage_gap = (
        failed_checks >= _MAJOR_GAP_FAILED_CHECKS or coverage_pct < _MAJOR_GAP_COVERAGE_PCT
    )
    minor_coverage_gap = (
        0 < failed_checks < _MAJOR_GAP_FAILED_CHECKS
        or _MAJOR_GAP_COVERAGE_PCT <= coverage_pct < _MINOR_GAP_COVERAGE_PCT
    )

    if coverage.needs_review:
        return (
            DecompositionReadiness.NEEDS_ATTENTION,
            coverage.needs_review_reason
            or "This requirement needs a human judgment call before coverage can be fully confirmed.",
        )

    if major_coverage_gap:
        return (
            DecompositionReadiness.NEEDS_ATTENTION,
            (
                f"{failed_checks} coverage check(s) failed and coverage is "
                f"{coverage_pct:.0f}% — significant parts of the requirement are "
                "not yet represented by a story."
            ),
        )

    if minor_coverage_gap:
        return (
            DecompositionReadiness.READY_WITH_IMPROVEMENTS,
            (
                f"Coverage is {coverage_pct:.0f}% with {failed_checks} check(s) "
                "needing attention — mostly there, a few gaps remain."
            ),
        )

    # Coverage is solid at this point; INVEST only ever downgrades one tier.
    if not_ready_count > 0:
        return (
            DecompositionReadiness.READY_WITH_IMPROVEMENTS,
            (
                f"Coverage is solid ({coverage_pct:.0f}%), but {not_ready_count} of "
                f"{len(stories)} stor{'y' if len(stories) == 1 else 'ies'} could be "
                "improved for estimation — see the suggestions below."
            ),
        )

    return (
        DecompositionReadiness.READY,
        f"Coverage is {coverage_pct:.0f}% and every story is estimation-ready.",
    )


# Legacy projection — see DecompositionGateStatus's docstring. Nothing reads
# this to decide whether the student can proceed anymore; it exists only so
# older stored rows / any code still keying off the three old values degrades
# sensibly rather than breaking.
_LEGACY_MAP = {
    DecompositionReadiness.READY: DecompositionGateStatus.COMPLETE,
    DecompositionReadiness.READY_WITH_IMPROVEMENTS: DecompositionGateStatus.INCOMPLETE,
    DecompositionReadiness.NEEDS_ATTENTION: DecompositionGateStatus.INCOMPLETE,
}


def legacy_gate_status(
    readiness: DecompositionReadiness, needs_review: bool
) -> DecompositionGateStatus:
    if needs_review and readiness == DecompositionReadiness.NEEDS_ATTENTION:
        return DecompositionGateStatus.NEEDS_REVIEW
    return _LEGACY_MAP[readiness]
