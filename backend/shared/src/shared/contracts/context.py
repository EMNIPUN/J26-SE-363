"""Project context shared by the Core API, the AI Backend and every agent.

Relationship: Student -> Group -> Project -> Sprint -> Task.
Project titles are not unique (several groups may build the same project), so
every entity is identified by its id.
"""

from datetime import date
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator


class UserRole(str, Enum):
    STUDENT = "student"
    LECTURER = "lecturer"
    ADMIN = "admin"


class RequesterContext(BaseModel):
    """Who made the request. Filled in by the Core API from the verified user."""

    user_id: str
    role: UserRole


class StudentContext(BaseModel):
    student_id: str
    name: str | None = None


class GroupContext(BaseModel):
    group_id: str
    name: str | None = None
    member_ids: list[str] = Field(default_factory=list)


class ProjectContext(BaseModel):
    project_id: str
    title: str | None = None
    group_id: str | None = None


class SprintContext(BaseModel):
    sprint_id: str
    name: str | None = None
    number: int | None = None
    start_date: date | None = None
    end_date: date | None = None


class TaskContext(BaseModel):
    task_id: str
    title: str | None = None
    sprint_id: str | None = None
    assignee_ids: list[str] = Field(default_factory=list)


class SelviaContext(BaseModel):
    """Everything known about the student's current project position."""

    student: StudentContext | None = None
    group: GroupContext | None = None
    project: ProjectContext | None = None
    sprint: SprintContext | None = None
    task: TaskContext | None = None


_SCOPE_FIELDS = (
    ("student_id", "student"),
    ("group_id", "group"),
    ("project_id", "project"),
    ("sprint_id", "sprint"),
    ("task_id", "task"),
)


class ScopedRequest(BaseModel):
    """Base for requests that target a student/group/project scope.

    The flat ids are the source of truth for routing and access checks; `context`
    carries optional details. Missing ids are taken from `context`, and a
    mismatch between the two is rejected.
    """

    request_id: str = Field(default_factory=lambda: str(uuid4()))
    student_id: str | None = None
    group_id: str | None = None
    project_id: str | None = None
    sprint_id: str | None = None
    task_id: str | None = None
    context: SelviaContext = Field(default_factory=SelviaContext)

    @model_validator(mode="after")
    def _align_ids_with_context(self) -> "ScopedRequest":
        for id_field, context_field in _SCOPE_FIELDS:
            entity = getattr(self.context, context_field)
            if entity is None:
                continue
            context_id = getattr(entity, id_field)
            own_id = getattr(self, id_field)
            if own_id is None:
                setattr(self, id_field, context_id)
            elif own_id != context_id:
                raise ValueError(
                    f"{id_field}={own_id!r} does not match context.{context_field}.{id_field}={context_id!r}"
                )
        return self
