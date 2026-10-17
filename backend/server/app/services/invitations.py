"""Inviting people to a team and answering invitations.

An invitation is addressed to an email address and matched to the account whose *verified* email
is that address, so it works whether or not the person has registered yet. The secret in the
email link is only used to find the invitation; answering it needs a signed-in account with the
right email, so a forwarded link is useless to anyone else.
"""

from dataclasses import dataclass
from datetime import timedelta

from shared.contracts import UserRole
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import ApiError, bad_request, conflict, forbidden, not_found
from app.models import (
    Group,
    GroupMember,
    InvitationStatus,
    MemberRole,
    TeamInvitation,
    TeamStatus,
    User,
)
from app.schemas.team import InvitationResult
from app.services import team_rules as rules
from app.services.email import Email, EmailService

# A cheap guard against using the invite feature to send mail to strangers at scale.
MAX_OPEN_INVITATIONS_PER_PERSON = 200


@dataclass
class Invited:
    results: list[InvitationResult]
    emails: list[Email]


# --- inviting --------------------------------------------------------------------------------


def invite(
    db: Session,
    group: Group,
    inviter: User,
    email_service: EmailService,
    *,
    students: list[str],
    lecturers: list[str],
    leader_email: str | None,
) -> Invited:
    """Create or reopen invitations. Flushes; the caller commits."""
    if leader_email and group.leader_id is not None:
        raise bad_request(
            "leader_exists",
            "This team already has a leader. Ask the leader to transfer leadership.",
        )
    if leader_email is None and students and not _has_leader_flag(group):
        leader_email = students[
            0
        ]  # nobody was named: the first student on the list leads
    own = (inviter.email or "").lower()
    if own and own in {*students, *lecturers}:
        raise bad_request(
            "cannot_invite_yourself", "You cannot invite your own email address"
        )

    _check_quota(db, inviter, len(students) + len(lecturers))
    if leader_email:  # only one invitation can carry the leader flag
        for other in group.invitations:
            if other.email != leader_email:
                other.as_leader = False
    member_emails = {m.user.email for m in group.members if m.user.email}
    # Students listed first: the first one is the default leader (see team_rules.refresh_team).
    wanted = [(e, MemberRole.MEMBER) for e in students] + [
        (e, MemberRole.LECTURER) for e in lecturers
    ]

    results: list[InvitationResult] = []
    emails: list[Email] = []
    for address, role in wanted:
        if address in member_emails:
            results.append(InvitationResult(email=address, outcome="already_member"))
            continue
        as_leader = role is MemberRole.MEMBER and address == leader_email
        existing = next((i for i in group.invitations if i.email == address), None)
        if existing is not None and rules.is_open(existing):
            if as_leader:  # the lecturer changed their mind about who leads
                existing.as_leader = True
            results.append(InvitationResult(email=address, outcome="already_invited"))
            continue

        raw, hashed = rules.new_token()
        expires = rules.utcnow() + timedelta(days=settings.INVITATION_TTL_DAYS)
        if existing is None:
            invitation = TeamInvitation(
                group_id=group.id,
                email=address,
                role=role,
                as_leader=as_leader,
                token_hash=hashed,
                expires_at=expires,
                invited_by_id=inviter.id,
            )
            group.invitations.append(invitation)
            outcome = "invited"
        else:  # declined, revoked, accepted-then-removed or expired: reopen the same row
            existing.role = role
            existing.as_leader = as_leader
            existing.status = InvitationStatus.PENDING
            existing.token_hash = hashed
            existing.expires_at = expires
            existing.responded_at = None
            existing.invited_by_id = inviter.id
            outcome = "reinvited"
        results.append(InvitationResult(email=address, outcome=outcome))
        if (
            group.status is not TeamStatus.PENDING
        ):  # a pending team's mail waits for activation
            emails.append(
                email_service.team_invitation(
                    address,
                    inviter_name=inviter.name,
                    team_name=group.name,
                    as_lecturer=role is MemberRole.LECTURER,
                    token=raw,
                    expires_in_days=settings.INVITATION_TTL_DAYS,
                )
            )
    db.flush()
    return Invited(results, emails)


def _has_leader_flag(group: Group) -> bool:
    """Does the team already have a leader, or an open invitation that will make one?"""
    return group.leader_id is not None or any(
        i.as_leader and rules.is_open(i) for i in group.invitations
    )


def ensure_leader_flag(group: Group) -> None:
    """If invitations were withdrawn along the way, the earliest remaining student leads."""
    if _has_leader_flag(group):
        return
    open_students = [
        i for i in group.invitations if i.role is MemberRole.MEMBER and rules.is_open(i)
    ]
    if open_students:
        first = min(open_students, key=lambda i: (rules.as_utc(i.created_at), i.email))
        first.as_leader = True


def send_open(group: Group, inviter: User, email_service: EmailService) -> list[Email]:
    """A fresh link for every invitation still waiting, e.g. when a pending team is activated."""
    return [
        _reissue(group, invitation, inviter, email_service)
        for invitation in group.invitations
        if rules.is_open(invitation)
    ]


def _check_quota(db: Session, inviter: User, adding: int) -> None:
    open_count = (
        db.scalar(
            select(func.count())
            .select_from(TeamInvitation)
            .where(
                TeamInvitation.invited_by_id == inviter.id,
                TeamInvitation.status == InvitationStatus.PENDING,
                TeamInvitation.expires_at > rules.utcnow(),
            )
        )
        or 0
    )
    if open_count + adding > MAX_OPEN_INVITATIONS_PER_PERSON:
        raise ApiError(
            429,
            "too_many_invitations",
            "You have too many invitations waiting for an answer. Remove some or wait for replies.",
        )


def revoke(group: Group, invitation_id) -> None:
    invitation = _in_team(group, invitation_id)
    if invitation.status is not InvitationStatus.PENDING:
        raise conflict("invitation_closed", "This invitation has already been answered")
    invitation.status = InvitationStatus.REVOKED
    invitation.responded_at = rules.utcnow()
    rules.refresh_team(group)


def resend(
    group: Group, invitation_id, inviter: User, email_service: EmailService
) -> Email:
    invitation = _in_team(group, invitation_id)
    if group.status is TeamStatus.PENDING:
        raise conflict(
            "team_pending", "Invitations are sent when the team's setup is finished"
        )
    if invitation.status is not InvitationStatus.PENDING:
        raise conflict("invitation_closed", "This invitation has already been answered")
    return _reissue(group, invitation, inviter, email_service)


def _reissue(
    group: Group,
    invitation: TeamInvitation,
    inviter: User,
    email_service: EmailService,
) -> Email:
    # The secret is not stored, so sending again means issuing a new one (the old link stops).
    raw, hashed = rules.new_token()
    invitation.token_hash = hashed
    invitation.expires_at = rules.utcnow() + timedelta(
        days=settings.INVITATION_TTL_DAYS
    )
    return email_service.team_invitation(
        invitation.email,
        inviter_name=inviter.name,
        team_name=group.name,
        as_lecturer=invitation.role is MemberRole.LECTURER,
        token=raw,
        expires_in_days=settings.INVITATION_TTL_DAYS,
    )


def _in_team(group: Group, invitation_id) -> TeamInvitation:
    invitation = next((i for i in group.invitations if i.id == invitation_id), None)
    if invitation is None:
        raise not_found("Invitation not found")
    return invitation


def sent_by(db: Session, user: User) -> list[TeamInvitation]:
    """Invitations this person sent that are still open, oldest first, for teams that are open."""
    rows = db.scalars(
        select(TeamInvitation)
        .join(Group, Group.id == TeamInvitation.group_id)
        .where(
            TeamInvitation.invited_by_id == user.id,
            TeamInvitation.status == InvitationStatus.PENDING,
            Group.status != TeamStatus.PENDING,
        )
        .order_by(TeamInvitation.created_at.asc())
        .limit(100)
    ).all()
    return [row for row in rows if rules.is_open(row)]


# --- the invited person ----------------------------------------------------------------------


def open_for_email(db: Session, email: str) -> list[TeamInvitation]:
    rows = db.scalars(
        select(TeamInvitation)
        .join(Group, Group.id == TeamInvitation.group_id)
        .where(
            TeamInvitation.email == email,
            TeamInvitation.status == InvitationStatus.PENDING,
            Group.status
            != TeamStatus.PENDING,  # a team still being set up is not offered yet
        )
        .order_by(TeamInvitation.created_at.desc())
    ).all()
    return [row for row in rows if rules.is_open(row)]


def find_by_token(db: Session, token: str) -> TeamInvitation | None:
    return db.scalar(
        select(TeamInvitation).where(
            TeamInvitation.token_hash == rules.hash_token(token)
        )
    )


def lookup_by_token(db: Session, token: str, email: str | None) -> TeamInvitation:
    """The invitation behind an email link, for the person it was sent to."""
    invitation = find_by_token(db, token)
    if (
        invitation is None
        or not rules.is_open(invitation)
        or invitation.group.status is TeamStatus.PENDING
    ):
        raise ApiError(
            410, "invitation_invalid", "This invitation link is no longer valid"
        )
    if email is None:
        raise forbidden(
            "email_not_verified", "Verify your email address to see this invitation"
        )
    if invitation.email != email:
        raise forbidden(
            "invitation_wrong_account",
            f"This invitation was sent to {rules.mask_email(invitation.email)}. "
            "Sign in with that address.",
        )
    return invitation


def respond(
    db: Session,
    user: User,
    role: UserRole | None,
    email: str | None,
    invitation_id,
    *,
    accept: bool,
    email_service: EmailService,
) -> tuple[Group, list[Email]]:
    """Accept or decline. Commits."""
    if email is None:
        raise forbidden(
            "email_not_verified", "Verify your email address to answer invitations"
        )
    invitation = db.get(TeamInvitation, invitation_id)
    if invitation is None or invitation.email != email:
        # Same answer for "does not exist" and "not yours".
        raise not_found("Invitation not found")
    if not rules.is_open(invitation):
        raise ApiError(410, "invitation_invalid", "This invitation is no longer open")

    # Lock the team row so two answers (or an answer and a removal) cannot interleave.
    group = db.scalar(
        rules.team_query().where(Group.id == invitation.group_id).with_for_update()
    )
    invitation = next(i for i in group.invitations if i.id == invitation.id)
    if group.status is TeamStatus.PENDING:
        raise ApiError(410, "invitation_invalid", "This invitation is no longer open")

    now = rules.utcnow()
    if accept:
        _join(db, group, user, role, invitation, now)
        invitation.status = InvitationStatus.ACCEPTED
    else:
        invitation.status = InvitationStatus.DECLINED
    invitation.responded_at = now
    rules.refresh_team(group)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise conflict("already_in_team", "You cannot join this team") from exc

    emails: list[Email] = []
    inviter = (
        db.get(User, invitation.invited_by_id) if invitation.invited_by_id else None
    )
    if inviter is not None and inviter.email:
        emails.append(
            email_service.invitation_response(
                inviter.email,
                member_name=user.name,
                team_name=group.name,
                accepted=accept,
            )
        )
    return group, emails


def _join(
    db: Session,
    group: Group,
    user: User,
    role: UserRole | None,
    invitation: TeamInvitation,
    now,
) -> None:
    is_student_invite = invitation.role is MemberRole.MEMBER
    needed = UserRole.STUDENT if is_student_invite else UserRole.LECTURER
    if role is not needed:
        raise forbidden(
            "role_mismatch",
            f"This invitation is for a {needed.value} account. Your account is set up as "
            f"a {role.value if role else 'new'} account.",
        )
    if rules.membership(group, user.id) is not None:
        raise conflict("already_in_team", "You are already in this team")

    term = group.term if is_student_invite else None
    if term:
        other = db.scalar(
            select(Group)
            .join(GroupMember, GroupMember.group_id == Group.id)
            .where(GroupMember.user_id == user.id, GroupMember.term == term)
        )
        if other is not None:
            raise conflict(
                "already_in_team_for_term",
                f"You are already in {other.name} for {term}. A student can be in one team per term.",
            )

    group.members.append(
        GroupMember(
            user_id=user.id,
            user=user,
            role=invitation.role,
            term=term,
            joined_at=now,
        )
    )
    if is_student_invite and invitation.as_leader and group.leader_id is None:
        group.leader_id = user.id
