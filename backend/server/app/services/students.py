"""Students who are not in a team yet, for a lecturer to invite.

Anyone can register as a lecturer (there is no approval step), so the list is deliberately narrow:
only students who gave the *same institution* as the lecturer, only their name, institution,
GitHub login and picture (the list has no email), and invitations go out by id: the address is
looked up here for the invitation email. Once invited, a student shows in the team's invitation list
with their address like any other invitee, so this narrows what a lecturer can discover, it does
not hide it. A real fix for open lecturer sign-up is an approval step (docs/REGISTRATION_AND_TEAMS.md).
"""

import uuid

from shared.contracts import UserRole
from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session

from app.core.errors import bad_request
from app.models import Group, GroupMember, User

MAX_LISTED = 200


def _without_team(term: str):
    return ~exists().where(GroupMember.user_id == User.id, GroupMember.term == term)


def _candidates(lecturer: User, term: str):
    institution = (lecturer.institution or "").strip().lower()
    return select(User).where(
        User.role == UserRole.STUDENT,
        User.onboarding_completed_at.is_not(None),
        User.email.is_not(None),
        func.lower(func.trim(User.institution)) == institution,
        _without_team(term),
    )


def available(db: Session, lecturer: User, term: str) -> list[User]:
    if not (lecturer.institution or "").strip():
        return []
    rows = db.scalars(_candidates(lecturer, term).order_by(User.name).limit(MAX_LISTED))
    return list(rows)


def emails_for(
    db: Session, lecturer: User, group: Group, ids: list[uuid.UUID]
) -> list[str]:
    """The addresses of these students, or "student_not_available" if any of them may not be
    invited to this team by this lecturer (not a student, another institution, already in a team
    that term)."""
    if not ids:
        return []
    if group.term is None:
        raise bad_request("student_not_available", "This team has no term")
    wanted = set(ids)
    rows = db.scalars(
        _candidates(lecturer, group.term).where(User.id.in_(wanted))
    ).all()
    if {u.id for u in rows} != wanted:
        raise bad_request(
            "student_not_available",
            "One of those students cannot be invited to this team",
        )
    return [u.email for u in rows]
