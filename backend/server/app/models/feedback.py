import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, string_enum
from app.models.enums import FeedbackStage, FeedbackType, Severity


class Feedback(TimestampMixin, Base):
    __tablename__ = "rqa_feedbacks"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    pipeline_session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rqa_pipeline_sessions.id", ondelete="CASCADE"), index=True
    )
    requirement_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("rqa_requirements.id", ondelete="CASCADE"), index=True
    )
    user_story_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("rqa_user_stories.id", ondelete="CASCADE")
    )
    target_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    dart_session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("rqa_dart_sessions.id", ondelete="SET NULL")
    )
    feedback_stage: Mapped[FeedbackStage] = mapped_column(
        string_enum(FeedbackStage, "feedback_stage")
    )
    feedback_type: Mapped[FeedbackType] = mapped_column(
        string_enum(FeedbackType, "feedback_type")
    )
    feedback_text: Mapped[str] = mapped_column(Text)
    standard_reference: Mapped[str | None] = mapped_column(String(255))
    severity: Mapped[Severity] = mapped_column(
        string_enum(Severity, "feedback_severity"), default=Severity.MEDIUM
    )
    is_dart_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    is_viewed: Mapped[bool] = mapped_column(Boolean, default=False)
    is_acted_upon: Mapped[bool] = mapped_column(Boolean, default=False)
    viewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    acted_upon_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
