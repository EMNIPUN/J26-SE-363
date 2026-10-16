import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, string_enum
from app.models.enums import RequirementCategory

if TYPE_CHECKING:
    from app.models.pipeline_session import PipelineSession


class Requirement(TimestampMixin, Base):
    __tablename__ = "rqa_requirements"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    srs_document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("rqa_srs_documents.id", ondelete="CASCADE"), index=True
    )
    pipeline_session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rqa_pipeline_sessions.id", ondelete="CASCADE"), index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    group_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("groups.id", ondelete="CASCADE"), index=True
    )
    requirement_ref: Mapped[str] = mapped_column(String(20))
    requirement_category: Mapped[RequirementCategory] = mapped_column(
        string_enum(RequirementCategory, "requirement_category"),
        default=RequirementCategory.FUNCTIONAL,
    )
    requirement_text: Mapped[str] = mapped_column(Text)
    section_reference: Mapped[str | None] = mapped_column(String(100))
    extraction_confidence: Mapped[float | None] = mapped_column(Numeric(5, 2))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    pipeline_session: Mapped["PipelineSession"] = relationship(
        back_populates="requirements"
    )
