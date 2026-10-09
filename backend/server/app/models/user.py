import uuid
from typing import TYPE_CHECKING

from shared.contracts import UserRole
from sqlalchemy import String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, string_enum

if TYPE_CHECKING:
    from app.models.group import GroupMember


class User(TimestampMixin, Base):
    """A person who has signed in through Keycloak (student, lecturer or admin)."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    # Keycloak subject (`sub` claim); the only link between a token and this row.
    keycloak_sub: Mapped[str] = mapped_column(String(255), unique=True)
    role: Mapped[UserRole] = mapped_column(string_enum(UserRole, "role"))
    name: Mapped[str] = mapped_column(String(255))
    student_number: Mapped[str | None] = mapped_column(String(32), unique=True)

    memberships: Mapped[list["GroupMember"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
