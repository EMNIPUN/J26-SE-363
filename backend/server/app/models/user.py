import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from shared.contracts import UserRole
from sqlalchemy import DateTime, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, string_enum

if TYPE_CHECKING:
    from app.models.group import GroupMember


class User(TimestampMixin, Base):
    """A person who has signed in through Keycloak.

    The row is created on the first authenticated request. `role` stays empty until the person
    finishes onboarding and chooses to be a student or a lecturer (administrators get theirs from
    Keycloak, see app/core/security.py).
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    # Keycloak subject (`sub` claim); the only link between a token and this row.
    keycloak_sub: Mapped[str] = mapped_column(String(255), unique=True)
    role: Mapped[UserRole | None] = mapped_column(string_enum(UserRole, "role"))
    name: Mapped[str] = mapped_column(String(255))
    # Copied from the token on every request; invitations are matched against it.
    email: Mapped[str | None] = mapped_column(String(320), index=True)
    student_number: Mapped[str | None] = mapped_column(String(32), unique=True)
    institution: Mapped[str | None] = mapped_column(String(255))
    # Lecturers only.
    department: Mapped[str | None] = mapped_column(String(255))
    title: Mapped[str | None] = mapped_column(String(128))
    # Students only. Stored in lower case: two accounts cannot claim the same GitHub login.
    github_username: Mapped[str | None] = mapped_column(String(64), unique=True)
    consent_version: Mapped[str | None] = mapped_column(String(32))
    consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    onboarding_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    memberships: Mapped[list["GroupMember"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )

    @property
    def is_onboarded(self) -> bool:
        return self.onboarding_completed_at is not None
