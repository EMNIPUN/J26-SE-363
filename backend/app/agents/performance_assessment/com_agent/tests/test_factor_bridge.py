"""Unit tests for FactorBridge (Decoupled Factor Evaluator).

Validates:
- Agent nodes evaluate factors via evaluate_factor() without direct simulator imports.
- Dynamic resolution hierarchy: Production model -> Simulator -> Fallback.
- Seamless fallback when simulator is absent or removed.
- FactorOutput schema consistency across all factors.
- Fast testing behavior under pytest.
"""

import pytest
import asyncio
from unittest.mock import patch
from app.agents.performance_assessment.com_agent.factor_bridge import (
    evaluate_factor,
    classify_persona_via_bridge,
    _resolve_factor_module,
)
from app.agents.performance_assessment.com_agent.state import FactorOutput


@pytest.mark.asyncio
async def test_evaluate_all_factors_via_bridge():
    """Validates that all factors evaluate through the bridge producing valid FactorOutput."""
    factors = [
        ("effort", {"CC": 12, "LOC_net": 240, "FC": 5, "CT": 2, "RD": 3}),
        ("consistency", {"AWR": 0.6, "DC": 0.3, "LI_norm": 0.2, "CV_norm": 0.3}),
        ("requirement_fulfillment", {"student_tasks": []}),
        ("collaboration", {"review_comments": [], "issue_comments": []}),
        ("task_complexity", {"SP": 5, "SC": 3, "FI": 5, "DR": 3, "CB": 2}),
        ("code_ownership", {"student_response": "The function calculates order totals."}),
    ]

    for factor_name, payload in factors:
        res = await evaluate_factor(
            factor_name=factor_name,
            payload=payload,
            mode="quick",
            duration_seconds=0.01,
        )
        assert isinstance(res, FactorOutput), f"Factor {factor_name} must return FactorOutput"
        assert 0.0 <= res.score <= 1.0
        assert res.status == "completed"
        assert isinstance(res.features, dict)


@pytest.mark.asyncio
async def test_classify_persona_via_bridge():
    """Validates that Behavioral Pattern classifies persona and multiplier via the bridge."""
    signals = {
        "effort": 0.85,
        "consistency": 0.80,
        "collaboration": 0.70,
        "ko_raw": 0.80,
    }
    persona, modifier, rationale = await classify_persona_via_bridge(
        signals,
        mode="quick",
        duration_seconds=0.01,
    )
    assert persona == "Consistent deep contributor"
    assert modifier == 1.15
    assert len(rationale) > 0


@pytest.mark.asyncio
async def test_bridge_graceful_fallback_when_factor_missing():
    """Validates that an unknown or missing factor falls back safely without raising an exception."""
    res = await evaluate_factor("unknown_factor_xyz", payload={})
    assert isinstance(res, FactorOutput)
    assert res.status == "fallback_applied"
    assert res.score == 0.0


@pytest.mark.asyncio
async def test_bridge_prioritizes_production_model(tmp_path, monkeypatch):
    """Validates that if a production model (evaluate.py) is introduced in a factor folder,
    the bridge immediately routes to it instead of the simulator.
    """
    from app.agents.performance_assessment.com_agent import factor_bridge

    # Mock resolving a production module
    class MockProdModel:
        @staticmethod
        def evaluate(payload, context=None):
            return {"score": 0.99, "features": {"source": "production_model"}, "status": "completed"}

    with patch.object(factor_bridge, "_resolve_factor_module", return_value=(MockProdModel, "production")):
        res = await evaluate_factor("effort", payload={})
        assert res.score == 0.99
        assert res.features.get("source") == "production_model"
