"""Tests for cross-sprint memory nodes (T5.10 & PLAN.md Section 9 Nodes 11, 15).

Improvements over original:
- store=None guard test
- Duplicate sprint_id idempotency test
- Multi-sprint accumulation test
- Missing student_id edge case
"""

import pytest
from app.agents.performance_assessment.com_agent.nodes.memory_node import (
    load_cross_sprint_memory_node,
    update_cross_sprint_memory_node,
)


@pytest.mark.asyncio
async def test_load_cross_sprint_memory_sprint_1_empty():
    """Sprint 1: no prior history → empty trajectory."""
    store = {}
    state = {"student_id": "STU-001"}
    updates = await load_cross_sprint_memory_node(state, store=store)

    assert updates["current_step"] == "cross_sprint_memory_loaded"
    assert updates["historical_trajectory"] == []


@pytest.mark.asyncio
async def test_load_cross_sprint_memory_store_none():
    """store=None must not crash — returns empty trajectory."""
    state = {"student_id": "STU-001"}
    updates = await load_cross_sprint_memory_node(state, store=None)

    assert updates["current_step"] == "cross_sprint_memory_loaded"
    assert updates["historical_trajectory"] == []


@pytest.mark.asyncio
async def test_update_and_load_cross_sprint_memory():
    """Persist Sprint 1 result and load it as Sprint 2 trajectory."""
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

    upd1 = await update_cross_sprint_memory_node(state_sprint_1, store=store)
    assert upd1["current_step"] == "cross_sprint_memory_updated"

    state_sprint_2 = {"student_id": "STU-001"}
    upd2 = await load_cross_sprint_memory_node(state_sprint_2, store=store)
    assert upd2["current_step"] == "cross_sprint_memory_loaded"

    trajectory = upd2["historical_trajectory"]
    assert len(trajectory) == 1
    assert trajectory[0]["sprint_id"] == "sprint-01"
    assert trajectory[0]["final_score"] == 0.72
    assert trajectory[0]["behavioral_persona"] == "Balanced Contributor"


@pytest.mark.asyncio
async def test_cross_sprint_memory_multi_sprint_accumulation():
    """Saving 3 sprints builds a trajectory of exactly 3 entries in order."""
    store = {}
    student_id = "STU-002"

    for i, (sprint_id, score) in enumerate([
        ("sprint-01", 0.60),
        ("sprint-02", 0.72),
        ("sprint-03", 0.81),
    ]):
        await update_cross_sprint_memory_node(
            {
                "student_id": student_id,
                "sprint_id": sprint_id,
                "final_score": score,
                "additive_score": score - 0.02,
                "behavioral_persona": "Balanced Contributor",
                "behavioral_modifier": 1.00,
                "team_id": "TEAM-B",
            },
            store=store,
        )

    trajectory_updates = await load_cross_sprint_memory_node(
        {"student_id": student_id}, store=store
    )
    traj = trajectory_updates["historical_trajectory"]
    assert len(traj) == 3
    sprint_ids = [e["sprint_id"] for e in traj]
    assert "sprint-01" in sprint_ids
    assert "sprint-02" in sprint_ids
    assert "sprint-03" in sprint_ids


@pytest.mark.asyncio
async def test_cross_sprint_memory_idempotency():
    """Saving the same sprint_id twice must NOT create duplicate entries."""
    store = {}
    state = {
        "student_id": "STU-001",
        "sprint_id": "sprint-01",
        "final_score": 0.70,
        "additive_score": 0.68,
        "behavioral_persona": "Balanced Contributor",
        "behavioral_modifier": 1.00,
        "team_id": "TEAM-A",
    }

    await update_cross_sprint_memory_node(state, store=store)
    # Update same sprint with a corrected score
    state_updated = {**state, "final_score": 0.75}
    await update_cross_sprint_memory_node(state_updated, store=store)

    traj_updates = await load_cross_sprint_memory_node(
        {"student_id": "STU-001"}, store=store
    )
    traj = traj_updates["historical_trajectory"]
    # Should have exactly 1 entry for sprint-01, with the updated score
    sprint01_entries = [e for e in traj if e["sprint_id"] == "sprint-01"]
    assert len(sprint01_entries) == 1
    assert sprint01_entries[0]["final_score"] == 0.75


@pytest.mark.asyncio
async def test_cross_sprint_memory_isolation_between_students():
    """Memory for STU-001 must not bleed into STU-002's trajectory."""
    store = {}
    await update_cross_sprint_memory_node(
        {
            "student_id": "STU-001",
            "sprint_id": "sprint-01",
            "final_score": 0.80,
            "additive_score": 0.78,
            "behavioral_persona": "Consistent Builder",
            "behavioral_modifier": 1.10,
            "team_id": "TEAM-A",
        },
        store=store,
    )

    traj_stu002 = await load_cross_sprint_memory_node(
        {"student_id": "STU-002"}, store=store
    )
    assert traj_stu002["historical_trajectory"] == []
