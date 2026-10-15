import uuid
from typing import Any

from sqlalchemy import String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, JSONType, TimestampMixin


class DecompositionRecord(TimestampMixin, Base):
    """One versioned decomposition analysis result for a requirement.

    Mirrors RequirementQualityRecord: the full agent result is stored as JSON in
    ``result``; scope and requirement ref are columns for querying. History is the
    set of rows sharing (project_id, requirement_ref), ordered by created_at.
    """

    __tablename__ = "decomposition_results"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[str] = mapped_column(String(255), index=True)
    requirement_ref: Mapped[str] = mapped_column(String(64), index=True)
    requirement_text: Mapped[str] = mapped_column(Text)
    result: Mapped[dict[str, Any]] = mapped_column(JSONType)
