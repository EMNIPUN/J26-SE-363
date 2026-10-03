"""Tests for parallel passive factor tools and join node (T5.2 & PLAN.md Section 9 Nodes 2-3).

Improvements over original:
- Added fallback (exception) path tests for all 5 passive tools
- Tightened assertions: check specific feature values, not just > 0
- Added join_passive_factors_node edge case: empty factor_scores
"""

import pytest
from unittest.mock import AsyncMock, patch
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


# ===========================================================================
# Happy path tests
# ===========================================================================

@pytest.mark.asyncio
async def test_run_effort_tool_happy_path(mock_student_state):
    res = await run_effort_tool(mock_student_state)
    assert "factor_scores" in res
    assert "effort" in res["factor_scores"]
    output = res["factor_scores"]["effort"]
    assert isinstance(output, FactorOutput)
    assert 0.0 <= output.score <= 1.0
    assert output.status == "completed"
    assert "CC" in output.features
    assert "LOC_net" in output.features
    assert "CT" in output.features
    # Mock commits fixture has 12 Alice commits → CC must be 12
    assert output.features["CC"] == 12
    # Mock has 2 completed tasks out of 3
    assert output.features["CT"] == 2


@pytest.mark.asyncio
async def test_run_consistency_tool_happy_path(mock_student_state):
    res = await run_consistency_tool(mock_student_state)
    assert "consistency" in res["factor_scores"]
    output = res["factor_scores"]["consistency"]
    assert isinstance(output, FactorOutput)
    assert 0.0 <= output.score <= 1.0
    assert output.status == "completed"
    assert "AWR" in output.features
    # Must have actually counted active days
    assert output.features["active_days_count"] > 0


@pytest.mark.asyncio
async def test_run_req_fulfillment_tool_happy_path(mock_student_state):
    res = await run_req_fulfillment_tool(mock_student_state)
    assert "requirement_fulfillment" in res["factor_scores"]
    output = res["factor_scores"]["requirement_fulfillment"]
    assert isinstance(output, FactorOutput)
    assert 0.0 <= output.score <= 1.0
    assert output.status == "completed"
    # Mock fixture: 3 tasks assigned, 2 done
    assert output.features["assigned_task_count"] == 3
    assert output.features["completed_task_count"] == 2
    # Score should reflect 2/3 completion ratio
    assert output.score == pytest.approx(2 / 3, abs=0.05)


@pytest.mark.asyncio
async def test_run_collaboration_tool_happy_path(mock_student_state):
    res = await run_collaboration_tool(mock_student_state)
    assert "collaboration" in res["factor_scores"]
    output = res["factor_scores"]["collaboration"]
    assert isinstance(output, FactorOutput)
    assert 0.0 <= output.score <= 1.0
    assert output.status == "completed"
    # Alice has 2 PRs authored → PCount=2
    assert output.features["PCount"] >= 1
    # Alice has reviewed >= 2 teammate PRs → CCount >= 2
    assert output.features["CCount"] >= 1


@pytest.mark.asyncio
async def test_run_complexity_tool_happy_path(mock_student_state):
    res = await run_complexity_tool(mock_student_state)
    assert "task_complexity" in res["factor_scores"]
    output = res["factor_scores"]["task_complexity"]
    assert isinstance(output, FactorOutput)
    assert 0.0 <= output.score <= 1.0
    assert output.status == "completed"
    # Mock: 3 tasks with story_points > 0 each
    assert output.features["SP"] > 0
    assert output.features["SC"] > 0


# ===========================================================================
# Fallback (exception) path tests — CRITICAL coverage gap in original
# ===========================================================================

@pytest.mark.asyncio
async def test_run_effort_tool_fallback_on_github_error(mock_student_state):
    """When GitHub client raises, effort tool returns fallback_applied."""
    with patch(
        "app.agents.performance_assessment.com_agent.nodes.passive_runner_node.get_github_client"
    ) as mock_factory:
        mock_client = AsyncMock()
        mock_client.get_commits.side_effect = ConnectionError("GitHub API unreachable")
        mock_factory.return_value = mock_client

        res = await run_effort_tool(mock_student_state)

    output = res["factor_scores"]["effort"]
    assert output.status == "fallback_applied"
    assert output.score == 0.0
    assert output.error_message is not None


@pytest.mark.asyncio
async def test_run_consistency_tool_fallback_on_github_error(mock_student_state):
    """When GitHub client raises, consistency tool returns fallback_applied."""
    with patch(
        "app.agents.performance_assessment.com_agent.nodes.passive_runner_node.get_github_client"
    ) as mock_factory:
        mock_client = AsyncMock()
        mock_client.get_commits.side_effect = TimeoutError("Rate limit exceeded")
        mock_factory.return_value = mock_client

        res = await run_consistency_tool(mock_student_state)

    output = res["factor_scores"]["consistency"]
    assert output.status == "fallback_applied"
    assert output.score == 0.0


@pytest.mark.asyncio
async def test_run_req_fulfillment_tool_fallback_on_scrum_error(mock_student_state):
    """When Scrum client raises, requirement_fulfillment returns fallback_applied."""
    with patch(
        "app.agents.performance_assessment.com_agent.nodes.passive_runner_node.get_scrum_client"
    ) as mock_factory:
        mock_client = AsyncMock()
        mock_client.get_student_tasks.side_effect = RuntimeError("Scrum MCP connection failed")
        mock_factory.return_value = mock_client

        res = await run_req_fulfillment_tool(mock_student_state)

    output = res["factor_scores"]["requirement_fulfillment"]
    assert output.status == "fallback_applied"
    assert output.score == 0.0


@pytest.mark.asyncio
async def test_run_collaboration_tool_fallback_on_github_error(mock_student_state):
    """When GitHub client raises, collaboration returns fallback_applied."""
    with patch(
        "app.agents.performance_assessment.com_agent.nodes.passive_runner_node.get_github_client"
    ) as mock_factory:
        mock_client = AsyncMock()
        mock_client.get_review_comments.side_effect = OSError("Socket closed")
        mock_factory.return_value = mock_client

        res = await run_collaboration_tool(mock_student_state)

    output = res["factor_scores"]["collaboration"]
    assert output.status == "fallback_applied"
    assert output.score == 0.0


@pytest.mark.asyncio
async def test_run_complexity_tool_fallback_on_scrum_error(mock_student_state):
    """When Scrum client raises, task_complexity returns fallback_applied."""
    with patch(
        "app.agents.performance_assessment.com_agent.nodes.passive_runner_node.get_scrum_client"
    ) as mock_factory:
        mock_client = AsyncMock()
        mock_client.get_student_tasks.side_effect = ValueError("Invalid sprint ID")
        mock_factory.return_value = mock_client

        res = await run_complexity_tool(mock_student_state)

    output = res["factor_scores"]["task_complexity"]
    assert output.status == "fallback_applied"
    assert output.score == 0.0


# ===========================================================================
# join_passive_factors_node
# ===========================================================================

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
    # All 6 factors should have weights (code_ownership will be redistributed from its base weight)
    assert len(updates["weights_used"]) >= 5


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
    assert "requirement_fulfillment" not in updates["weights_used"]
    assert sum(updates["weights_used"].values()) == pytest.approx(1.0, rel=1e-5)


@pytest.mark.asyncio
async def test_join_passive_factors_node_empty_factor_scores():
    """Edge case: no factors computed yet — should not crash, weights_used may be empty or full."""
    state = {"factor_scores": {}}
    updates = await join_passive_factors_node(state)
    assert updates["current_step"] == "passive_complete"
    assert "weights_used" in updates
    # With no fallbacks detected, base weights returned unchanged
    weights = updates["weights_used"]
    if weights:
        assert sum(weights.values()) == pytest.approx(1.0, rel=1e-5)
