"""Rules shared by the team and invitation services.

The leader rules, in one place:
  * a team has at most one leader (`Group.leader_id`), and the leader is a student member;
  * the lecturer can flag one invited student as the leader; the flag takes effect when that
    student accepts;
  * if nobody is leader and no flagged invitation is still waiting, the student who joined
    first becomes leader, so a team is never left without one while it has students.
"""

import hashlib
import secrets
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    Group,
    GroupMember,
    InvitationStatus,
    MemberRole,
    TeamInvitation,
    TeamStatus,
)

EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


def utcnow() -> datetime:
    return datetime.now(UTC)


def as_utc(value: datetime | None) -> datetime | None:
    """SQLite hands back naive datetimes; treat them as UTC like PostgreSQL does."""
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def new_token() -> tuple[str, str]:
    """A secret for an email link and the SHA-256 that is stored instead of it."""
    raw = secrets.token_urlsafe(32)
    return raw, hash_token(raw)


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def is_expired(invitation: TeamInvitation, now: datetime | None = None) -> bool:
    return as_utc(invitation.expires_at) <= (now or utcnow())


def is_open(invitation: TeamInvitation, now: datetime | None = None) -> bool:
    """Pending and not past its expiry: the only state in which it can be answered."""
    return invitation.status is InvitationStatus.PENDING and not is_expired(
        invitation, now
    )


def invitation_state(invitation: TeamInvitation) -> str:
    if invitation.status is InvitationStatus.PENDING and is_expired(invitation):
        return "expired"
    return invitation.status.value


def mask_email(email: str) -> str:
    """j***@example.com: enough for someone to recognise their own address."""
    local, _, domain = email.partition("@")
    return f"{local[:1]}***@{domain}"


# --- loading ---------------------------------------------------------------------------------


def team_query():
    return select(Group).options(
        selectinload(Group.members).selectinload(GroupMember.user),
        selectinload(Group.projects),
        selectinload(Group.invitations),
    )


def find_team(db: Session, ref: str) -> Group | None:
    """A team by id or by code (codes are stored in upper case)."""
    try:
        return db.scalar(team_query().where(Group.id == uuid.UUID(ref)))
    except ValueError:
        return db.scalar(
            team_query().where(func.upper(Group.code) == ref.strip().upper())
        )


def membership(group: Group, user_id: uuid.UUID) -> GroupMember | None:
    return next((m for m in group.members if m.user_id == user_id), None)


def students(group: Group) -> list[GroupMember]:
    return [m for m in group.members if m.role is MemberRole.MEMBER]


def lecturers(group: Group) -> list[GroupMember]:
    return [m for m in group.members if m.role is MemberRole.LECTURER]


# --- invariants ------------------------------------------------------------------------------


def refresh_team(group: Group) -> None:
    """Restore the leader and status rules after anyone joined, left or an invitation closed."""
    team_students = students(group)
    student_ids = {m.user_id for m in team_students}

    if group.pending_leader_id and group.pending_leader_id not in student_ids:
        group.pending_leader_id = None
    if group.leader_id and group.leader_id not in student_ids:
        group.leader_id = None

    if group.leader_id is None and team_students:
        waiting_for_flagged_leader = any(
            i.status is InvitationStatus.PENDING and i.as_leader and is_open(i)
            for i in group.invitations
        )
        if not waiting_for_flagged_leader:
            first = min(
                team_students,
                key=lambda m: (as_utc(m.joined_at) or EPOCH, str(m.id)),
            )
            group.leader_id = first.user_id

    group.status = TeamStatus.ACTIVE if team_students else TeamStatus.FORMING
