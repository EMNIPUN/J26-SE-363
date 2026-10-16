import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, string_enum
from app.models.enums import PipelineStage, SessionStatus

if TYPE_CHECKING:
    from app.models.quality_assessment import QualityGateDecision
    from app.models.requirement import Requirement
    from app.models.srs_document import SrsDocument


class PipelineSession(TimestampMixin, Base):
    __tablename__ = "rqa_pipeline_sessions"
    __table_args__ = (UniqueConstraint("group_id", "version"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    group_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("groups.id", ondelete="CASCADE"), index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    initiated_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    current_stage: Mapped[PipelineStage] = mapped_column(
        string_enum(PipelineStage, "pipeline_stage"), default=PipelineStage.PARSING
    )
    status: Mapped[SessionStatus] = mapped_column(
        string_enum(SessionStatus, "session_status"), default=SessionStatus.ACTIVE
    )
    version: Mapped[int] = mapped_column(Integer, default=1)
    dart_activation_count: Mapped[int] = mapped_column(Integer, default=0)
    overall_composite_score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    srs_document: Mapped["SrsDocument | None"] = relationship(
        back_populates="pipeline_session", uselist=False
    )
    requirements: Mapped[list["Requirement"]] = relationship(
        back_populates="pipeline_session"
    )
    quality_gate_decision: Mapped["QualityGateDecision | None"] = relationship(
        back_populates="pipeline_session", uselist=False
    )
