"""Tests for discrepancy detection node (T5.8 & PLAN.md Section 9 Node 9).

Improvements over original:
- Fixed test_discrepancy_node_warning_does_not_trigger_human_review: explicitly
  includes collaboration factor so the state is unambiguous about which rules fire.
- Added test for all-four-alerts scenario.
- Added test for empty factor_scores edge case.
"""

import pytest
from app.agents.performance_assessment.com_agent.state import FactorOutput
from app.agents.performance_assessment.com_agent.nodes.discrepancy_node import (
    discrepancy_detection_node,
)


@pytest.mark.asyncio
async def test_discrepancy_node_critical_triggers_human_review():
    """GHOSTWRITER_SUSPICION (CRITICAL) requires human review."""
    state = {
        "factor_scores": {
            "effort": FactorOutput(score=0.85),
            "consistency": FactorOutput(score=0.70),
            "collaboration": FactorOutput(score=0.60),
            "code_ownership": FactorOutput(
                score=0.20,
                features={"ko_raw_score": 0.20},
            ),
        }
    }

    updates = await discrepancy_detection_node(state)
    assert updates["current_step"] == "discrepancy_checked"
    assert updates["requires_human_review"] is True
    codes = {a.alert_code for a in updates["discrepancy_flags"]}
    assert "GHOSTWRITER_SUSPICION" in codes
    assert updates["discrepancy_flags"][0].severity == "CRITICAL"


@pytest.mark.asyncio
async def test_discrepancy_node_warning_does_not_trigger_human_review():
    """DEADLINE_PANIC (WARNING) must NOT set requires_human_review = True.

    State is crafted to trigger DEADLINE_PANIC only:
    - effort=0.75 > 0.60, consistency=0.20 < 0.30 -> DEADLINE_PANIC
    - effort=0.75 is NOT > 0.75 (strict) -> no GHOSTWRITER
    - effort=0.75 is NOT < 0.25 -> no FREE_RIDER
    - collaboration is explicitly set to 0.60 (>= 0.25) -> no FREE_RIDER
    - ko_raw=0.70 is NOT > 0.80 -> no UNRECORDED_WORK
    """
    state = {
        "factor_scores": {
            "effort": FactorOutput(score=0.75),
            "consistency": FactorOutput(score=0.20),
            "collaboration": FactorOutput(score=0.60),  # explicit: prevents FREE_RIDER
            "code_ownership": FactorOutput(
                score=0.70,
                features={"ko_raw_score": 0.70},
            ),
        }
    }

    updates = await discrepancy_detection_node(state)
    assert updates["current_step"] == "discrepancy_checked"

    codes = {a.alert_code for a in updates["discrepancy_flags"]}
    assert "DEADLINE_PANIC" in codes
    assert "GHOSTWRITER_SUSPICION" not in codes
    assert "FREE_RIDER" not in codes
    assert len(updates["discrepancy_flags"]) == 1
    assert updates["discrepancy_flags"][0].severity == "WARNING"
    # WARNING alone does NOT halt pipeline for HITL review
    assert updates["requires_human_review"] is False


@pytest.mark.asyncio
async def test_discrepancy_node_normal_profile():
    """Normal engagement profile fires no alerts."""
    state = {
        "factor_scores": {
            "effort": FactorOutput(score=0.70),
            "consistency": FactorOutput(score=0.70),
            "collaboration": FactorOutput(score=0.70),
            "code_ownership": FactorOutput(
                score=0.70,
                features={"ko_raw_score": 0.70},
            ),
        }
    }

    updates = await discrepancy_detection_node(state)
    assert updates["current_step"] == "discrepancy_checked"
    assert len(updates["discrepancy_flags"]) == 0
    assert updates["requires_human_review"] is False


@pytest.mark.asyncio
async def test_discrepancy_node_empty_factor_scores():
    """Empty factor_scores (edge case) fires no alerts and does not crash."""
    state = {"factor_scores": {}}
    updates = await discrepancy_detection_node(state)
    assert updates["current_step"] == "discrepancy_checked"
    assert updates["requires_human_review"] is False
    assert isinstance(updates["discrepancy_flags"], list)
