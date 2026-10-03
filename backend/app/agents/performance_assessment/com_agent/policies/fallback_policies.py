"""Missing data and tool failure fallback policies for com_agent factors.

Strictly aligned with:
- BOARD.md T3.3 (T3.3.1 - T3.3.3)
- PLAN.md Section 9 (Node 3) & Section 12.6 (Factor Tool Error & Retry Policy)
"""

from typing import Dict, List, Optional
from app.agents.performance_assessment.com_agent.state import FactorOutput


def get_fallback_for_factor(
    factor_code: str, error_message: Optional[str] = None
) -> FactorOutput:
    """Return fallback FactorOutput when retries are exhausted or data is missing.

    Score is set to 0.0 with status 'fallback_applied' so weight redistribution
    or fallback rules can process it deterministically.
    """
    return FactorOutput(
        score=0.0,
        status="fallback_applied",
        evidence_traces=[],
        features={},
        error_message=error_message or f"Fallback applied for {factor_code} due to missing data or execution error",
    )


def redistribute_weights(
    weights: Dict[str, float], failed_factors: List[str]
) -> Dict[str, float]:
    """Redistribute weights of failed factors proportionally across remaining active factors.

    Ensures sum(weights.values()) == 1.0 after removing failed factors.
    If no factors failed, returns original weights unmodified.
    If all factors failed, returns empty dict.
    """
    failed_set = set(failed_factors)
    active = {k: float(v) for k, v in weights.items() if k not in failed_set}

    if not active:
        return {}

    if not failed_set.intersection(weights.keys()):
        # No weights need redistribution
        return dict(weights)

    active_sum = sum(active.values())
    if active_sum <= 0:
        return {}

    # Proportionally redistribute
    redistributed: Dict[str, float] = {}
    for k, v in active.items():
        redistributed[k] = v / active_sum

    # Ensure precision: normalize to strictly 1.0
    total = sum(redistributed.values())
    if total > 0 and total != 1.0:
        # Adjust largest weight for any tiny IEEE-754 precision delta
        max_k = max(redistributed, key=lambda k: redistributed[k])
        redistributed[max_k] += (1.0 - total)

    return redistributed


def handle_zero_review_comments() -> FactorOutput:
    """Handle the valid zero case for Factor 4 (Collaboration).

    Authoring 0 PR review comments is a legitimate non-participation state,
    not a system or connector error, so status is 'completed' with score 0.0.
    """
    return FactorOutput(
        score=0.0,
        status="completed",
        features={"review_comment_count": 0, "is_valid_zero": True},
        evidence_traces=[
            {
                "type": "collaboration_notice",
                "message": "Student authored 0 PR review comments during the sprint window",
            }
        ],
        error_message=None,
    )
