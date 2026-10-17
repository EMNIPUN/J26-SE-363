import uuid
from enum import Enum
from typing import Any

from shared.contracts import UserRole
from sqlalchemy import String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, JSONType, TimestampMixin, string_enum


class AgentRunStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class AgentRun(TimestampMixin, Base):
    """One orchestration request handled in the background, and its result.

    Scope ids are copied from the OrchestrationRequest as plain strings, without foreign
    keys: a run is a record of what was asked and must survive later changes to the
    entities it mentions (sprints and tasks are not Core API tables yet).
    """

    __tablename__ = "agent_runs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    request_id: Mapped[str] = mapped_column(String(64), unique=True)
    # None when the request carried a free-text `message` instead of an action.
    action: Mapped[str | None] = mapped_column(String(128))

    # RequesterContext: Keycloak subject and role of the user who asked.
    requester_id: Mapped[str] = mapped_column(String(255), index=True)
    requester_role: Mapped[UserRole] = mapped_column(string_enum(UserRole, "requester_role"))

    student_id: Mapped[str | None] = mapped_column(String(255))
    group_id: Mapped[str | None] = mapped_column(String(255), index=True)
    project_id: Mapped[str | None] = mapped_column(String(255), index=True)
    sprint_id: Mapped[str | None] = mapped_column(String(255))
    task_id: Mapped[str | None] = mapped_column(String(255))

    status: Mapped[AgentRunStatus] = mapped_column(
        string_enum(AgentRunStatus, "status"), default=AgentRunStatus.QUEUED, index=True
    )
    # OrchestrationResponse as JSON, set when the run finishes.
    response: Mapped[dict[str, Any] | None] = mapped_column(JSONType)
    # ErrorInfo as JSON ({"code", "message", "retryable"}), set when the run fails.
    error: Mapped[dict[str, Any] | None] = mapped_column(JSONType)
