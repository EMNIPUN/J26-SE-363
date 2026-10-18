import uuid

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin


class NotificationPreference(TimestampMixin, Base):
    """Whether one person wants emails for one kind of notification. No row means the default
    (on). In-app notifications are always kept; this is only about email."""

    __tablename__ = "notification_preferences"
    __table_args__ = (UniqueConstraint("user_id", "category"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    category: Mapped[str] = mapped_column(String(32))
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
