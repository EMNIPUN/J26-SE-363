import uuid

from sqlalchemy import ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin


class Term(TimestampMixin, Base):
    """An academic term a team can belong to, e.g. "2026-S1".

    Lecturers add terms as they need them. `Group.term` holds the name, not a foreign key, so a
    team keeps its term even if the list is ever tidied.
    """

    __tablename__ = "terms"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(32), unique=True)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
