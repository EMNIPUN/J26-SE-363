"""Tests for discrepancy detection node (T5.8 & PLAN.md Section 9 Node 9)."""

import pytest
from app.agents.performance_assessment.com_agent.state import FactorOutput
from app.agents.performance_assessment.com_agent.nodes.discrepancy_node import (
    discrepancy_detection_node,
)


@pytest.mark.asyncio
async def test_discrepancy_node_critical_triggers_human_review():
    state = {
        "factor_scores": {
            "effort": FactorOutput(score=0.85),
            "code_ownership": FactorOutput(
                score=0.20,
                features={"ko_raw_score": 0.20},
            ),
        }
    }

    updates = await discrepancy_detection_node(state)
    assert updates["current_step"] == "discrepancy_checked"
    assert len(updates["discrepancy_flags"]) >= 1
    assert updates["requires_human_review"] is True
    alert = updates["discrepancy_flags"][0]
    assert alert.alert_code == "GHOSTWRITER_SUSPICION"
    assert alert.severity == "CRITICAL"


@pytest.mark.asyncio
async def test_discrepancy_node_warning_does_not_trigger_human_review():
    # Deadline panic is a WARNING, not CRITICAL
    state = {
        "factor_scores": {
            "effort": FactorOutput(score=0.75),
            "consistency": FactorOutput(score=0.20),
            "code_ownership": FactorOutput(score=0.70),
        }
    }

    updates = await discrepancy_detection_node(state)
    assert updates["current_step"] == "discrepancy_checked"
    assert len(updates["discrepancy_flags"]) == 1
    assert updates["discrepancy_flags"][0].alert_code == "DEADLINE_PANIC"
    assert updates["discrepancy_flags"][0].severity == "WARNING"
    # WARNING alone does not halt pipeline for HITL review
    assert updates["requires_human_review"] is False


@pytest.mark.asyncio
async def test_discrepancy_node_normal_profile():
    state = {
        "factor_scores": {
            "effort": FactorOutput(score=0.70),
            "consistency": FactorOutput(score=0.70),
            "collaboration": FactorOutput(score=0.70),
            "code_ownership": FactorOutput(score=0.70),
        }
    }

    updates = await discrepancy_detection_node(state)
    assert updates["current_step"] == "discrepancy_checked"
    assert len(updates["discrepancy_flags"]) == 0
    assert updates["requires_human_review"] is False
