"""Tests for cross-sprint memory nodes (T5.10 & PLAN.md Section 9 Nodes 11, 15)."""

import pytest
from app.agents.performance_assessment.com_agent.nodes.memory_node import (
    load_cross_sprint_memory_node,
    update_cross_sprint_memory_node,
)


@pytest.mark.asyncio
async def test_load_cross_sprint_memory_sprint_1_empty():
    store = {}
    state = {"student_id": "STU-001"}
    updates = await load_cross_sprint_memory_node(state, store=store)

    assert updates["current_step"] == "cross_sprint_memory_loaded"
    assert updates["historical_trajectory"] == []


@pytest.mark.asyncio
async def test_update_and_load_cross_sprint_memory():
    store = {}
    state_sprint_1 = {
        "student_id": "STU-001",
        "sprint_id": "sprint-01",
        "final_score": 0.72,
        "additive_score": 0.70,
        "behavioral_persona": "Balanced Contributor",
        "behavioral_modifier": 1.02,
        "team_id": "TEAM-A",
    }

    # Persist Sprint 1
    upd1 = await update_cross_sprint_memory_node(state_sprint_1, store=store)
    assert upd1["current_step"] == "cross_sprint_memory_updated"

    # In Sprint 2: Load historical trajectory
    state_sprint_2 = {"student_id": "STU-001"}
    upd2 = await load_cross_sprint_memory_node(state_sprint_2, store=store)
    assert upd2["current_step"] == "cross_sprint_memory_loaded"
    trajectory = upd2["historical_trajectory"]
    assert len(trajectory) == 1
    assert trajectory[0]["sprint_id"] == "sprint-01"
    assert trajectory[0]["final_score"] == 0.72
    assert trajectory[0]["behavioral_persona"] == "Balanced Contributor"
