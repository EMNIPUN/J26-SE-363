import uuid

from sqlalchemy import ForeignKey, Integer, Numeric, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, string_enum
from app.models.enums import EstimationSource, Priority, TaskStatus, TaskType


class SprintBacklogItem(TimestampMixin, Base):
    __tablename__ = "rqa_sprint_backlog_items"
    __table_args__ = (UniqueConstraint("pipeline_session_id", "user_story_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    pipeline_session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rqa_pipeline_sessions.id", ondelete="CASCADE"), index=True
    )
    user_story_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rqa_user_stories.id", ondelete="CASCADE"), index=True
    )
    requirement_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rqa_requirements.id", ondelete="CASCADE"), index=True
    )
    sprint_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("rqa_sprints.id", ondelete="SET NULL"), index=True
    )
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    task_type: Mapped[TaskType] = mapped_column(
        string_enum(TaskType, "backlog_task_type"), default=TaskType.STORY
    )
    task_description: Mapped[str | None] = mapped_column(Text)
    final_story_points: Mapped[int] = mapped_column(Integer)
    final_estimated_hours: Mapped[float | None] = mapped_column(Numeric(8, 2))
    priority: Mapped[Priority] = mapped_column(
        string_enum(Priority, "backlog_priority"), default=Priority.MEDIUM
    )
    status: Mapped[TaskStatus] = mapped_column(
        string_enum(TaskStatus, "backlog_task_status"), default=TaskStatus.TODO
    )
    estimation_source: Mapped[EstimationSource] = mapped_column(
        string_enum(EstimationSource, "backlog_estimation_source"),
        default=EstimationSource.STUDENT_ONLY,
    )
