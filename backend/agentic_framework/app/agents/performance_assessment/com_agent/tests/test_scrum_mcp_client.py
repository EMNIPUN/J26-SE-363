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
async def test_real_scrum_client_raises_not_implemented():
    client = RealScrumMCPClient()
    with pytest.raises(NotImplementedError):
        await client.get_sprint_details("sprint-02")
    with pytest.raises(NotImplementedError):
        await client.get_student_tasks("sprint-02", "STU-001")
    with pytest.raises(NotImplementedError):
        await client.get_task_acceptance_criteria("TASK-101")
    with pytest.raises(NotImplementedError):
        await client.get_task_status_history("TASK-101")

def test_scrum_client_factory():
    client_dev = get_scrum_client(is_dev=True)
    assert isinstance(client_dev, MockScrumMCPClient)

    client_prod = get_scrum_client(is_dev=False)
    assert isinstance(client_prod, RealScrumMCPClient)
