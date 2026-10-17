import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, string_enum

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.user import User


class TeamStatus(str, Enum):
    FORMING = "forming"  # created, nobody has accepted yet
    ACTIVE = "active"  # at least one student has joined


class MemberRole(str, Enum):
    LECTURER = "lecturer"  # evaluates the team, takes no part in development
    MEMBER = "member"  # a student; the team leader is a member named by `Group.leader_id`


class Group(TimestampMixin, Base):
    """A student project group, shown to people as a "team"."""

    __tablename__ = "groups"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    # Stable identifier used in URLs and across the university, e.g. "J26-SE-363".
    code: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    # Academic term, e.g. "2026-S1". A student can be in one team per term.
    term: Mapped[str | None] = mapped_column(String(32))
    status: Mapped[TeamStatus] = mapped_column(
        string_enum(TeamStatus, "status"), default=TeamStatus.FORMING
    )
    repo_url: Mapped[str | None] = mapped_column(String(1024))
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    # One leader per team: a single column cannot hold two people. Must be a student member.
    leader_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    # Member the leader offered the role to; becomes `leader_id` once they accept.
    pending_leader_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )

    members: Mapped[list["GroupMember"]] = relationship(
        back_populates="group", cascade="all, delete-orphan", passive_deletes=True
    )
    projects: Mapped[list["Project"]] = relationship(back_populates="group")


class GroupMember(Base):
    """Membership of one user in one group."""

    __tablename__ = "group_members"
    __table_args__ = (
        UniqueConstraint("group_id", "user_id"),
        # Students only (NULL for lecturers, and NULLs never collide): one team per term.
        UniqueConstraint("user_id", "term"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    group_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"))
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[MemberRole] = mapped_column(
        string_enum(MemberRole, "role"), default=MemberRole.MEMBER
    )
    # Copy of the group's term for student members; see the unique constraint above.
    term: Mapped[str | None] = mapped_column(String(32))
    joined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    group: Mapped["Group"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship(back_populates="memberships")
