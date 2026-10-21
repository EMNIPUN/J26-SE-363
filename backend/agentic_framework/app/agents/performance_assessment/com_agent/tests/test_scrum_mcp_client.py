"""Unit tests for Scrum MCP client adapter (T2.4 & PLAN.md Section 4.1)."""

import pytest
from app.agents.performance_assessment.com_agent.ingestion.scrum_mcp_client import (
    ScrumMCPClientProtocol,
    MockScrumMCPClient,
    RealScrumMCPClient,
    get_scrum_client,
)

@pytest.mark.asyncio
async def test_mock_scrum_client_sprint_details():
    client = MockScrumMCPClient()
    sprint = await client.get_sprint_details("sprint-02")
    assert sprint["sprint_id"] == "sprint-02"
    assert sprint["sprint_name"] == "Sprint 2: Core Authentication and Data Layer"
    assert "start_date" in sprint
    assert "end_date" in sprint

@pytest.mark.asyncio
async def test_mock_scrum_client_student_tasks_filtering():
    client = MockScrumMCPClient()
    tasks = await client.get_student_tasks(sprint_id="sprint-02", student_id="STU-001")
    assert len(tasks) == 3
    for t in tasks:
        assert t["student_id"] == "STU-001"
        assert t["sprint_id"] == "sprint-02"

    # Filter with non-existent student
    non_existent = await client.get_student_tasks(sprint_id="sprint-02", student_id="STU-999")
    assert len(non_existent) == 0

@pytest.mark.asyncio
async def test_mock_scrum_client_task_acceptance_criteria():
    client = MockScrumMCPClient()
    criteria = await client.get_task_acceptance_criteria("TASK-101")
    assert criteria["task_id"] == "TASK-101"
    assert len(criteria["acceptance_criteria"]) >= 1

    # Non-existent task returns fallback dict
    missing = await client.get_task_acceptance_criteria("TASK-UNKNOWN")
    assert missing["task_id"] == "TASK-UNKNOWN"
    assert missing["acceptance_criteria"] == []

@pytest.mark.asyncio
async def test_mock_scrum_client_task_status_history():
    client = MockScrumMCPClient()
    history = await client.get_task_status_history("TASK-101")
    assert isinstance(history, list)
    assert len(history) >= 2
    columns = [h["column"] for h in history]
    assert "Done" in columns

    # Non-existent task returns empty list
    missing_history = await client.get_task_status_history("TASK-UNKNOWN")
    assert missing_history == []

@pytest.mark.asyncio
async def test_real_scrum_client_talks_to_the_mcp_server_over_stdio():
    """Starts the real Scrum MCP server script as a subprocess and calls every tool through the MCP protocol (data: the course dataset)."""
    async with RealScrumMCPClient() as scrum:
        roster = await scrum.get_team_roster("T01")
        assert {"student_id": "STU-014", "team_id": "T01"} in roster
        sprints = await scrum.list_sprints("T01")
        assert sprints and sprints[0]["sprint_id"] == "T01-S1" and sprints[0]["start_date"]
        details = await scrum.get_sprint_details("T01-S1")
        assert details["total_story_points"] >= details["completed_story_points"] > 0
        tasks = await scrum.get_student_tasks("T01-S1", "STU-014")
        assert tasks and all(t["student_id"] == "STU-014" for t in tasks)
        crit = await scrum.get_task_acceptance_criteria("T01-001")
        assert len(crit["acceptance_criteria"]) == 4 and crit["acceptance_criteria"][1].startswith("Passwords are hashed")
        hist = await scrum.get_task_status_history("T01-001")
        assert hist[0]["source"] == "final_status_only"  # the export has no transitions and says so
        assert (await scrum.get_student_tasks("T01-S1", "STU-NOBODY")) == []
        assert (await scrum.get_task_acceptance_criteria("NOPE"))["acceptance_criteria"] == []


@pytest.mark.asyncio
async def test_real_scrum_client_works_without_a_long_lived_session():
    roster = await RealScrumMCPClient().get_team_roster("T02")
    assert roster and all(r["team_id"] == "T02" for r in roster)


def test_scrum_client_factory():
    client_dev = get_scrum_client(is_dev=True)
    assert isinstance(client_dev, MockScrumMCPClient)

    client_prod = get_scrum_client(is_dev=False)
    assert isinstance(client_prod, RealScrumMCPClient)
