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
    """Production Scrum MCP client interface (stub for external MCP connector)."""

    async def get_sprint_details(self, sprint_id: str) -> Dict[str, Any]:
        raise NotImplementedError(
            "RealScrumMCPClient requires custom in-house Scrum MCP server in production"
        )

    async def get_student_tasks(
        self, sprint_id: str, student_id: str
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError(
            "RealScrumMCPClient requires custom in-house Scrum MCP server in production"
        )

    async def get_task_acceptance_criteria(self, task_id: str) -> Dict[str, Any]:
        raise NotImplementedError(
            "RealScrumMCPClient requires custom in-house Scrum MCP server in production"
        )

    async def get_task_status_history(self, task_id: str) -> List[Dict[str, Any]]:
        raise NotImplementedError(
            "RealScrumMCPClient requires custom in-house Scrum MCP server in production"
        )


def get_scrum_client(is_dev: Optional[bool] = None) -> ScrumMCPClientProtocol:
    """Factory creating configured Scrum MCP Client."""
    if is_dev is None:
        is_dev = IS_DEV_MODE
    return MockScrumMCPClient() if is_dev else RealScrumMCPClient()
