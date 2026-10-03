"""Tests for deterministic fusion node (T5.7 & PLAN.md Section 9 Node 8)."""

import pytest
from app.agents.performance_assessment.com_agent.state import FactorOutput
from app.agents.performance_assessment.com_agent.nodes.fusion_node import (
    deterministic_fusion_node,
)


@pytest.mark.asyncio
async def test_deterministic_fusion_node_calculation():
    state = {
        "behavioral_persona": "Consistent Builder",
        "behavioral_modifier": 1.10,
        "weights_used": {
            "effort": 0.20,
            "consistency": 0.15,
            "requirement_fulfillment": 0.25,
            "collaboration": 0.15,
            "task_complexity": 0.10,
            "code_ownership": 0.15,
        },
        "factor_scores": {
            "effort": FactorOutput(score=0.80),
            "consistency": FactorOutput(score=0.70),
            "requirement_fulfillment": FactorOutput(score=0.90),
            "collaboration": FactorOutput(score=0.60),
            "task_complexity": FactorOutput(score=0.75),
            "code_ownership": FactorOutput(score=0.85),
        },
    }

    updates = await deterministic_fusion_node(state)

    assert updates["current_step"] == "fusion_complete"
    assert updates["additive_score"] == pytest.approx(0.7825, abs=1e-4)
    # final_score = 0.7825 * 1.10 = 0.86075 -> rounded to 0.8608
    assert updates["final_score"] == pytest.approx(0.8608, abs=1e-4)
    assert "calculation_audit_trail" in updates
    assert "radar_chart_data" in updates
    assert updates["radar_chart_data"]["effort"] == 0.80


@pytest.mark.asyncio
async def test_deterministic_fusion_node_clamping():
    state = {
        "behavioral_modifier": 1.20,
        "weights_used": {"effort": 1.0},
        "factor_scores": {"effort": FactorOutput(score=0.95)},
    }
    updates = await deterministic_fusion_node(state)
    assert updates["final_score"] == 1.0  # Clamped at 1.0
