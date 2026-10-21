"""Shared fixtures for the com_agent tests.

The Code Ownership answer rating lives in ``factor_models/07_code_ownership`` (frozen code encoder + trained head) and needs torch, transformers and scikit-learn plus the
encoder weights, which the agent's test environment does not have. The flow tests below check the agent (timeouts, caps, fusion, review), so the rating step alone is stubbed
here; every other factor goes through the real bridge. The rating itself is tested in ``factor_models/07_code_ownership/tests``.
"""
import pytest

from app.agents.performance_assessment.com_agent.nodes import active_quiz_node
from app.agents.performance_assessment.com_agent.state import FactorOutput


@pytest.fixture(autouse=True)
def stub_code_ownership_rating(monkeypatch):
    real = active_quiz_node.evaluate_factor

    async def evaluate(factor_name, payload=None, context=None, **kw):
        if factor_name == "code_ownership" and payload and "student_response" in payload:
            text = (payload["student_response"] or "").strip()
            score = 0.85 if len(text) > 20 else (0.25 if text else 0.0)
            return FactorOutput(score=score, features={"ko_raw_score": score}, status="completed")
        return await real(factor_name, payload=payload, context=context, **kw)

    monkeypatch.setattr(active_quiz_node, "evaluate_factor", evaluate)
