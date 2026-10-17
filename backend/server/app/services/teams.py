"""Creating and running a team: details, members and leadership.

Who may do what:
  create a team            lecturers (it stays "pending" until its setup is finished)
  invite, edit, remove     the team's lecturers (lecturers evaluate; they never develop)
  set the repository URL   the team's lecturers and its leader
  leave                    any member, except the leader while other students remain
  transfer leadership      the leader (or a lecturer); the chosen student has to accept
"""

import re
import secrets
import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import bad_request, conflict, forbidden, not_found
from app.models import Group, GroupMember, MemberRole, Project, TeamStatus, User
from app.schemas.team import ProjectUpdate, TeamCreate, TeamUpdate
from app.services import invitations, terms
from app.services import team_rules as rules
from app.services.email import Email, EmailService


def _generate_code(db: Session, name: str) -> str:
    base = re.sub(r"[^A-Z0-9]+", "-", name.upper()).strip("-")[:40] or "TEAM"
    candidates = [base, *(f"{base}-{n}" for n in range(2, 10))]
    for candidate in candidates:
        if len(candidate) >= 2 and not _code_exists(db, candidate):
            return candidate
    return f"{base}-{secrets.token_hex(3).upper()}"


def _code_exists(db: Session, code: str) -> bool:
    return (
        db.scalar(
            select(func.count())
            .select_from(Group)
            .where(func.upper(Group.code) == code)
        )
        > 0
    )


# --- access ----------------------------------------------------------------------------------


def team_for(
    db: Session, ref: str, user: User, *, is_admin: bool = False
) -> tuple[Group, GroupMember | None]:
    """The team, if this person belongs to it (or is an administrator). Otherwise "not found",
    so teams cannot be discovered by guessing codes."""
    group = rules.find_team(db, ref)
    member = rules.membership(group, user.id) if group else None
    if group is None or (member is None and not is_admin):
        raise not_found("Team not found")
    return group, member


def require_lecturer(member: GroupMember | None) -> GroupMember:
    if member is None or member.role is not MemberRole.LECTURER:
        raise forbidden("lecturer_only", "Only the team's lecturers can do this")
    return member


def my_teams(db: Session, user: User) -> list[Group]:
    ids = db.scalars(
        select(GroupMember.group_id).where(GroupMember.user_id == user.id)
    ).all()
    if not ids:
        return []
    groups = db.scalars(rules.team_query().where(Group.id.in_(ids))).all()
    return sorted(groups, key=lambda g: rules.as_utc(g.created_at), reverse=True)


# --- create / edit ---------------------------------------------------------------------------


def create_team(db: Session, creator: User, data: TeamCreate) -> Group:
    """Step 1: the team exists, as "pending", with its creator as the only member."""
    term = terms.require(db, data.term)
    code = data.code or _generate_code(db, data.name)
    if _code_exists(db, code):
        raise conflict("team_code_taken", f"The team code {code} is already used")

    group = Group(
        code=code,
        name=data.name,
        term=term.name,
        status=TeamStatus.PENDING,
        created_by_id=creator.id,
    )
    group.members.append(
        GroupMember(
            user_id=creator.id,
            user=creator,
            role=MemberRole.LECTURER,
            joined_at=rules.utcnow(),
        )
    )
    db.add(group)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise conflict(
            "team_code_taken", f"The team code {code} is already used"
        ) from exc
    return rules.find_team(db, str(group.id))


def set_project(group: Group, user: User, data: ProjectUpdate) -> None:
    """Step 2: what the team will build. Creates the project the first time, then edits it."""
    if group.projects:
        project = group.projects[0]
        project.title = data.title
        project.description = data.description
    else:
        group.projects.append(
            Project(
                created_by_id=user.id, title=data.title, description=data.description
            )
        )


def activate_team(group: Group, user: User, email_service: EmailService) -> list[Email]:
    """The last step: the team opens, and the invitations saved so far are emailed."""
    if group.status is not TeamStatus.PENDING:
        raise conflict("team_not_pending", "This team is already set up")
    if not group.projects:
        raise bad_request(
            "setup_incomplete", "Add the project's title before finishing"
        )
    group.status = TeamStatus.FORMING
    # The links were not sent while the team was pending, and only a hash is stored: issue new ones.
    invitations.ensure_leader_flag(group)
    emails = invitations.send_open(group, user, email_service)
    rules.refresh_team(group)
    return emails


def discard_team(db: Session, group: Group) -> None:
    """Throw away a team that was never finished."""
    if group.status is not TeamStatus.PENDING:
        raise conflict(
            "team_not_pending",
            "Only a team that is still being set up can be discarded",
        )
    for project in group.projects:  # projects restrict deleting their team
        db.delete(project)
    db.delete(group)


def update_team(
    db: Session,
    group: Group,
    user: User,
    member: GroupMember | None,
    data: TeamUpdate,
) -> None:
    is_lecturer = member is not None and member.role is MemberRole.LECTURER
    is_leader = member is not None and group.leader_id == user.id
    sent = data.model_fields_set
    if "name" in sent and data.name:
        if not is_lecturer:
            raise forbidden(
                "lecturer_only", "Only the team's lecturers can rename the team"
            )
        group.name = data.name
    if "term" in sent and data.term:
        if not is_lecturer:
            raise forbidden(
                "lecturer_only", "Only the team's lecturers can change the term"
            )
        if group.status is not TeamStatus.PENDING:
            raise conflict(
                "team_not_pending", "The term cannot change once the team is set up"
            )
        group.term = terms.require(db, data.term).name
    if "repo_url" in sent:
        if not (is_lecturer or is_leader):
            raise forbidden(
                "not_allowed",
                "Only the team leader or a lecturer can set the repository",
            )
        group.repo_url = data.repo_url


# --- members ---------------------------------------------------------------------------------


def remove_member(
    group: Group, actor: User, actor_member: GroupMember, target_user_id: uuid.UUID
) -> None:
    target = rules.membership(group, target_user_id)
    if target is None:
        raise not_found("That person is not in this team")

    leaving = target_user_id == actor.id
    if not leaving and actor_member.role is not MemberRole.LECTURER:
        raise forbidden("lecturer_only", "Only the team's lecturers can remove members")

    if target.role is MemberRole.LECTURER and len(rules.lecturers(group)) == 1:
        raise conflict("last_lecturer", "A team needs at least one lecturer")
    if leaving and group.leader_id == actor.id and len(rules.students(group)) > 1:
        raise conflict(
            "leader_must_transfer",
            "Transfer leadership to another member before you leave",
        )

    group.members.remove(target)
    rules.refresh_team(group)


# --- leadership ------------------------------------------------------------------------------


def start_leader_transfer(
    group: Group,
    actor: User,
    actor_member: GroupMember,
    to_user_id: uuid.UUID,
    email_service: EmailService,
) -> Email | None:
    is_leader = group.leader_id == actor.id
    if not (is_leader or actor_member.role is MemberRole.LECTURER):
        raise forbidden(
            "not_allowed", "Only the team leader or a lecturer can transfer leadership"
        )
    target = rules.membership(group, to_user_id)
    if target is None or target.role is not MemberRole.MEMBER:
        raise bad_request(
            "not_a_student_member", "Choose a student who is in this team"
        )
    if group.leader_id == to_user_id:
        raise bad_request("already_leader", "That student is already the leader")

    group.pending_leader_id = to_user_id
    if not target.user.email:
        return None
    return email_service.leader_transfer_request(
        target.user.email, from_name=actor.name, team_name=group.name
    )


def respond_to_leader_transfer(
    group: Group, user: User, *, accept: bool, email_service: EmailService
) -> list[Email]:
    if group.pending_leader_id != user.id:
        raise not_found("There is no leadership request for you in this team")
    previous = rules.membership(group, group.leader_id) if group.leader_id else None
    group.pending_leader_id = None
    if accept:
        group.leader_id = user.id
    emails: list[Email] = []
    if previous is not None and previous.user.email and previous.user_id != user.id:
        emails.append(
            email_service.leader_transfer_result(
                previous.user.email,
                member_name=user.name,
                team_name=group.name,
                accepted=accept,
            )
        )
    return emails


def cancel_leader_transfer(
    group: Group, actor: User, actor_member: GroupMember
) -> None:
    if group.pending_leader_id is None:
        raise not_found("There is no pending leadership request")
    if not (group.leader_id == actor.id or actor_member.role is MemberRole.LECTURER):
        raise forbidden(
            "not_allowed", "Only the leader or a lecturer can cancel the request"
        )
    group.pending_leader_id = None


__all__ = [
    "activate_team",
    "cancel_leader_transfer",
    "create_team",
    "discard_team",
    "my_teams",
    "remove_member",
    "require_lecturer",
    "respond_to_leader_transfer",
    "set_project",
    "start_leader_transfer",
    "team_for",
    "update_team",
]
