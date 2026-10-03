"""Tests for behavioral pattern persona classification (T5.6 & PLAN.md Section 9 Node 7).

Improvements over original:
- Added ko_raw_score=None fallback path test
- Added modifier clamping test at 0.80 minimum
- Added test for Balanced Contributor default (when no other archetype matches)
- Added full-node tests for all 5 archetypes
"""

import pytest
from app.agents.performance_assessment.com_agent.state import FactorOutput
from app.agents.performance_assessment.com_agent.nodes.behavioral_node import (
    classify_persona,
    run_behavioral_pattern_node,
)


# ---------------------------------------------------------------------------
# classify_persona — pure function tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("signals,expected_persona,expected_modifier", [
    # Consistent Builder: effort>=0.70, consistency>=0.60, ko_raw>=0.65
    (
        {"effort": 0.85, "consistency": 0.80, "collaboration": 0.60, "ko_raw": 0.85},
        "Consistent Builder", 1.10,
    ),
    # Collaborative Harmonizer: collaboration>=0.70, effort>=0.45
    # (effort must NOT be >= 0.70 to avoid matching Consistent Builder first)
    (
        {"effort": 0.60, "consistency": 0.50, "collaboration": 0.85, "ko_raw": 0.70},
        "Collaborative Harmonizer", 1.05,
    ),
    # Deadline Rusher: effort>=0.60, consistency<0.35
    (
        {"effort": 0.80, "consistency": 0.20, "collaboration": 0.40, "ko_raw": 0.70},
        "Deadline Rusher", 0.90,
    ),
    # Disengaged Contributor: effort<0.30, collaboration<0.30
    (
        {"effort": 0.15, "collaboration": 0.10, "consistency": 0.40, "ko_raw": 0.30},
        "Disengaged Contributor", 0.85,
    ),
    # Balanced Contributor: none of the above match
    (
        {"effort": 0.55, "consistency": 0.55, "collaboration": 0.55, "ko_raw": 0.55},
        "Balanced Contributor", 1.00,
    ),
])
def test_classify_persona_all_archetypes(signals, expected_persona, expected_modifier):
    persona, modifier = classify_persona(signals)
    assert persona == expected_persona
    assert modifier == pytest.approx(expected_modifier, abs=1e-6)


def test_classify_persona_modifier_always_in_range():
    """Whatever inputs are given, modifier must stay in [0.80, 1.20]."""
    test_cases = [
        {"effort": 0.0, "consistency": 0.0, "collaboration": 0.0, "ko_raw": 0.0},
        {"effort": 1.0, "consistency": 1.0, "collaboration": 1.0, "ko_raw": 1.0},
        {"effort": 0.50, "consistency": 0.50, "collaboration": 0.50, "ko_raw": 0.50},
    ]
    for signals in test_cases:
        _, modifier = classify_persona(signals)
        assert 0.80 <= modifier <= 1.20, f"modifier={modifier} out of [0.80, 1.20] for signals={signals}"


# ---------------------------------------------------------------------------
# run_behavioral_pattern_node — node tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_behavioral_pattern_node_uses_raw_ko_score():
    """Critical: persona must be derived from ko_raw_score (uncapped), not the capped .score.

    code_ownership.score = 0.50 (capped for grading), but ko_raw_score = 0.90.
    Because ko_raw >= 0.65, student qualifies as Consistent Builder.
    If the node used .score=0.50 instead, it would fall through to Balanced Contributor.
    """
    state = {
        "ko_raw_score": 0.90,  # explicit uncapped value in state
        "factor_scores": {
            "effort": FactorOutput(score=0.85),
            "consistency": FactorOutput(score=0.75),
            "collaboration": FactorOutput(score=0.60),
            "code_ownership": FactorOutput(
                score=0.50,  # capped for final_score calculation
                features={"ko_raw_score": 0.90, "ko_fusion_score": 0.50},
            ),
        },
    }

    updates = await run_behavioral_pattern_node(state)
    assert updates["current_step"] == "behavioral_pattern_classified"
    assert updates["behavioral_persona"] == "Consistent Builder"
    assert updates["behavioral_modifier"] == pytest.approx(1.10, abs=1e-6)
    assert 0.80 <= updates["behavioral_modifier"] <= 1.20


@pytest.mark.asyncio
async def test_run_behavioral_pattern_node_ko_raw_score_none_fallback():
    """When ko_raw_score is None in state AND not in features, node must not crash.

    Falls back to reading code_ownership.score, then defaults to 0.5 if unavailable.
    """
    state = {
        # ko_raw_score not in state at all
        "factor_scores": {
            "effort": FactorOutput(score=0.50),
            "consistency": FactorOutput(score=0.50),
            "collaboration": FactorOutput(score=0.50),
            # code_ownership also absent — node must handle gracefully
        },
    }

    updates = await run_behavioral_pattern_node(state)
    assert updates["current_step"] == "behavioral_pattern_classified"
    assert updates["behavioral_persona"] == "Balanced Contributor"
    assert 0.80 <= updates["behavioral_modifier"] <= 1.20


@pytest.mark.asyncio
async def test_run_behavioral_pattern_node_disengaged_modifier_minimum():
    """Disengaged Contributor modifier is 0.85 — above 0.80 minimum, correctly not clamped."""
    state = {
        "ko_raw_score": 0.30,
        "factor_scores": {
            "effort": FactorOutput(score=0.15),
            "consistency": FactorOutput(score=0.40),
            "collaboration": FactorOutput(score=0.10),
            "code_ownership": FactorOutput(score=0.30),
        },
    }

    updates = await run_behavioral_pattern_node(state)
    assert updates["behavioral_persona"] == "Disengaged Contributor"
    assert updates["behavioral_modifier"] == pytest.approx(0.85, abs=1e-6)
    # 0.85 is above 0.80 minimum — no clamping needed
    assert updates["behavioral_modifier"] >= 0.80


@pytest.mark.asyncio
async def test_run_behavioral_pattern_node_output_always_clamped():
    """Regardless of classify_persona output, node must clamp to [0.80, 1.20]."""
    # Simulate a future archetype that might return a modifier outside range
    from unittest.mock import patch
    with patch(
        "app.agents.performance_assessment.com_agent.nodes.behavioral_node.classify_persona",
        return_value=("FuturePersona", 1.50),  # hypothetical out-of-range value
    ):
        state = {"factor_scores": {}}
        updates = await run_behavioral_pattern_node(state)
        assert updates["behavioral_modifier"] == 1.20  # clamped down to max
