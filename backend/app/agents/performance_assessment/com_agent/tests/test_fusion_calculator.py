"""Tests for deterministic mathematical fusion calculator (T3.1 & PLAN.md Section 9 Node 8)."""

import pytest
from app.agents.performance_assessment.com_agent.state import FactorOutput
from app.agents.performance_assessment.com_agent.fusion_engine.calculator import (
    compute_additive_score,
    apply_behavioral_modifier,
    build_radar_chart_data,
)


@pytest.fixture
def standard_weights():
    return {
        "effort": 0.20,
        "consistency": 0.15,
        "requirement_fulfillment": 0.25,
        "collaboration": 0.15,
        "task_complexity": 0.10,
        "code_ownership": 0.15,
    }


def test_compute_additive_score_normal(standard_weights):
    factor_scores = {
        "effort": FactorOutput(score=0.80),
        "consistency": FactorOutput(score=0.70),
        "requirement_fulfillment": FactorOutput(score=0.90),
        "collaboration": FactorOutput(score=0.60),
        "task_complexity": FactorOutput(score=0.75),
        "code_ownership": FactorOutput(score=0.85),
    }

    # Expected calculation:
    # 0.20*0.80 + 0.15*0.70 + 0.25*0.90 + 0.15*0.60 + 0.10*0.75 + 0.15*0.85
    # = 0.16 + 0.105 + 0.225 + 0.09 + 0.075 + 0.1275 = 0.7825
    additive_score, audit = compute_additive_score(factor_scores, standard_weights)

    assert additive_score == pytest.approx(0.7825, abs=1e-4)
    assert audit["weights_sum"] == pytest.approx(1.0, abs=1e-5)
    assert audit["failed_factors"] == []
    assert len(audit["steps"]) == 6
    assert audit["steps"]["effort"]["factor_score"] == 0.80
    assert audit["steps"]["effort"]["weighted_contribution"] == pytest.approx(0.16)


def test_compute_additive_score_uses_ko_fusion_score_override(standard_weights):
    # Raw score is 0.90, but capped score in features is 0.50 due to quiz extension
    factor_scores = {
        "effort": FactorOutput(score=0.50),
        "consistency": FactorOutput(score=0.50),
        "requirement_fulfillment": FactorOutput(score=0.50),
        "collaboration": FactorOutput(score=0.50),
        "task_complexity": FactorOutput(score=0.50),
        "code_ownership": FactorOutput(
            score=0.90,
            features={"ko_raw_score": 0.90, "ko_fusion_score": 0.50},
        ),
    }

    additive_score, audit = compute_additive_score(factor_scores, standard_weights)
    # Since all effective scores are 0.50 and weights sum to 1.0, result must be exactly 0.50
    assert additive_score == pytest.approx(0.50, abs=1e-4)
    assert audit["steps"]["code_ownership"]["factor_score"] == 0.50


def test_compute_additive_score_with_fallback_redistribution(standard_weights):
    factor_scores = {
        "effort": FactorOutput(score=0.80),
        "consistency": FactorOutput(score=0.70),
        "requirement_fulfillment": FactorOutput(score=0.0, status="fallback_applied"),
        "collaboration": FactorOutput(score=0.60),
        "task_complexity": FactorOutput(score=0.75),
        "code_ownership": FactorOutput(score=0.85),
    }

    additive_score, audit = compute_additive_score(factor_scores, standard_weights)

    # requirement_fulfillment (0.25) failed, remaining 0.75 weight redistributed
    assert "requirement_fulfillment" in audit["failed_factors"]
    assert "requirement_fulfillment" not in audit["effective_weights"]
    assert audit["weights_sum"] == pytest.approx(1.0, abs=1e-5)
    assert len(audit["effective_weights"]) == 5
    assert sum(audit["effective_weights"].values()) == pytest.approx(1.0)


def test_apply_behavioral_modifier():
    # Regular multiplier
    score = apply_behavioral_modifier(additive_score=0.80, bp_modifier=1.10)
    assert score == pytest.approx(0.88, abs=1e-4)

    # Negative persona penalty
    penalty_score = apply_behavioral_modifier(additive_score=0.80, bp_modifier=0.85)
    assert penalty_score == pytest.approx(0.68, abs=1e-4)

    # Upper clamping at 1.0
    clamped_high = apply_behavioral_modifier(additive_score=0.95, bp_modifier=1.20)
    assert clamped_high == 1.0

    # Lower clamping at 0.0
    clamped_low = apply_behavioral_modifier(additive_score=0.0, bp_modifier=0.80)
    assert clamped_low == 0.0


def test_build_radar_chart_data():
    factor_scores = {
        "effort": FactorOutput(score=0.7423),
        "consistency": FactorOutput(score=0.6128),
        "requirement_fulfillment": FactorOutput(score=0.8500),
        "collaboration": FactorOutput(score=0.5500),
        "task_complexity": FactorOutput(score=0.6800),
        "code_ownership": FactorOutput(score=0.7900),
    }

    radar = build_radar_chart_data(factor_scores)
    assert isinstance(radar, dict)
    assert len(radar) == 6
    assert radar["effort"] == 0.7423
    assert radar["consistency"] == 0.6128
    assert radar["requirement_fulfillment"] == 0.85
