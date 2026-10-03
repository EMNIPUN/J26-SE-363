"""Rule-based anomaly heuristics and discrepancy alerts for com_agent.

Strictly aligned with:
- BOARD.md T3.4 (T3.4.1 - T3.4.6)
- PLAN.md Section 9 Node 9 (Discrepancy & Anomaly Detection)
- state.py DiscrepancyAlert Pydantic model
"""

from typing import Dict, List, Optional, Any, Union
from app.agents.performance_assessment.com_agent.state import (
    DiscrepancyAlert,
    FactorOutput,
)

REQUIRES_HUMAN_REVIEW_SEVERITIES = ["CRITICAL"]


def check_ghostwriter_suspicion(effort: float, ko_raw: float) -> Optional[DiscrepancyAlert]:
    """Flag critical discrepancy when high effort is paired with very low comprehension.

    Trigger condition: effort > 0.75 and ko_raw < 0.35.
    """
    if effort > 0.75 and ko_raw < 0.35:
        return DiscrepancyAlert(
            alert_code="GHOSTWRITER_SUSPICION",
            severity="CRITICAL",
            description=(
                f"High code contribution effort ({effort:.2f}) contradicts very low "
                f"code comprehension ({ko_raw:.2f}). Potential proxy commit authoring or ghostwriting."
            ),
            recommended_action=(
                "Mandatory oral interview with student. Verify conceptual code ownership "
                "before releasing final sprint grade."
            ),
        )
    return None


def check_deadline_panic(consistency: float, effort: float) -> Optional[DiscrepancyAlert]:
    """Flag warning when code submission is highly clustered right before sprint cut-off.

    Trigger condition: consistency < 0.30 and effort > 0.60.
    """
    if consistency < 0.30 and effort > 0.60:
        return DiscrepancyAlert(
            alert_code="DEADLINE_PANIC",
            severity="WARNING",
            description=(
                f"High volume of code ({effort:.2f}) submitted in an irregular, last-minute burst "
                f"(consistency score: {consistency:.2f})."
            ),
            recommended_action=(
                "Review commit timestamps against sprint milestone schedule. Provide time "
                "management coaching."
            ),
        )
    return None


def check_free_rider(effort: float, collaboration: float) -> Optional[DiscrepancyAlert]:
    """Flag warning when both individual code contribution and team collaboration are deficient.

    Trigger condition: effort < 0.25 and collaboration < 0.25.
    """
    if effort < 0.25 and collaboration < 0.25:
        return DiscrepancyAlert(
            alert_code="FREE_RIDER",
            severity="WARNING",
            description=(
                f"Extremely low individual effort ({effort:.2f}) and near-zero peer engagement "
                f"({collaboration:.2f}). High risk of disengagement or free-riding."
            ),
            recommended_action=(
                "Intervene with student and team lead to assess sprint impediments or project disengagement."
            ),
        )
    return None


def check_unrecorded_work(
    effort: float, ko_raw: float, consistency: float
) -> Optional[DiscrepancyAlert]:
    """Flag informational notice when student has high ownership but low git commit footprint.

    Trigger condition: ko_raw > 0.80 and effort < 0.40 and consistency < 0.40.
    """
    if ko_raw > 0.80 and effort < 0.40 and consistency < 0.40:
        return DiscrepancyAlert(
            alert_code="UNRECORDED_WORK",
            severity="INFO",
            description=(
                f"Demonstrated deep code ownership ({ko_raw:.2f}) despite low logged git "
                f"activity ({effort:.2f}). Work may have been committed through teammate accounts or pair programming."
            ),
            recommended_action=(
                "Check Scrum meeting notes and inquire about pair-programming or architectural advisory role."
            ),
        )
    return None


def run_all_discrepancy_checks(
    factor_scores: Dict[str, Union[FactorOutput, Dict[str, Any], float]]
) -> List[DiscrepancyAlert]:
    """Run all four rule-based heuristic checks against extracted factor scores.

    Returns:
        List of generated DiscrepancyAlert instances.
    """

    def _extract_score(factor_name: str) -> float:
        val = factor_scores.get(factor_name)
        if val is None:
            return 0.0
        if hasattr(val, "score"):
            return float(getattr(val, "score"))
        if isinstance(val, dict):
            return float(val.get("score", 0.0))
        return float(val)

    def _extract_ko_raw() -> float:
        val = factor_scores.get("code_ownership")
        if val is None:
            return 0.0
        if hasattr(val, "features"):
            features = getattr(val, "features") or {}
            if "ko_raw_score" in features:
                return float(features["ko_raw_score"])
        elif isinstance(val, dict):
            features = val.get("features", {})
            if "ko_raw_score" in features:
                return float(features["ko_raw_score"])
        return _extract_score("code_ownership")

    effort = _extract_score("effort")
    consistency = _extract_score("consistency")
    collaboration = _extract_score("collaboration")
    ko_raw = _extract_ko_raw()

    alerts: List[DiscrepancyAlert] = []

    a1 = check_ghostwriter_suspicion(effort=effort, ko_raw=ko_raw)
    if a1:
        alerts.append(a1)

    a2 = check_deadline_panic(consistency=consistency, effort=effort)
    if a2:
        alerts.append(a2)

    a3 = check_free_rider(effort=effort, collaboration=collaboration)
    if a3:
        alerts.append(a3)

    a4 = check_unrecorded_work(effort=effort, ko_raw=ko_raw, consistency=consistency)
    if a4:
        alerts.append(a4)

    return alerts
