"""Quality discrepancy and anomaly detection node for com_agent.

Strictly aligned with:
- BOARD.md T5.8 (T5.8.1)
- PLAN.md Section 9 Node 9 (discrepancy_detection_node)
"""

import logging
from typing import Dict, Any, List
from app.agents.performance_assessment.com_agent.state import DiscrepancyAlert
from app.agents.performance_assessment.com_agent.policies.discrepancy_rules import (
    run_all_discrepancy_checks,
    REQUIRES_HUMAN_REVIEW_SEVERITIES,
)

logger = logging.getLogger(__name__)


async def discrepancy_detection_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """T5.8.1: Node 9 — Quality Discrepancy & Anomaly Detection.

    Runs all four heuristic checks, stores discrepancy_flags in state,
    and sets requires_human_review = True if any alert has severity in REQUIRES_HUMAN_REVIEW_SEVERITIES (CRITICAL).
    """
    factor_scores = state.get("factor_scores", {})
    alerts: List[DiscrepancyAlert] = run_all_discrepancy_checks(factor_scores)

    # Double timeout anomaly check
    if state.get("quiz_is_double_timed_out"):
        alerts.append(
            DiscrepancyAlert(
                alert_code="DOUBLE_TIMEOUT",
                severity="CRITICAL",
                description="Student failed to complete active verification quiz within both 48h and +24h extension windows.",
                recommended_action="Conduct mandatory live oral examination to verify code authorship.",
            )
        )

    requires_human = any(
        alert.severity in REQUIRES_HUMAN_REVIEW_SEVERITIES for alert in alerts
    )

    return {
        "discrepancy_flags": alerts,
        "requires_human_review": requires_human,
        "current_step": "discrepancy_checked",
    }
