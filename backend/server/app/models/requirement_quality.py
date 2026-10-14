import uuid
from typing import Any

from sqlalchemy import String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, JSONType, TimestampMixin


class RequirementQualityRecord(TimestampMixin, Base):
    """One scored version of a requirement, persisted by the Core API.

    The full quality result (scores, rationale, smells, rewrite, confidence,
    retrieval evidence, title/priority) is stored as JSON in ``result``; only the
    scope and the requirement ref are promoted to columns for querying. History is
    the set of rows sharing (project_id, requirement_ref), ordered by created_at.
    Scope ids are plain strings (no FKs), like agent_runs.
    """

    __tablename__ = "requirement_quality_results"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    # Scope: the team/project the requirement belongs to.
    project_id: Mapped[str] = mapped_column(String(255), index=True)
    requirement_ref: Mapped[str] = mapped_column(String(64), index=True)
    requirement_text: Mapped[str] = mapped_column(Text)
    # The mapped quality result (overall_score, status, dimension_scores, smells,
    # suggested_rewrite, confidence, dart_triggered, retrieval, title, priority).
    result: Mapped[dict[str, Any]] = mapped_column(JSONType)
