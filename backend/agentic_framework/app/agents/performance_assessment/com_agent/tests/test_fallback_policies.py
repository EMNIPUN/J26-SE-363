"""Tests for fallback policies and weight redistribution (T3.3)."""

import pytest
from app.agents.performance_assessment.com_agent.state import FactorOutput
from app.agents.performance_assessment.com_agent.policies.fallback_policies import (
    get_fallback_for_factor,
    redistribute_weights,
    handle_zero_review_comments,
)


def test_get_fallback_for_factor():
    fb = get_fallback_for_factor("effort", error_message="Network timeout")
    assert isinstance(fb, FactorOutput)
    assert fb.score == 0.0
    assert fb.status == "fallback_applied"
    assert fb.error_message == "Network timeout"
    assert fb.evidence_traces == []
    assert fb.features == {}


def test_redistribute_weights_no_failures():
    original = {"w1": 0.2, "w2": 0.3, "w3": 0.5}
    res = redistribute_weights(original, failed_factors=[])
    assert res == original
    assert sum(res.values()) == pytest.approx(1.0)


def test_redistribute_weights_with_single_failure():
    # Remove w2 (0.3). Remaining w1 (0.2) and w3 (0.5), sum=0.7.
    # New w1 = 0.2 / 0.7 = 2/7 ≈ 0.285714
    # New w3 = 0.5 / 0.7 = 5/7 ≈ 0.714286
    original = {"w1": 0.2, "w2": 0.3, "w3": 0.5}
    res = redistribute_weights(original, failed_factors=["w2"])
    assert "w2" not in res
    assert "w1" in res and "w3" in res
    assert sum(res.values()) == pytest.approx(1.0, rel=1e-6)
    assert res["w1"] == pytest.approx(0.2 / 0.7, rel=1e-5)
    assert res["w3"] == pytest.approx(0.5 / 0.7, rel=1e-5)


def test_redistribute_weights_with_multiple_failures():
    original = {"w1": 0.2, "w2": 0.2, "w3": 0.2, "w4": 0.2, "w5": 0.2}
    res = redistribute_weights(original, failed_factors=["w1", "w3", "w5"])
    assert len(res) == 2
    assert "w2" in res and "w4" in res
    assert res["w2"] == pytest.approx(0.5, rel=1e-6)
    assert res["w4"] == pytest.approx(0.5, rel=1e-6)
    assert sum(res.values()) == pytest.approx(1.0)


def test_redistribute_weights_all_failures():
    original = {"w1": 0.5, "w2": 0.5}
    res = redistribute_weights(original, failed_factors=["w1", "w2"])
    assert res == {}


def test_handle_zero_review_comments():
    output = handle_zero_review_comments()
    assert isinstance(output, FactorOutput)
    assert output.score == 0.0
    assert output.status == "completed"  # Legitimate participation, not fallback
    assert output.error_message is None
    assert output.features.get("review_comment_count") == 0
    assert len(output.evidence_traces) >= 1


@pytest.mark.asyncio
async def test_all_passive_factors_fallback_pipeline_completes():
    """T8.4.4: All 5 passive factors fallback -> pipeline completes without exception."""
    from app.agents.performance_assessment.com_agent.fusion_engine.calculator import compute_additive_score
    weights = {
        "effort": 0.20,
        "consistency": 0.15,
        "requirement_fulfillment": 0.25,
        "collaboration": 0.15,
        "task_complexity": 0.10,
        "code_ownership": 0.15,
    }
    factor_scores = {
        "effort": get_fallback_for_factor("effort", "Scrum timeout"),
        "consistency": get_fallback_for_factor("consistency", "Git timeout"),
        "requirement_fulfillment": get_fallback_for_factor("requirement_fulfillment", "AC error"),
        "collaboration": get_fallback_for_factor("collaboration", "PR API error"),
        "task_complexity": get_fallback_for_factor("task_complexity", "DAG error"),
        "code_ownership": FactorOutput(score=0.80, status="completed"),
    }
    additive_score, audit = compute_additive_score(factor_scores, weights)
    assert additive_score == pytest.approx(0.80, abs=1e-4)
    assert len(audit["failed_factors"]) == 5
    assert audit["effective_weights"] == {"code_ownership": 1.0}

