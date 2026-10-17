"""Tests for validate_context_node (T5.1 & PLAN.md Section 9 Node 1)."""

import pytest
from app.agents.performance_assessment.com_agent.nodes.validation_node import (
    validate_context_node,
)


@pytest.mark.asyncio
async def test_validate_context_node_dev_mode_success():
    state = {}
    updates = await validate_context_node(state, is_dev=True)

    assert updates["current_step"] == "context_validated"
    assert updates["errors"] == []
    assert updates["student_id"] == "STU-001"
    assert updates["student_github_username"] == "alice-perera"
    assert "cohort_baselines" in updates
    assert updates["cohort_baselines"]["sprint_count_used"] >= 1
    assert "cc" in updates["cohort_baselines"]["metric_means"]


@pytest.mark.asyncio
async def test_validate_context_node_missing_required_fields():
    # Provide incomplete state with dev mode disabled
    incomplete_state = {
        "student_id": "STU-002",
        # missing student_github_username, repo_url, assigned_tasks
        "student_git_emails": ["bob@sliit.lk"],
        "team_id": "TEAM-B",
        "sprint_id": "sprint-02",
    }
    updates = await validate_context_node(incomplete_state, is_dev=False)

    assert updates["current_step"] == "validation_failed"
    assert len(updates["errors"]) >= 2
    err_str = " ".join(updates["errors"])
    assert "student_github_username" in err_str
    assert "repo_url" in err_str


@pytest.mark.asyncio
async def test_validate_context_node_empty_emails_fails():
    state = {
        "student_id": "STU-003",
        "student_github_username": "charlie",
        "student_git_emails": [],  # Empty emails
        "team_id": "TEAM-C",
        "sprint_id": "sprint-02",
        "repo_url": "https://github.com/org/repo",
        "assigned_tasks": [{"task_id": "TASK-1"}],
    }
    updates = await validate_context_node(state, is_dev=True)

    assert updates["current_step"] == "validation_failed"
    assert any("student_git_emails" in e for e in updates["errors"])


@pytest.mark.asyncio
async def test_validate_context_node_prod_mode_checks_repo_clone():
    valid_state = {
        "student_id": "STU-004",
        "student_github_username": "dave",
        "student_git_emails": ["dave@sliit.lk"],
        "team_id": "NON_EXISTENT_TEAM_12345",
        "sprint_id": "sprint-02",
        "repo_url": "https://github.com/org/repo",
        "assigned_tasks": [{"task_id": "TASK-1"}],
    }
    # In prod mode, non-existent clone dir must trigger validation failure
    updates = await validate_context_node(valid_state, is_dev=False)

    assert updates["current_step"] == "validation_failed"
    assert any("Local clone directory does not exist" in e for e in updates["errors"])
