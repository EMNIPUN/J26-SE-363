import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin


class Sprint(TimestampMixin, Base):
    __tablename__ = "rqa_sprints"
    __table_args__ = (UniqueConstraint("project_id", "sprint_number"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    sprint_number: Mapped[int] = mapped_column(Integer)
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(32), default="planning")
    jira_sprint_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    jira_state: Mapped[str | None] = mapped_column(String(32), nullable=True)
    jira_goal: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    jira_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    jira_last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
