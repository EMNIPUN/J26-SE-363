"""Sprint snapshot providers for the Adaptive AI Tutor.

Fixture-backed data is injected by callers. A future shared database or planning
provider can implement the same protocol without changing the context builder.
"""

from typing import Protocol

from app.agents.adaptive_tutor.schemas import SprintSnapshot


class SprintDataProviderError(ValueError):
    """Raised when a sprint snapshot cannot be retrieved."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class SprintDataProvider(Protocol):
    """Boundary for loading sprint-scoped task data."""

    def get_sprint_snapshot(self, project_id: str, sprint_id: str) -> SprintSnapshot:
        """Return the sprint snapshot for the given project and sprint."""


class FixtureSprintDataProvider:
    """In-memory provider; snapshots are supplied by fixtures or tests."""

    def __init__(self, snapshots: dict[tuple[str, str], SprintSnapshot]):
        self._snapshots = snapshots

    def get_sprint_snapshot(self, project_id: str, sprint_id: str) -> SprintSnapshot:
        if not isinstance(project_id, str) or project_id.strip() == "":
            raise SprintDataProviderError(
                "missing_project_id",
                "project_id is required to load a sprint snapshot.",
            )
        if not isinstance(sprint_id, str) or sprint_id.strip() == "":
            raise SprintDataProviderError(
                "missing_sprint_id",
                "sprint_id is required to load a sprint snapshot.",
            )

        key = (project_id.strip(), sprint_id.strip())
        snapshot = self._snapshots.get(key)
        if snapshot is None:
            raise SprintDataProviderError(
                "unknown_sprint",
                "No sprint snapshot exists for the requested project and sprint.",
            )
        return snapshot
