"""Read-only JSON Scrum fixtures matched to a team's connected repository."""
from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, ValidationError


DEFAULT_FIXTURE_DIR = Path(__file__).resolve().parents[3] / "data" / "scrum_simulator"


def normalize_repo_url(value: str) -> str:
    parsed = urlsplit((value or "").strip())
    host = (parsed.hostname or "").lower()
    path = parsed.path.rstrip("/").lower()
    if host == "www.github.com":
        host = "github.com"
    return f"https://{host}{path}" if host and path else ""


class FixtureProject(BaseModel):
    model_config = ConfigDict(extra="forbid")
    project_id: str = Field(min_length=1)
    project_name: str = Field(min_length=1)
    project_domain: str = ""


class FixtureStudent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    student_id: str = Field(min_length=1)
    name: str = ""
    email: str = ""


class FixtureSprint(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sprint_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    goal: str = ""
    start_date: date
    end_date: date
    status: str


class FixtureTask(BaseModel):
    model_config = ConfigDict(extra="forbid")
    task_id: str = Field(min_length=1)
    sprint_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str = ""
    status: str
    priority: str = ""
    assignee_ids: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    labels: list[str] = Field(default_factory=list)
    story_points: int = Field(default=0, ge=0)
    subtask_count: int = Field(default=0, ge=0)
    linked_commits: list[str] = []
    completed_by: str | None = None
    carried_over_from: str | None = None


class ScrumFixture(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: str = "1"
    github_repo_url: HttpUrl
    project: FixtureProject
    students: list[FixtureStudent]
    sprints: list[FixtureSprint]
    tasks: list[FixtureTask]
    status_history: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)


from functools import lru_cache


@lru_cache(maxsize=4)
def _load_fixtures_cached(fixture_dir_str: str) -> list[ScrumFixture]:
    p = Path(fixture_dir_str)
    if not p.exists():
        return []
    fixtures: list[ScrumFixture] = []
    for path in sorted(p.glob("*.json")):
        if path.name.endswith(".schema.json"):
            continue
        try:
            fixtures.append(ScrumFixture.model_validate_json(path.read_text(encoding="utf-8")))
        except (OSError, ValidationError, json.JSONDecodeError) as exc:
            raise ValueError(f"Invalid Scrum simulator fixture {path.name}: {exc}") from exc
    return fixtures


class ScrumSimulator:
    def __init__(self, fixture_dir: str | os.PathLike[str] | None = None):
        self.fixture_dir = Path(fixture_dir or os.environ.get("SCRUM_SIMULATOR_DATA_DIR") or DEFAULT_FIXTURE_DIR)
        self.fixtures = _load_fixtures_cached(str(self.fixture_dir))

    def match(self, repo_url: str) -> ScrumFixture | None:
        normalized = normalize_repo_url(repo_url)
        matches = [f for f in self.fixtures if normalize_repo_url(str(f.github_repo_url)) == normalized]
        if matches:
            return matches[0]
        # Match by repository name (allowing forks or owner differences)
        repo_name = normalized.rstrip("/").split("/")[-1].lower() if normalized else ""
        if repo_name:
            for f in self.fixtures:
                f_name = normalize_repo_url(str(f.github_repo_url)).rstrip("/").split("/")[-1].lower()
                if f_name == repo_name:
                    return f
        # Fallback: if only one fixture is configured in the system, serve it
        if len(self.fixtures) == 1:
            return self.fixtures[0]
        return None

    @staticmethod
    def _sprint(fixture: ScrumFixture, sprint: FixtureSprint) -> dict[str, Any]:
        tasks = [t for t in fixture.tasks if t.sprint_id == sprint.sprint_id]
        done = [t for t in tasks if t.status.lower() == "done"]
        return {
            "sprint_id": sprint.sprint_id, "team_id": fixture.project.project_id,
            "name": sprint.name, "goal": sprint.goal,
            "start_date": sprint.start_date.isoformat(), "end_date": sprint.end_date.isoformat(),
            "length_days": (sprint.end_date - sprint.start_date).days,
            "status": sprint.status, "project_domain": fixture.project.project_domain,
            "total_story_points": sum(t.story_points for t in tasks),
            "completed_story_points": sum(t.story_points for t in done),
            "task_count": len(tasks),
        }

    def payload(self, operation: str, repo_url: str, **params: str) -> Any:
        fixture = self.match(repo_url)
        if fixture is None:
            raise LookupError("No Scrum fixture is configured for this repository")
        if operation == "list_sprints":
            return [self._sprint(fixture, s) for s in fixture.sprints]
        if operation == "get_team_roster":
            return [{"student_id": s.student_id, "name": s.name, "email": s.email, "team_id": fixture.project.project_id} for s in fixture.students]
        if operation == "get_sprint_details":
            sprint = next((s for s in fixture.sprints if s.sprint_id == params["sprint_id"]), None)
            return self._sprint(fixture, sprint) if sprint else {"error": f"unknown sprint {params['sprint_id']}"}
        if operation == "get_student_tasks":
            student_id = params.get("student_id", "")
            return [self._task(t, fixture) for t in fixture.tasks if t.sprint_id == params["sprint_id"] and (not student_id or student_id in t.assignee_ids)]
        if operation == "get_task_acceptance_criteria":
            task = next((t for t in fixture.tasks if t.task_id == params["task_id"]), None)
            return {"task_id": params["task_id"], "title": task.title if task else "Unknown task", "description": task.description if task else "", "acceptance_criteria": task.acceptance_criteria if task else []}
        if operation == "get_task_status_history":
            return fixture.status_history.get(params["task_id"], [{"status": next((t.status for t in fixture.tasks if t.task_id == params["task_id"]), "unknown"), "at": None, "source": "fixture_final_status"}])
        raise ValueError(f"Unknown Scrum operation {operation}")

    @staticmethod
    def _task(task: FixtureTask, fixture: ScrumFixture) -> dict[str, Any]:
        return {"task_id": task.task_id, "student_id": task.assignee_ids[0] if task.assignee_ids else "", "student_ids": task.assignee_ids, "sprint_id": task.sprint_id, "title": task.title, "story": task.title, "story_points": task.story_points, "subtask_count": task.subtask_count, "status": task.status, "completed_by": task.completed_by, "carried_over_from": task.carried_over_from, "linked_commits": task.linked_commits, "description": task.description, "assignee_ids": task.assignee_ids}
