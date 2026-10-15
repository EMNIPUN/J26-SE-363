import uuid
from typing import Any

from sqlalchemy import String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, JSONType, TimestampMixin


class SprintTaskRecord(TimestampMixin, Base):
    """A sprint task created when a student confirms an effort estimate.

    The full task payload (title, points, assigneeId, dueDate, blockedReason,
    dependsOn) is stored as JSON in ``data``; only the scope and refs are
    promoted to columns for querying.
    """

    __tablename__ = "sprint_tasks"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[str] = mapped_column(String(255), index=True)
    task_ref: Mapped[str] = mapped_column(String(64), index=True)
    story_ref: Mapped[str] = mapped_column(String(64), index=True)
    requirement_ref: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), default="Todo")
    data: Mapped[dict[str, Any]] = mapped_column(JSONType)
