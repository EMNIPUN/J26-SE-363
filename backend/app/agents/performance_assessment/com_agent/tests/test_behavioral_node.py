"""Tests for behavioral pattern persona classification (T5.6 & PLAN.md Section 9 Node 7)."""

import pytest
from app.agents.performance_assessment.com_agent.state import FactorOutput
from app.agents.performance_assessment.com_agent.nodes.behavioral_node import (
    classify_persona,
    run_behavioral_pattern_node,
)


def test_classify_persona_archetypes():
    # 1. Consistent Builder
    p1, m1 = classify_persona({"effort": 0.85, "consistency": 0.80, "ko_raw": 0.85})
    assert p1 == "Consistent Builder"
    assert m1 >= 1.10

    # 2. Collaborative Harmonizer
    p2, m2 = classify_persona({"effort": 0.60, "consistency": 0.50, "collaboration": 0.85, "ko_raw": 0.70})
    assert p2 == "Collaborative Harmonizer"
    assert m2 == 1.05

    # 3. Deadline Rusher
    p3, m3 = classify_persona({"effort": 0.80, "consistency": 0.20, "ko_raw": 0.70})
    assert p3 == "Deadline Rusher"
    assert m3 == 0.90

    # 4. Disengaged Contributor
    p4, m4 = classify_persona({"effort": 0.15, "collaboration": 0.10, "ko_raw": 0.30})
    assert p4 == "Disengaged Contributor"
    assert m4 == 0.85

    # 5. Balanced Contributor
    p5, m5 = classify_persona({"effort": 0.55, "consistency": 0.55, "collaboration": 0.55, "ko_raw": 0.55})
    assert p5 == "Balanced Contributor"
    assert m5 == 1.00


@pytest.mark.asyncio
async def test_run_behavioral_pattern_node_uses_raw_ko_score():
    # Crucial test: Code ownership score in factor_scores was CAPPED at 0.50 due to quiz extension.
    # But ko_raw_score was 0.90!
    # Because ko_raw_score >= 0.65, student MUST qualify as Consistent Builder, NOT be downgraded!
    state = {
        "ko_raw_score": 0.90,  # Raw uncapped
        "factor_scores": {
            "effort": FactorOutput(score=0.85),
            "consistency": FactorOutput(score=0.75),
            "collaboration": FactorOutput(score=0.60),
            "code_ownership": FactorOutput(
                score=0.50,  # Capped score for grading
                features={"ko_raw_score": 0.90, "ko_fusion_score": 0.50},
            ),
        },
    }

    updates = await run_behavioral_pattern_node(state)
    assert updates["current_step"] == "behavioral_pattern_classified"
    assert updates["behavioral_persona"] == "Consistent Builder"
    assert updates["behavioral_modifier"] == 1.10
    assert 0.80 <= updates["behavioral_modifier"] <= 1.20
