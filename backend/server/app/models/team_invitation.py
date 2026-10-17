import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, string_enum
from app.models.group import MemberRole

if TYPE_CHECKING:
    from app.models.group import Group


class InvitationStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    REVOKED = "revoked"


class TeamInvitation(TimestampMixin, Base):
    """An invitation to join a team, addressed to an email address.

    The person may not have an account yet, so it is matched to the account whose verified
    email equals `email`. One row per team and address: inviting again after a decline or a
    revoke reopens the same row. "Expired" is not a status: it is `expires_at` in the past.
    """

    __tablename__ = "team_invitations"
    __table_args__ = (UniqueConstraint("group_id", "email"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    group_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("groups.id", ondelete="CASCADE"), index=True
    )
    # Lower case.
    email: Mapped[str] = mapped_column(String(320), index=True)
    role: Mapped[MemberRole] = mapped_column(string_enum(MemberRole, "role"))
    # Students only: becomes the team leader when this invitation is accepted.
    as_leader: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[InvitationStatus] = mapped_column(
        string_enum(InvitationStatus, "status"), default=InvitationStatus.PENDING
    )
    # SHA-256 of the secret in the email link; the secret itself is never stored.
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    invited_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )

    group: Mapped["Group"] = relationship()
