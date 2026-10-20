import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, JSONType, TimestampMixin, string_enum
from app.models.enums import ReadyBacklogStatus

if TYPE_CHECKING:
    from app.models.decomposition_assessment import UserStory
    from app.models.pipeline_session import PipelineSession
    from app.models.requirement import Requirement


class BacklogReadinessPassport(TimestampMixin, Base):
    """The Backlog Readiness Passport for a user story.

    Persists trust-calibrated gate outcomes across Requirement Quality,
    Decomposition Coverage, INVEST Readiness, Story Points assignment,
    and DART uncertainty resolution.
    """

    __tablename__ = "rqa_backlog_passports"
    __table_args__ = (
        UniqueConstraint(
            "pipeline_session_id",
            "user_story_id",
            name="uq_rqa_backlog_passports_session_story",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    pipeline_session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rqa_pipeline_sessions.id", ondelete="CASCADE"), index=True
    )
    requirement_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rqa_requirements.id", ondelete="CASCADE"), index=True
    )
    user_story_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rqa_user_stories.id", ondelete="CASCADE"), index=True
    )
    overall_status: Mapped[ReadyBacklogStatus] = mapped_column(
        string_enum(ReadyBacklogStatus, "ready_backlog_status"),
        default=ReadyBacklogStatus.NOT_READY,
    )
    quality_gate_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    decomposition_gate_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    invest_gate_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    points_assigned: Mapped[bool] = mapped_column(Boolean, default=False)
    # These are human-readable diagnostic summaries, not bounded enum values.
    # Use Text so a detailed gate explanation cannot fail passport persistence.
    quality_status: Mapped[str] = mapped_column(Text, default="Not evaluated")
    coverage_status: Mapped[str] = mapped_column(Text, default="Not evaluated")
    invest_status: Mapped[str] = mapped_column(Text, default="Not evaluated")
    estimation_status: Mapped[str] = mapped_column(Text, default="Not assigned")
    dart_status: Mapped[str] = mapped_column(Text, default="Clear")
    readiness_gap: Mapped[str | None] = mapped_column(Text)
    student_action_required: Mapped[str | None] = mapped_column(Text)
    evidence_summary: Mapped[dict | None] = mapped_column(JSONType)
    passport_data: Mapped[dict | None] = mapped_column(JSONType)
    last_evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user_story: Mapped["UserStory"] = relationship("UserStory", foreign_keys=[user_story_id])
    requirement: Mapped["Requirement"] = relationship("Requirement", foreign_keys=[requirement_id])
