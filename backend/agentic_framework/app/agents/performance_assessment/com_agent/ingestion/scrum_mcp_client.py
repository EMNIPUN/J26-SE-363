"""Scrum MCP client adapter layer for com_agent sprint and task evidence gathering.

Strictly aligned with:
- PLAN.md Section 4.1 (Custom Scrum Board MCP Server with 4 Tools)
- PLAN.md Section 12.6 (Retry Policy on Remote Calls)
- PLAN.md Section 12.8 (External Connector Mock Strategy)
"""

import abc
import json
import logging
import pathlib
import sys
from typing import Dict, List, Optional, Any
from app.agents.performance_assessment.com_agent.policies.retry_policy import retry_with_backoff
from app.agents.performance_assessment.com_agent.config.settings_loader import IS_DEV_MODE

logger = logging.getLogger(__name__)

MOCK_SCRUM_DIR = (
    pathlib.Path(__file__).resolve().parent.parent / "mock_context" / "mock_scrum_responses"
)


class ScrumMCPClientProtocol(abc.ABC):
    """Abstract interface contract for in-house Scrum Board MCP Server."""

    @abc.abstractmethod
    async def get_sprint_details(self, sprint_id: str) -> Dict[str, Any]:
        """Tool 1: Retrieve sprint metadata (dates, milestone, status)."""
        pass

    @abc.abstractmethod
    async def get_student_tasks(
        self, sprint_id: str, student_id: str
    ) -> List[Dict[str, Any]]:
        """Tool 2: Retrieve all backlog tasks assigned to a specific student in a sprint."""
        pass

    @abc.abstractmethod
    async def get_task_acceptance_criteria(self, task_id: str) -> Dict[str, Any]:
        """Tool 3: Retrieve functional acceptance criteria and descriptions for a task."""
        pass

    @abc.abstractmethod
    async def get_task_status_history(self, task_id: str) -> List[Dict[str, Any]]:
        """Tool 4: Retrieve chronological column transitions for a task."""
        pass


class MockScrumMCPClient(ScrumMCPClientProtocol):
    """Mock Scrum MCP client serving realistic fixture data."""

    def __init__(self, mock_dir: Optional[pathlib.Path] = None):
        self.mock_dir = mock_dir or MOCK_SCRUM_DIR

    def _load_fixture(self, filename: str) -> Any:
        path = self.mock_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Mock fixture not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    @retry_with_backoff(max_attempts=3, base_delay_seconds=0.1)
    async def get_sprint_details(self, sprint_id: str) -> Dict[str, Any]:
        data = self._load_fixture("sprint_details.json")
        return data

    @retry_with_backoff(max_attempts=3, base_delay_seconds=0.1)
    async def get_student_tasks(
        self, sprint_id: str, student_id: str
    ) -> List[Dict[str, Any]]:
        tasks: List[Dict[str, Any]] = self._load_fixture("student_tasks.json")
        filtered = [
            t
            for t in tasks
            if (not student_id or t.get("student_id") == student_id)
            and (not sprint_id or t.get("sprint_id") == sprint_id)
        ]
        return filtered

    @retry_with_backoff(max_attempts=3, base_delay_seconds=0.1)
    async def get_task_acceptance_criteria(self, task_id: str) -> Dict[str, Any]:
        criteria_map: Dict[str, Any] = self._load_fixture("task_acceptance_criteria.json")
        if task_id in criteria_map:
            return criteria_map[task_id]
        return {
            "task_id": task_id,
            "title": "Unknown Task",
            "description": "",
            "acceptance_criteria": [],
        }

    @retry_with_backoff(max_attempts=3, base_delay_seconds=0.1)
    async def get_task_status_history(self, task_id: str) -> List[Dict[str, Any]]:
        history_map: Dict[str, Any] = self._load_fixture("task_status_history.json")
        return history_map.get(task_id, [])


class RealScrumMCPClient(ScrumMCPClientProtocol):
    """Talks to the Scrum board MCP server (mcp_servers/scrum_board_server.py) over stdio.

    Use as ``async with RealScrumMCPClient() as scrum:`` to keep one server process for a whole run. Used without ``async with`` every call starts and stops its own
    server process (slower, but always correct).
    """

    def __init__(self, command: Optional[str] = None, args: Optional[List[str]] = None, env: Optional[Dict[str, str]] = None):
        server = pathlib.Path(__file__).resolve().parents[2] / "mcp_servers" / "scrum_board_server.py"
        self.command = command or sys.executable
        self.args = args if args is not None else [str(server)]
        self.env = env
        self._session = None
        self._stack = None

    async def __aenter__(self):
        from contextlib import AsyncExitStack
        from mcp import ClientSession
        from mcp.client.stdio import StdioServerParameters, stdio_client

        self._stack = AsyncExitStack()
        read, write = await self._stack.enter_async_context(stdio_client(StdioServerParameters(command=self.command, args=self.args, env=self.env)))
        self._session = await self._stack.enter_async_context(ClientSession(read, write))
        await self._session.initialize()
        return self

    async def __aexit__(self, *exc):
        if self._stack is not None:
            await self._stack.aclose()
        self._session = self._stack = None

    @staticmethod
    def _parse(result):
        if getattr(result, "isError", False):
            raise RuntimeError("Scrum MCP tool failed: " + " ".join(getattr(c, "text", "") for c in result.content)[:300])
        sc = getattr(result, "structuredContent", None)
        if sc is not None:
            return sc["result"] if isinstance(sc, dict) and set(sc) == {"result"} else sc
        texts = [json.loads(c.text) for c in result.content if getattr(c, "text", None)]
        return texts[0] if len(texts) == 1 else texts

    async def _call(self, tool: str, **arguments):
        if self._session is not None:
            return self._parse(await self._session.call_tool(tool, arguments))
        async with RealScrumMCPClient(self.command, self.args, self.env) as one_shot:
            return await one_shot._call(tool, **arguments)

    async def list_sprints(self, team_id: str) -> List[Dict[str, Any]]:
        return await self._call("list_sprints", team_id=team_id)

    async def get_team_roster(self, team_id: str) -> List[Dict[str, Any]]:
        return await self._call("get_team_roster", team_id=team_id)

    async def get_sprint_details(self, sprint_id: str) -> Dict[str, Any]:
        return await self._call("get_sprint_details", sprint_id=sprint_id)

    async def get_student_tasks(self, sprint_id: str, student_id: str) -> List[Dict[str, Any]]:
        return await self._call("get_student_tasks", sprint_id=sprint_id, student_id=student_id)

    async def get_task_acceptance_criteria(self, task_id: str) -> Dict[str, Any]:
        return await self._call("get_task_acceptance_criteria", task_id=task_id)

    async def get_task_status_history(self, task_id: str) -> List[Dict[str, Any]]:
        return await self._call("get_task_status_history", task_id=task_id)


def get_scrum_client(is_dev: Optional[bool] = None) -> ScrumMCPClientProtocol:
    """Factory creating configured Scrum MCP Client."""
    if is_dev is None:
        is_dev = IS_DEV_MODE
    return MockScrumMCPClient() if is_dev else RealScrumMCPClient()
