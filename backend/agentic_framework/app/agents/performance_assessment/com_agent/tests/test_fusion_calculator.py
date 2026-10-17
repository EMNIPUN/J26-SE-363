"""Tests for deterministic mathematical fusion calculator (T3.1 & PLAN.md Section 9 Node 8).

Improvements over original:
- KO fusion cap test uses ASYMMETRIC scores to prove ko_fusion_score is used, not .score
- Added test for all-factors-failed (empty effective_weights) edge case
- Added identity case for apply_behavioral_modifier (1.0 * 1.0 = 1.0)
- Added test for dict-format factor_scores in build_radar_chart_data
"""

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

    # Expected: 0.20*0.80 + 0.15*0.70 + 0.25*0.90 + 0.15*0.60 + 0.10*0.75 + 0.15*0.85
    # = 0.16 + 0.105 + 0.225 + 0.09 + 0.075 + 0.1275 = 0.7825
    additive_score, audit = compute_additive_score(factor_scores, standard_weights)

    assert additive_score == pytest.approx(0.7825, abs=1e-4)
    assert audit["weights_sum"] == pytest.approx(1.0, abs=1e-5)
    assert audit["failed_factors"] == []
    assert len(audit["steps"]) == 6
    assert audit["steps"]["effort"]["factor_score"] == 0.80
    assert audit["steps"]["effort"]["weighted_contribution"] == pytest.approx(0.16)


def test_compute_additive_score_uses_ko_fusion_score_not_raw_score(standard_weights):
    """Prove ko_fusion_score is used instead of the FactorOutput.score for code_ownership.

    Uses ASYMMETRIC scores so coincidental equality can't mask the failure:
    - All other factors score at 0.80 (not 0.50)
    - code_ownership.score = 0.90 (would give high contribution)
    - ko_fusion_score = 0.50 (capped, should give lower contribution)

    Expected additive_score using ko_fusion_score=0.50:
      0.20*0.80 + 0.15*0.80 + 0.25*0.80 + 0.15*0.80 + 0.10*0.80 + 0.15*0.50
      = 0.16 + 0.12 + 0.20 + 0.12 + 0.08 + 0.075 = 0.755

    Expected if .score=0.90 were incorrectly used instead:
      0.15*0.90 = 0.135 → additive = 0.16 + 0.12 + 0.20 + 0.12 + 0.08 + 0.135 = 0.815
    """
    factor_scores = {
        "effort": FactorOutput(score=0.80),
        "consistency": FactorOutput(score=0.80),
        "requirement_fulfillment": FactorOutput(score=0.80),
        "collaboration": FactorOutput(score=0.80),
        "task_complexity": FactorOutput(score=0.80),
        "code_ownership": FactorOutput(
            score=0.90,
            features={"ko_raw_score": 0.90, "ko_fusion_score": 0.50},
        ),
    }

    additive_score, audit = compute_additive_score(factor_scores, standard_weights)

    # Must use ko_fusion_score=0.50 for code_ownership, not .score=0.90
    assert audit["steps"]["code_ownership"]["factor_score"] == 0.50
    assert additive_score == pytest.approx(0.755, abs=1e-4)
    # Sanity: confirm .score=0.90 would give a different (wrong) result
    assert additive_score != pytest.approx(0.815, abs=1e-4)


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

    assert "requirement_fulfillment" in audit["failed_factors"]
    assert "requirement_fulfillment" not in audit["effective_weights"]
    assert audit["weights_sum"] == pytest.approx(1.0, abs=1e-5)
    assert len(audit["effective_weights"]) == 5
    assert sum(audit["effective_weights"].values()) == pytest.approx(1.0)


def test_compute_additive_score_all_factors_failed():
    """All 6 factors in fallback → effective_weights is empty → score = 0.0."""
    weights = {
        "effort": 0.20, "consistency": 0.15, "requirement_fulfillment": 0.25,
        "collaboration": 0.15, "task_complexity": 0.10, "code_ownership": 0.15,
    }
    factor_scores = {
        name: FactorOutput(score=0.0, status="fallback_applied") for name in weights
    }

    additive_score, audit = compute_additive_score(factor_scores, weights)

    assert len(audit["failed_factors"]) == 6
    assert audit["effective_weights"] == {}
    assert additive_score == 0.0


def test_apply_behavioral_modifier_normal():
    # Positive persona bonus
    assert apply_behavioral_modifier(0.80, 1.10) == pytest.approx(0.88, abs=1e-4)
    # Negative persona penalty
    assert apply_behavioral_modifier(0.80, 0.85) == pytest.approx(0.68, abs=1e-4)
    # Identity case (modifier = 1.0)
    assert apply_behavioral_modifier(0.75, 1.00) == pytest.approx(0.75, abs=1e-6)


def test_apply_behavioral_modifier_upper_clamp():
    """0.95 * 1.20 = 1.14 → must be clamped to 1.0."""
    result = apply_behavioral_modifier(additive_score=0.95, bp_modifier=1.20)
    assert result == 1.0


def test_apply_behavioral_modifier_lower_clamp():
    """0.0 * 0.80 = 0.0 → stays 0.0 (at lower bound)."""
    result = apply_behavioral_modifier(additive_score=0.0, bp_modifier=0.80)
    assert result == 0.0


def test_build_radar_chart_data_from_factor_output():
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


def test_build_radar_chart_data_from_dict_format():
    """Radar chart must also handle dict-format factor_scores (not just FactorOutput)."""
    factor_scores = {
        "effort": {"score": 0.70},
        "consistency": {"score": 0.60},
        "requirement_fulfillment": {"score": 0.80},
        "collaboration": {"score": 0.55},
        "task_complexity": {"score": 0.65},
        "code_ownership": {"score": 0.75},
    }

    radar = build_radar_chart_data(factor_scores)
    assert isinstance(radar, dict)
    assert radar["effort"] == 0.70
    assert radar["code_ownership"] == 0.75
