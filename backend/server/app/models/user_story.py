import uuid
from typing import Any

from sqlalchemy import String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, JSONType, TimestampMixin


class UserStoryRecord(TimestampMixin, Base):
    """A student's user story, persisted by the Core API.

    The full story (title, acceptance_criteria, status, invest_result, tasks,
    bugs) is stored as JSON in ``data``; only the scope and refs are promoted to
    columns for querying. Source of truth — replace-on-update.
    """

    __tablename__ = "user_stories"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[str] = mapped_column(String(255), index=True)
    requirement_ref: Mapped[str] = mapped_column(String(64), index=True)
    story_ref: Mapped[str] = mapped_column(String(64), index=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSONType)
