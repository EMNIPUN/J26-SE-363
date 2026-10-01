"""Tests for parallel passive factor tools and join node (T5.2 & PLAN.md Section 9 Nodes 2-3)."""

import pytest
from app.agents.performance_assessment.com_agent.state import FactorOutput
from app.agents.performance_assessment.com_agent.nodes.passive_runner_node import (
    run_effort_tool,
    run_consistency_tool,
    run_req_fulfillment_tool,
    run_collaboration_tool,
    run_complexity_tool,
    join_passive_factors_node,
)


@pytest.fixture
def mock_student_state():
    return {
        "student_id": "STU-001",
        "student_name": "Alice Perera",
        "student_github_username": "alice-perera",
        "student_git_emails": ["alice@student.sliit.lk", "alice.p@gmail.com"],
        "team_id": "TEAM-A",
        "sprint_id": "sprint-02",
        "repo_url": "https://github.com/org/project-repo",
        "sprint_start": "2025-09-01T00:00:00Z",
        "sprint_end": "2025-09-14T23:59:59Z",
        "cohort_baselines": {
            "metric_means": {"cc": 10.0, "loc_net": 200.0, "fc": 4.0},
            "metric_stds": {"cc": 2.0, "loc_net": 50.0, "fc": 1.0},
        },
    }


@pytest.mark.asyncio
async def test_run_effort_tool(mock_student_state):
    res = await run_effort_tool(mock_student_state)
    assert "factor_scores" in res
    assert "effort" in res["factor_scores"]
    output = res["factor_scores"]["effort"]
    assert isinstance(output, FactorOutput)
    assert 0.0 <= output.score <= 1.0
    assert output.status == "completed"
    assert "CC" in output.features
    assert "LOC_net" in output.features
    assert output.features["CC"] > 0


@pytest.mark.asyncio
async def test_run_consistency_tool(mock_student_state):
    res = await run_consistency_tool(mock_student_state)
    assert "consistency" in res["factor_scores"]
    output = res["factor_scores"]["consistency"]
    assert isinstance(output, FactorOutput)
    assert 0.0 <= output.score <= 1.0
    assert output.status == "completed"
    assert "AWR" in output.features
    assert output.features["active_days_count"] > 0


@pytest.mark.asyncio
async def test_run_req_fulfillment_tool(mock_student_state):
    res = await run_req_fulfillment_tool(mock_student_state)
    assert "requirement_fulfillment" in res["factor_scores"]
    output = res["factor_scores"]["requirement_fulfillment"]
    assert isinstance(output, FactorOutput)
    assert 0.0 <= output.score <= 1.0
    assert output.status == "completed"
    assert output.features["assigned_task_count"] == 3
    assert output.features["completed_task_count"] == 2


@pytest.mark.asyncio
async def test_run_collaboration_tool(mock_student_state):
    res = await run_collaboration_tool(mock_student_state)
    assert "collaboration" in res["factor_scores"]
    output = res["factor_scores"]["collaboration"]
    assert isinstance(output, FactorOutput)
    assert 0.0 <= output.score <= 1.0
    assert output.status == "completed"
    assert output.features["PCount"] >= 1
    assert output.features["CCount"] >= 1


@pytest.mark.asyncio
async def test_run_complexity_tool(mock_student_state):
    res = await run_complexity_tool(mock_student_state)
    assert "task_complexity" in res["factor_scores"]
    output = res["factor_scores"]["task_complexity"]
    assert isinstance(output, FactorOutput)
    assert 0.0 <= output.score <= 1.0
    assert output.status == "completed"
    assert output.features["SP"] > 0
    assert output.features["SC"] > 0


@pytest.mark.asyncio
async def test_join_passive_factors_node_normal():
    state = {
        "factor_scores": {
            "effort": FactorOutput(score=0.85),
            "consistency": FactorOutput(score=0.75),
            "requirement_fulfillment": FactorOutput(score=0.90),
            "collaboration": FactorOutput(score=0.65),
            "task_complexity": FactorOutput(score=0.70),
        }
    }
    updates = await join_passive_factors_node(state)
    assert updates["current_step"] == "passive_complete"
    assert "weights_used" in updates
    assert sum(updates["weights_used"].values()) == pytest.approx(1.0, rel=1e-5)


@pytest.mark.asyncio
async def test_join_passive_factors_node_with_fallback_redistribution():
    state = {
        "factor_scores": {
            "effort": FactorOutput(score=0.85),
            "consistency": FactorOutput(score=0.75),
            "requirement_fulfillment": FactorOutput(score=0.0, status="fallback_applied"),
            "collaboration": FactorOutput(score=0.65),
            "task_complexity": FactorOutput(score=0.70),
        }
    }
    updates = await join_passive_factors_node(state)
    assert updates["current_step"] == "passive_complete"
    # requirement_fulfillment should be removed from effective weights
    assert "requirement_fulfillment" not in updates["weights_used"]
    assert sum(updates["weights_used"].values()) == pytest.approx(1.0, rel=1e-5)
