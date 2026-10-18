"""Unit tests for Jira Software REST Client, ADF Builders, and Sync Services."""

import pytest
import httpx
from unittest.mock import AsyncMock, patch

from app.modules.planning.jira_client import (
    JiraClient,
    build_story_adf,
    text_to_adf,
)
from app.modules.planning import jira_service


def test_text_to_adf_valid_structure():
    doc = text_to_adf("First line\nSecond line")
    assert doc["version"] == 1
    assert doc["type"] == "doc"
    assert len(doc["content"]) == 2
    assert doc["content"][0]["type"] == "paragraph"
    assert doc["content"][0]["content"][0]["text"] == "First line"


def test_build_story_adf_complete_sections():
    doc = build_story_adf(
        as_a="Student",
        i_want="to integrate with Jira",
        so_that="I can track sprints",
        description="Detailed background note.",
        acceptance_criteria=["AC1: Click push button", "AC2: Verify issues in Jira"],
        story_points=5,
        hours=8.0,
        estimation_basis="Fibonacci planning poker consensus",
    )
    assert doc["version"] == 1
    assert doc["type"] == "doc"

    types = [item["type"] for item in doc["content"]]
    assert "heading" in types
    assert "paragraph" in types
    assert "bulletList" in types
    assert "rule" in types

    bullet_lists = [item for item in doc["content"] if item["type"] == "bulletList"]
    assert len(bullet_lists) >= 1
    ac_list = bullet_lists[0]
    assert len(ac_list["content"]) == 2
    assert ac_list["content"][0]["content"][0]["content"][0]["text"] == "AC1: Click push button"


@pytest.mark.asyncio
async def test_jira_client_test_connection_success():
    client = JiraClient(
        base_url="https://test-team.atlassian.net",
        email="student@example.com",
        api_token="dummy_token_123",
        project_key="SEL",
    )

    mock_resp = httpx.Response(
        200,
        json={
            "displayName": "Alex Student",
            "emailAddress": "student@example.com",
            "accountId": "acc-12345",
            "active": True,
        },
        request=httpx.Request("GET", "https://test-team.atlassian.net/rest/api/3/myself"),
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        status = await client.test_connection()
        assert status["ok"] is True
        assert status["displayName"] == "Alex Student"
        assert status["accountId"] == "acc-12345"


@pytest.mark.asyncio
async def test_jira_client_test_connection_auth_failure():
    client = JiraClient(
        base_url="https://test-team.atlassian.net",
        email="student@example.com",
        api_token="wrong_token",
    )

    mock_resp = httpx.Response(
        401,
        json={"errorMessages": ["Unauthorized access"]},
        request=httpx.Request("GET", "https://test-team.atlassian.net/rest/api/3/myself"),
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        with pytest.raises(ValueError, match="Jira authentication failed"):
            await client.test_connection()


@pytest.mark.asyncio
async def test_jira_client_issue_exists_preserves_existing_issue_links():
    client = JiraClient(
        base_url="https://test-team.atlassian.net",
        email="student@example.com",
        api_token="dummy_token",
    )
    response = httpx.Response(
        200,
        json={"key": "SCRUM-26"},
        request=httpx.Request("GET", "https://test-team.atlassian.net/rest/api/3/issue/SCRUM-26"),
    )
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = response
        assert await client.issue_exists("SCRUM-26") is True
        assert await client.issue_exists(None) is False


@pytest.mark.asyncio
async def test_jira_client_create_story():
    client = JiraClient(
        base_url="https://test-team.atlassian.net",
        email="student@example.com",
        api_token="dummy_token",
        project_key="SEL",
        story_points_field="customfield_10016",
    )

    mock_project_resp = httpx.Response(
        200,
        json={"issueTypes": [{"name": "Story"}, {"name": "Sub-task"}]},
        request=httpx.Request("GET", "https://test-team.atlassian.net/rest/api/3/project/SEL"),
    )
    mock_create_resp = httpx.Response(
        201,
        json={"id": "10001", "key": "SEL-10", "self": "https://..."},
        request=httpx.Request("POST", "https://test-team.atlassian.net/rest/api/3/issue"),
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get, \
         patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_get.return_value = mock_project_resp
        mock_post.return_value = mock_create_resp

        created = await client.create_story(
            summary="[US-01] User Login",
            description_adf=text_to_adf("Login feature"),
            story_points=5,
            priority="High",
            story_ref="US-01",
        )
        assert created["key"] == "SEL-10"


@pytest.mark.asyncio
async def test_jira_client_reuses_existing_subtask_without_creating_a_duplicate():
    client = JiraClient(
        base_url="https://test-team.atlassian.net",
        email="student@example.com",
        api_token="dummy_token",
        project_key="SEL",
    )
    with patch.object(client, "find_subtask", new_callable=AsyncMock) as find_subtask, \
         patch("httpx.AsyncClient.post", new_callable=AsyncMock) as post:
        find_subtask.return_value = {"key": "SEL-12", "fields": {"summary": "Build API"}}
        result = await client.create_subtask("SEL-10", "Build API")
        assert result["key"] == "SEL-12"
        post.assert_not_called()


@pytest.mark.asyncio
async def test_jira_client_create_sprint_and_move():
    client = JiraClient(
        base_url="https://test-team.atlassian.net",
        email="student@example.com",
        api_token="dummy_token",
        project_key="SEL",
        board_id=42,
    )

    mock_sprint_resp = httpx.Response(
        201,
        json={"id": 99, "name": "Sprint 1", "state": "future"},
        request=httpx.Request("POST", "https://test-team.atlassian.net/rest/agile/1.0/sprint"),
    )
    mock_move_resp = httpx.Response(
        204,
        request=httpx.Request("POST", "https://test-team.atlassian.net/rest/agile/1.0/sprint/99/issue"),
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = [mock_sprint_resp, mock_move_resp]

        sprint = await client.create_sprint(name="Sprint 1")
        assert sprint["id"] == 99

        moved = await client.move_issues_to_sprint(sprint_id=99, issue_keys=["SEL-10", "SEL-11"])
        assert moved is True


@pytest.mark.asyncio
async def test_jira_client_fetches_linked_issue_and_paginates_sprint_issues():
    client = JiraClient(
        base_url="https://test-team.atlassian.net",
        email="student@example.com",
        api_token="dummy_token",
        project_key="SEL",
    )
    issue_response = httpx.Response(
        200,
        json={"key": "SEL-10", "fields": {"status": {"name": "Done"}}},
        request=httpx.Request("GET", "https://test-team.atlassian.net/rest/api/3/issue/SEL-10"),
    )
    sprint_page_one = httpx.Response(
        200,
        json={"issues": [{"key": "SEL-10"}], "total": 2},
        request=httpx.Request("GET", "https://test-team.atlassian.net/rest/agile/1.0/sprint/99/issue"),
    )
    sprint_page_two = httpx.Response(
        200,
        json={"issues": [{"key": "SEL-11"}], "total": 2},
        request=httpx.Request("GET", "https://test-team.atlassian.net/rest/agile/1.0/sprint/99/issue"),
    )
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = [issue_response, sprint_page_one, sprint_page_two]
        assert (await client.get_issue("SEL-10"))["key"] == "SEL-10"
        issues = await client.list_sprint_issues(99)
        assert [issue["key"] for issue in issues] == ["SEL-10", "SEL-11"]


def test_jira_execution_status_mapping_keeps_local_planning_lifecycle_separate():
    assert jira_service._jira_task_status({"status": {"name": "Blocked"}}).value == "blocked"
    assert jira_service._jira_task_status({"status": {"statusCategory": {"key": "done"}}}).value == "done"
    assert jira_service._jira_task_status({"status": {"statusCategory": {"key": "indeterminate"}}}).value == "in_progress"


@pytest.mark.asyncio
async def test_jira_service_status_unconfigured():
    status = await jira_service.check_jira_status({
        "base_url": "",
        "email": "",
        "api_token": "",
    })
    assert status["configured"] is False
    assert status["connected"] is False


def test_jira_api_status_endpoint():
    from app.main import app
    from fastapi.testclient import TestClient
    from app.core.security import CurrentUser, get_current_user
    from shared.contracts import UserRole

    mock_user = CurrentUser(
        user_id="test-student-jira",
        username="jirastudent",
        role=UserRole.STUDENT,
        roles=["student"],
    )
    app.dependency_overrides[get_current_user] = lambda: mock_user
    client = TestClient(app)

    try:
        resp = client.get("/api/v1/planning/jira/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "configured" in data
        assert "connected" in data
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_jira_client_transition_status():
    from unittest.mock import AsyncMock, patch

    client = JiraClient("https://mock.atlassian.net", "u@m.com", "tok", "PROJ")
    mock_transitions = [
        {"id": "11", "name": "To Do", "to": {"name": "To Do", "statusCategory": {"key": "new"}}},
        {"id": "21", "name": "In Progress", "to": {"name": "In Progress", "statusCategory": {"key": "indeterminate"}}},
        {"id": "31", "name": "Done", "to": {"name": "Done", "statusCategory": {"key": "done"}}},
    ]

    with patch.object(client, "get_issue_transitions", new_callable=AsyncMock) as mock_get, \
         patch.object(client, "transition_issue", new_callable=AsyncMock) as mock_trans:
        mock_get.return_value = mock_transitions
        mock_trans.return_value = True

        res = await client.transition_issue_by_status_name("PROJ-1", "Done")
        assert res["ok"] is True
        assert res["transition_id"] == "31"
        assert res["to_status"] == "Done"
        mock_trans.assert_called_once_with("PROJ-1", "31")

        mock_trans.reset_mock()
        res_progress = await client.transition_issue_by_status_name("PROJ-1", "In Progress")
        assert res_progress["ok"] is True
        assert res_progress["transition_id"] == "21"

