"""Atlassian Jira Software REST API v3 and Agile API v1 client.

Supports:
- Connection verification (/rest/api/3/myself)
- Project and Board discovery
- Dynamic Issue Type and Story Point field detection
- Epics, Stories, and Sub-tasks creation in Jira Backlog
- Sprint creation and issue assignment via Jira Agile API
- Atlassian Document Format (ADF) builders
"""

from __future__ import annotations

import base64
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


def text_to_adf(text: str) -> dict[str, Any]:
    """Convert a plain text string into a minimal valid ADF document."""
    lines = [line.strip() for line in (text or "").split("\n") if line.strip()]
    if not lines:
        lines = ["No description provided."]
    content = [
        {
            "type": "paragraph",
            "content": [{"type": "text", "text": line}],
        }
        for line in lines
    ]
    return {
        "version": 1,
        "type": "doc",
        "content": content,
    }


def build_story_adf(
    as_a: str | None = None,
    i_want: str | None = None,
    so_that: str | None = None,
    description: str | None = None,
    acceptance_criteria: list[str] | None = None,
    story_points: int | float | None = None,
    hours: float | None = None,
    estimation_basis: str | None = None,
) -> dict[str, Any]:
    """Construct an Atlassian Document Format (ADF) description for a User Story."""
    content: list[dict[str, Any]] = []

    # 1. As a / I want / So that section
    has_user_story_format = bool(as_a or i_want or so_that)
    if has_user_story_format:
        content.append({
            "type": "heading",
            "attrs": {"level": 3},
            "content": [{"type": "text", "text": "User Story"}],
        })
        story_paras = []
        if as_a:
            story_paras.append(
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "As a: ", "marks": [{"type": "strong"}]},
                        {"type": "text", "text": as_a},
                    ],
                }
            )
        if i_want:
            story_paras.append(
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "I want: ", "marks": [{"type": "strong"}]},
                        {"type": "text", "text": i_want},
                    ],
                }
            )
        if so_that:
            story_paras.append(
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "So that: ", "marks": [{"type": "strong"}]},
                        {"type": "text", "text": so_that},
                    ],
                }
            )
        content.extend(story_paras)

    # 2. Additional Description
    if description and description.strip():
        if has_user_story_format:
            content.append({
                "type": "heading",
                "attrs": {"level": 4},
                "content": [{"type": "text", "text": "Description"}],
            })
        for line in description.split("\n"):
            clean = line.strip()
            if clean:
                content.append({
                    "type": "paragraph",
                    "content": [{"type": "text", "text": clean}],
                })

    # 3. Acceptance Criteria
    if acceptance_criteria:
        content.append({
            "type": "heading",
            "attrs": {"level": 3},
            "content": [{"type": "text", "text": "Acceptance Criteria"}],
        })
        list_items = []
        for ac in acceptance_criteria:
            text_val = str(ac).strip()
            if text_val:
                list_items.append({
                    "type": "listItem",
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": text_val}],
                        }
                    ],
                })
        if list_items:
            content.append({
                "type": "bulletList",
                "content": list_items,
            })

    # 4. Estimation Metadata
    if story_points is not None or hours is not None or estimation_basis:
        content.append({"type": "rule"})
        content.append({
            "type": "heading",
            "attrs": {"level": 4},
            "content": [{"type": "text", "text": "Effort Estimation (SELVIA)"}],
        })
        est_items = []
        if story_points is not None:
            est_items.append(f"Story Points: {story_points} SP (Fibonacci)")
        if hours is not None:
            est_items.append(f"Estimated Hours: {hours} h")
        if estimation_basis:
            est_items.append(f"Basis: {estimation_basis}")

        content.append({
            "type": "bulletList",
            "content": [
                {
                    "type": "listItem",
                    "content": [{"type": "paragraph", "content": [{"type": "text", "text": item}]}],
                }
                for item in est_items
            ],
        })

    if not content:
        content = [{
            "type": "paragraph",
            "content": [{"type": "text", "text": "Generated from SELVIA Project Planning."}],
        }]

    return {
        "version": 1,
        "type": "doc",
        "content": content,
    }


class JiraClient:
    """Client for Jira Cloud REST API v3 and Agile API v1."""

    def __init__(
        self,
        base_url: str,
        email: str,
        api_token: str,
        project_key: str | None = None,
        board_id: int | None = None,
        story_points_field: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.email = email.strip()
        self.api_token = api_token.strip()
        self.project_key = (project_key or "").strip().upper() or None
        self.board_id = board_id
        self.story_points_field = story_points_field
        self.timeout = timeout

        raw_auth = f"{self.email}:{self.api_token}".encode("utf-8")
        self.auth_header = f"Basic {base64.b64encode(raw_auth).decode('utf-8')}"

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": self.auth_header,
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            timeout=self.timeout,
        )

    async def test_connection(self) -> dict[str, Any]:
        """Verify Jira credentials against /rest/api/3/myself."""
        async with self._client() as client:
            resp = await client.get("/rest/api/3/myself")
            if resp.status_code != 200:
                detail = resp.text
                try:
                    err_json = resp.json()
                    detail = err_json.get("errorMessages", [detail])[0]
                except Exception:
                    pass
                raise ValueError(f"Jira authentication failed ({resp.status_code}): {detail}")
            data = resp.json()
            return {
                "ok": True,
                "displayName": data.get("displayName"),
                "emailAddress": data.get("emailAddress"),
                "accountId": data.get("accountId"),
                "active": data.get("active", True),
            }

    async def issue_exists(self, issue_key: str | None) -> bool:
        """Check if an issue key actually exists in Jira (not deleted)."""
        if not issue_key or not issue_key.strip():
            return False
        try:
            async with self._client() as client:
                resp = await client.get(f"/rest/api/3/issue/{issue_key.strip()}")
                return resp.status_code == 200
        except Exception as e:
            logger.warning("Error checking issue existence for %s: %s", issue_key, e)
            return False

    async def get_issue(self, issue_key: str, fields: list[str] | None = None) -> dict[str, Any]:
        """Return the current Jira representation of one linked issue.

        Linked-key reads intentionally avoid project-wide imports: SELVIA only
        mirrors work items it created or was explicitly linked to.
        """
        requested = fields or [
            "summary", "status", "priority", "assignee", "updated", "sprint",
            "parent", "issuetype",
        ]
        async with self._client() as client:
            resp = await client.get(
                f"/rest/api/3/issue/{issue_key}",
                params={"fields": ",".join(requested)},
            )
            if resp.status_code != 200:
                raise ValueError(f"Could not fetch Jira issue {issue_key}: {resp.status_code} {resp.text}")
            return resp.json()

    async def get_sprint(self, sprint_id: int) -> dict[str, Any]:
        """Return the current Agile sprint details for a linked local sprint."""
        async with self._client() as client:
            resp = await client.get(f"/rest/agile/1.0/sprint/{sprint_id}")
            if resp.status_code != 200:
                raise ValueError(f"Could not fetch Jira sprint {sprint_id}: {resp.status_code} {resp.text}")
            return resp.json()

    async def list_sprint_issues(self, sprint_id: int) -> list[dict[str, Any]]:
        """Fetch all issue pages for a Jira sprint.

        This is used to discover sprint membership for already-linked work;
        callers still match only local Jira keys and never import unrelated
        Jira issues.
        """
        issues: list[dict[str, Any]] = []
        start_at = 0
        page_size = 50
        fields = "summary,status,priority,assignee,updated,sprint,parent,issuetype"
        async with self._client() as client:
            while True:
                resp = await client.get(
                    f"/rest/agile/1.0/sprint/{sprint_id}/issue",
                    params={"startAt": start_at, "maxResults": page_size, "fields": fields},
                )
                if resp.status_code != 200:
                    raise ValueError(
                        f"Could not fetch Jira sprint issues {sprint_id}: {resp.status_code} {resp.text}"
                    )
                data = resp.json()
                page = data.get("issues", [])
                issues.extend(page)
                total = data.get("total")
                if not page or (total is not None and start_at + len(page) >= total):
                    break
                start_at += len(page)
        return issues

    async def list_board_sprints(self, board_id: int | None = None) -> list[dict[str, Any]]:
        """List the board's Jira-managed sprints, following all pages."""
        resolved_board_id = board_id or await self.discover_board_id()
        if not resolved_board_id:
            raise ValueError("No Scrum Board found for this Jira project.")
        sprints: list[dict[str, Any]] = []
        start_at = 0
        page_size = 50
        async with self._client() as client:
            while True:
                resp = await client.get(
                    f"/rest/agile/1.0/board/{resolved_board_id}/sprint",
                    params={"state": "active,future,closed", "startAt": start_at, "maxResults": page_size},
                )
                if resp.status_code != 200:
                    raise ValueError(
                        f"Could not fetch Jira board sprints {resolved_board_id}: {resp.status_code} {resp.text}"
                    )
                data = resp.json()
                page = data.get("values", [])
                sprints.extend(page)
                total = data.get("total")
                if not page or (total is not None and start_at + len(page) >= total):
                    break
                start_at += len(page)
        return sprints

    async def get_project(self, project_key: str | None = None) -> dict[str, Any]:
        """Fetch project details by key."""
        key = project_key or self.project_key
        if not key:
            raise ValueError("Project key is required.")
        async with self._client() as client:
            resp = await client.get(f"/rest/api/3/project/{key}")
            if resp.status_code != 200:
                raise ValueError(f"Failed to find Jira project '{key}': {resp.text}")
            return resp.json()

    async def get_issue_types(self, project_key: str | None = None) -> dict[str, str]:
        """Return a mapping of normalized issue type names to their exact Jira name.
        e.g. {'story': 'Story', 'subtask': 'Sub-task', 'epic': 'Epic'}
        """
        key = project_key or self.project_key
        issue_types_map: dict[str, str] = {}
        async with self._client() as client:
            url = f"/rest/api/3/project/{key}" if key else "/rest/api/3/issuetype"
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                types = data.get("issueTypes", []) if isinstance(data, dict) and "issueTypes" in data else data
                if isinstance(types, list):
                    for it in types:
                        name = it.get("name", "")
                        norm = name.lower().replace("-", "").replace(" ", "")
                        issue_types_map[norm] = name
        return issue_types_map

    async def discover_board_id(self, project_key: str | None = None) -> int | None:
        """Find the Agile board ID for the project."""
        if self.board_id:
            return self.board_id
        key = project_key or self.project_key
        async with self._client() as client:
            resp = await client.get("/rest/agile/1.0/board", params={"projectKeyOrId": key} if key else {})
            if resp.status_code == 200:
                boards = resp.json().get("values", [])
                if boards:
                    # Prefer scrum board if available
                    for b in boards:
                        if b.get("type") == "scrum":
                            return b.get("id")
                    return boards[0].get("id")
        return None

    async def discover_story_points_field(self) -> str:
        """Detect the custom field ID for Story Points in this Jira instance."""
        if self.story_points_field:
            return self.story_points_field
        async with self._client() as client:
            resp = await client.get("/rest/api/3/field")
            if resp.status_code == 200:
                fields = resp.json()
                for f in fields:
                    name = f.get("name", "").lower()
                    if "story point" in name or name == "story points":
                        return f.get("id", "customfield_10016")
        return "customfield_10016"

    async def find_issue_by_label(self, label: str, project_key: str | None = None) -> dict[str, Any] | None:
        """Search Jira for an existing issue carrying the specified unique label."""
        key = project_key or self.project_key
        jql = f'labels = "{label}"'
        if key:
            jql = f'project = "{key}" AND {jql}'
        jql += " ORDER BY created ASC"
        try:
            async with self._client() as client:
                resp = await client.post(
                    "/rest/api/3/search/jql",
                    json={"jql": jql, "maxResults": 1, "fields": ["summary", "key", "issuetype"]},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    issues = data.get("issues", [])
                    if issues:
                        return issues[0]
        except Exception as e:
            logger.warning("Error checking existing issue for label %s: %s", label, e)
        return None

    async def find_subtask(self, parent_issue_key: str, summary: str) -> dict[str, Any] | None:
        """Search Jira for an existing subtask under the given parent issue."""
        jql = f'parent = "{parent_issue_key}"'
        try:
            async with self._client() as client:
                resp = await client.post(
                    "/rest/api/3/search/jql",
                    json={"jql": jql, "maxResults": 50, "fields": ["summary", "key", "issuetype"]},
                )
                if resp.status_code == 200:
                    for issue in resp.json().get("issues", []):
                        if issue.get("fields", {}).get("summary", "").strip().lower() == summary.strip().lower():
                            return issue
        except Exception as e:
            logger.warning("Error checking existing subtask for %s: %s", parent_issue_key, e)
        return None

    async def create_epic(
        self,
        summary: str,
        description_adf: dict[str, Any] | None = None,
        req_ref: str | None = None,
        project_key: str | None = None,
    ) -> dict[str, Any]:
        """Create an Epic issue in Jira, or return existing if already present."""
        key = project_key or self.project_key
        if req_ref:
            existing = await self.find_issue_by_label(req_ref, key)
            if existing:
                logger.info("Reusing existing Jira Epic %s for requirement %s", existing.get("key"), req_ref)
                return existing

        issue_types = await self.get_issue_types(key)
        epic_type_name = issue_types.get("epic", "Epic")

        payload: dict[str, Any] = {
            "fields": {
                "project": {"key": key},
                "summary": summary,
                "issuetype": {"name": epic_type_name},
                "labels": ["SELVIA", req_ref] if req_ref else ["SELVIA"],
            }
        }
        if description_adf:
            payload["fields"]["description"] = description_adf

        async with self._client() as client:
            resp = await client.post("/rest/api/3/issue", json=payload)
            if resp.status_code not in (200, 201):
                raise ValueError(f"Failed to create Epic '{summary}' in Jira: {resp.text}")
            return resp.json()

    async def create_story(
        self,
        summary: str,
        description_adf: dict[str, Any] | None = None,
        story_points: int | float | None = None,
        priority: str = "Medium",
        parent_epic_key: str | None = None,
        story_ref: str | None = None,
        project_key: str | None = None,
    ) -> dict[str, Any]:
        """Create a Story in the Jira Backlog, or return existing if already present."""
        key = project_key or self.project_key
        if story_ref:
            existing = await self.find_issue_by_label(story_ref, key)
            if existing:
                logger.info("Reusing existing Jira Story %s for story ref %s", existing.get("key"), story_ref)
                # The caller must not reset an already-exported item's workflow
                # state when the user pushes the backlog again.
                return {**existing, "_selvia_reused": True}

        issue_types = await self.get_issue_types(key)
        story_type_name = issue_types.get("story", issue_types.get("userstory", "Story"))

        labels = ["SELVIA"]
        if story_ref:
            labels.append(story_ref)

        payload: dict[str, Any] = {
            "fields": {
                "project": {"key": key},
                "summary": summary,
                "issuetype": {"name": story_type_name},
                "priority": {"name": priority.capitalize() if priority else "Medium"},
                "labels": labels,
            }
        }
        if description_adf:
            payload["fields"]["description"] = description_adf

        if parent_epic_key:
            payload["fields"]["parent"] = {"key": parent_epic_key}

        sp_field = await self.discover_story_points_field()
        if story_points is not None and sp_field:
            payload["fields"][sp_field] = float(story_points)

        async with self._client() as client:
            resp = await client.post("/rest/api/3/issue", json=payload)
            if resp.status_code not in (200, 201):
                # If priority name or parent field failed, retry without parent / with standard priority
                if "parent" in payload["fields"]:
                    payload["fields"].pop("parent", None)
                    resp = await client.post("/rest/api/3/issue", json=payload)
            if resp.status_code not in (200, 201):
                raise ValueError(f"Failed to create Story '{summary}' in Jira: {resp.text}")
            return resp.json()

    async def create_subtask(
        self,
        parent_issue_key: str,
        summary: str,
        description_adf: dict[str, Any] | None = None,
        priority: str = "Medium",
        project_key: str | None = None,
    ) -> dict[str, Any]:
        """Create a Sub-task under a Story, or return existing if already present."""
        existing = await self.find_subtask(parent_issue_key, summary)
        if existing:
            logger.info("Reusing existing Jira Subtask %s for parent %s", existing.get("key"), parent_issue_key)
            return {**existing, "_selvia_reused": True}
        key = project_key or self.project_key
        issue_types = await self.get_issue_types(key)
        subtask_type_name = (
            issue_types.get("subtask")
            or issue_types.get("subtaskissue")
            or "Sub-task"
        )

        payload: dict[str, Any] = {
            "fields": {
                "project": {"key": key},
                "parent": {"key": parent_issue_key},
                "summary": summary,
                "issuetype": {"name": subtask_type_name},
                "priority": {"name": priority.capitalize() if priority else "Medium"},
                "labels": ["SELVIA", "subtask"],
            }
        }
        if description_adf:
            payload["fields"]["description"] = description_adf

        async with self._client() as client:
            resp = await client.post("/rest/api/3/issue", json=payload)
            if resp.status_code not in (200, 201):
                raise ValueError(f"Failed to create Subtask '{summary}' under {parent_issue_key}: {resp.text}")
            return resp.json()

    async def create_sprint(
        self,
        name: str,
        board_id: int | None = None,
        start_date_iso: str | None = None,
        end_date_iso: str | None = None,
        goal: str | None = None,
    ) -> dict[str, Any]:
        """Create a Sprint via Jira Agile API."""
        b_id = board_id or await self.discover_board_id()
        if not b_id:
            raise ValueError("No Scrum Board ID found for this Jira project.")

        payload: dict[str, Any] = {
            "name": name,
            "originBoardId": b_id,
            "goal": goal or "Created from SELVIA Sprint Planning",
        }
        if start_date_iso:
            payload["startDate"] = start_date_iso
        if end_date_iso:
            payload["endDate"] = end_date_iso

        async with self._client() as client:
            resp = await client.post("/rest/agile/1.0/sprint", json=payload)
            if resp.status_code not in (200, 201):
                raise ValueError(f"Failed to create Sprint '{name}' in Jira: {resp.text}")
            return resp.json()

    async def move_issues_to_sprint(self, sprint_id: int, issue_keys: list[str]) -> bool:
        """Assign an array of issue keys to a Sprint."""
        if not issue_keys:
            return True
        async with self._client() as client:
            resp = await client.post(
                f"/rest/agile/1.0/sprint/{sprint_id}/issue",
                json={"issues": issue_keys},
            )
            return resp.status_code in (200, 204)

    async def get_issue_transitions(self, issue_key: str) -> list[dict[str, Any]]:
        """Fetch available workflow transitions for a Jira issue."""
        async with self._client() as client:
            resp = await client.get(f"/rest/api/3/issue/{issue_key}/transitions")
            if resp.status_code != 200:
                raise ValueError(f"Could not fetch transitions for {issue_key}: {resp.status_code} {resp.text}")
            return resp.json().get("transitions", [])

    async def transition_issue(self, issue_key: str, transition_id: str) -> bool:
        """Apply a transition to move an issue to a new status in Jira."""
        async with self._client() as client:
            resp = await client.post(
                f"/rest/api/3/issue/{issue_key}/transitions",
                json={"transition": {"id": transition_id}},
            )
            return resp.status_code in (200, 204)

    async def transition_issue_by_status_name(self, issue_key: str, target_status: str) -> dict[str, Any]:
        """Find matching transition for target status (e.g. 'In Progress', 'Done', 'To Do') and execute it."""
        transitions = await self.get_issue_transitions(issue_key)
        target_norm = target_status.strip().lower().replace(" ", "").replace("_", "")

        selected = None
        for t in transitions:
            t_name = str(t.get("name", "")).strip().lower().replace(" ", "").replace("_", "")
            to_status = str(t.get("to", {}).get("name", "")).strip().lower().replace(" ", "").replace("_", "")
            if target_norm in (t_name, to_status):
                selected = t
                break

        if not selected and transitions:
            for t in transitions:
                cat = str(t.get("to", {}).get("statusCategory", {}).get("key", "")).strip().lower()
                if (target_norm == "done" and cat == "done") or (target_norm in ("inprogress", "in_progress") and cat == "indeterminate") or (target_norm in ("todo", "to_do") and cat == "new"):
                    selected = t
                    break

        if not selected:
            valid_names = [f"{t.get('name')} (to {t.get('to', {}).get('name')})" for t in transitions]
            raise ValueError(f"No valid Jira transition to '{target_status}' found for {issue_key}. Available: {valid_names}")

        success = await self.transition_issue(issue_key, selected["id"])
        return {
            "ok": success,
            "transition_id": selected["id"],
            "transition_name": selected.get("name"),
            "to_status": selected.get("to", {}).get("name"),
        }

    async def ensure_issue_in_todo(self, issue_key: str) -> bool:
        """Place a newly-created backlog item in Jira's To Do category.

        Jira projects may use In Progress as their workflow's creation status.
        SELVIA's backlog export must not silently start implementation work, so
        this is called only for issues created during the current export.
        """
        issue = await self.get_issue(issue_key)
        status = (issue.get("fields") or {}).get("status") or {}
        name = str(status.get("name") or "").lower().replace(" ", "")
        category = str((status.get("statusCategory") or {}).get("key") or "").lower()
        if category == "new" or name in {"todo", "backlog", "new"}:
            return False
        result = await self.transition_issue_by_status_name(issue_key, "To Do")
        if not result.get("ok"):
            raise ValueError(f"Jira did not transition {issue_key} to To Do.")
        return True
