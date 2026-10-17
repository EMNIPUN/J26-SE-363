import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, JSONType, TimestampMixin


class Notification(TimestampMixin, Base):
    """Something that happened that one person should know about, shown in the web app.

    The same event may also be emailed; both are sent by one place (app/services/notifications).
    `kind` says what happened (see the catalog there). `ref` ties the row to what it is about
    (an invitation id, a team id) so it can be closed when that thing is answered. A row that was
    answered elsewhere gets `resolved_at` and stops offering its buttons.
    """

    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_user_id_created_at", "user_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    kind: Mapped[str] = mapped_column(String(48))
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str | None] = mapped_column(String(1000))
    # A path inside the web app, e.g. /teams/J26-SE-363/members.
    link: Mapped[str | None] = mapped_column(String(255))
    # Small facts the web app needs to act on it (team code, invitation id).
    data: Mapped[dict] = mapped_column(JSONType, default=dict)
    ref: Mapped[str | None] = mapped_column(String(64))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
