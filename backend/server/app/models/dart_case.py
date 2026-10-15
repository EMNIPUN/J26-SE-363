import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, JSONType, TimestampMixin


class DartCaseRecord(TimestampMixin, Base):
    """One DART arbitration case for a requirement.

    Stores the full five-step protocol result as JSON in ``result``.
    """

    __tablename__ = "dart_cases"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[str] = mapped_column(String(255), index=True)
    case_ref: Mapped[str] = mapped_column(String(64), index=True)
    requirement_ref: Mapped[str] = mapped_column(String(64), index=True)
    source_stage: Mapped[str] = mapped_column(String(32))
    category: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    result: Mapped[dict[str, Any]] = mapped_column(JSONType)
    resolved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
