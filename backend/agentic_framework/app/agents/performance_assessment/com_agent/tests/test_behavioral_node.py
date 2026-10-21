"""Tests for the behavioral pattern node (T5.6 & PLAN.md Section 9 Node 7).

The rules themselves are tested in factor_models/06_behavioral_pattern/tests; here the node's job is checked: gather the scores, treat factors that did not really run as missing,
call the factor package through the bridge, and write a clamped modifier into the state.
"""

import pytest
from app.agents.performance_assessment.com_agent.state import FactorOutput
from app.agents.performance_assessment.com_agent.nodes import behavioral_node as node
from app.agents.performance_assessment.com_agent.nodes.behavioral_node import run_behavioral_pattern_node
from app.agents.performance_assessment.com_agent.policies.fallback_policies import get_fallback_for_factor


def fs(e=None, c=None, co=None, bimodal=None):
    out = {}
    if e is not None:
        out["effort"] = FactorOutput(score=e)
    if c is not None:
        out["consistency"] = FactorOutput(score=c, features={} if bimodal is None else {"C_bimodal": bimodal})
    if co is not None:
        out["collaboration"] = FactorOutput(score=co)
    return out


@pytest.mark.asyncio
async def test_consistent_deep_contributor_through_the_factor_package():
    updates = await run_behavioral_pattern_node({"factor_scores": fs(0.95, 0.95, 0.5)})
    assert updates["current_step"] == "behavioral_pattern_classified"
    assert updates["behavioral_persona"] == "Consistent deep contributor"
    assert 1.10 <= updates["behavioral_modifier"] <= 1.20


@pytest.mark.asyncio
async def test_free_rider_needs_a_collaboration_score():
    low = await run_behavioral_pattern_node({"factor_scores": fs(0.02, 0.0, 0.0)})
    assert low["behavioral_persona"] == "Free rider"
    assert 0.80 <= low["behavioral_modifier"] <= 0.85


@pytest.mark.asyncio
async def test_missing_collaboration_is_not_treated_as_zero():
    """Collaboration not available (nobody in the team reviewed): the full Free rider rule cannot fire, so a student with middle Effort is not penalised for it."""
    updates = await run_behavioral_pattern_node({"factor_scores": fs(0.30, 0.40, None)})
    assert updates["behavioral_persona"] == "Balanced contributor"
    assert updates["behavioral_modifier"] == 1.0


@pytest.mark.asyncio
async def test_almost_no_activity_without_a_collaboration_score_is_an_effort_only_free_rider_with_a_milder_modifier():
    updates = await run_behavioral_pattern_node({"factor_scores": fs(0.02, 0.0, None)})
    assert updates["behavioral_persona"] == "Free rider"
    assert 0.90 <= updates["behavioral_modifier"] <= 0.95  # milder than the 0.80-0.85 of the full rule


@pytest.mark.asyncio
async def test_a_fallback_collaboration_is_passed_on_as_missing():
    factors = fs(0.30, 0.40)
    factors["collaboration"] = get_fallback_for_factor("collaboration", "not available")  # score 0.0 with status fallback_applied
    updates = await run_behavioral_pattern_node({"factor_scores": factors})
    assert updates["behavioral_persona"] == "Balanced contributor"  # a fallback 0.0 must not read as "no collaboration"
    assert updates["behavioral_modifier"] == 1.0
    low = fs(0.02, 0.0)
    low["collaboration"] = get_fallback_for_factor("collaboration", "not available")
    again = await run_behavioral_pattern_node({"factor_scores": low})
    assert 0.90 <= again["behavioral_modifier"] <= 0.95  # effort-only path, not the full 0.80-0.85 rule


@pytest.mark.asyncio
async def test_effort_or_consistency_missing_gives_no_adjustment():
    updates = await run_behavioral_pattern_node({"factor_scores": {}})
    assert updates["behavioral_persona"] == "Unclassified"
    assert updates["behavioral_modifier"] == 1.0


@pytest.mark.asyncio
async def test_the_bimodal_flag_of_the_consistency_factor_is_read():
    updates = await run_behavioral_pattern_node({"factor_scores": fs(0.95, 0.45, 0.5, bimodal=1)})
    assert updates["behavioral_persona"] == "Burst worker"


@pytest.mark.asyncio
async def test_node_output_is_always_clamped(monkeypatch):
    async def wild(signals, context=None, mode=None, duration_seconds=None):
        return "FuturePersona", 1.50, "out of range on purpose"

    monkeypatch.setattr(node, "classify_persona_via_bridge", wild)
    updates = await run_behavioral_pattern_node({"factor_scores": {}})
    assert updates["behavioral_modifier"] == 1.20
