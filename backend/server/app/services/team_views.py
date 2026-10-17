"""Turns teams and invitations into the API's response models."""

from shared.contracts import UserRole

from app.models import Group, GroupMember, MemberRole, TeamInvitation, User
from app.schemas.team import (
    InvitationOut,
    MemberOut,
    MyInvitation,
    PersonOut,
    ProjectOut,
    TeamDetail,
    TeamRole,
    TeamSummary,
)
from app.services import team_rules as rules


def person(user: User) -> PersonOut:
    return PersonOut(user_id=user.id, name=user.name)


def _find_user(group: Group, user_id) -> User | None:
    member = rules.membership(group, user_id) if user_id else None
    return member.user if member else None


def role_of(group: Group, member: GroupMember) -> TeamRole:
    if member.role is MemberRole.LECTURER:
        return "lecturer"
    return "leader" if group.leader_id == member.user_id else "member"


def can_see_everything(viewer_role: UserRole | None) -> bool:
    return viewer_role in (UserRole.LECTURER, UserRole.ADMIN)


def summary(group: Group, viewer: User, viewer_role: UserRole | None) -> TeamSummary:
    me = rules.membership(group, viewer.id)
    leader = _find_user(group, group.leader_id)
    project = group.projects[0] if group.projects else None
    staff = (
        me is not None and me.role is MemberRole.LECTURER
    ) or viewer_role is UserRole.ADMIN
    return TeamSummary(
        id=group.id,
        code=group.code,
        name=group.name,
        term=group.term,
        status=group.status.value,
        project=ProjectOut(
            id=project.id, title=project.title, description=project.description
        )
        if project
        else None,
        my_role=role_of(group, me) if me else "lecturer",
        leader=person(leader) if leader else None,
        student_count=len(rules.students(group)),
        lecturer_count=len(rules.lecturers(group)),
        pending_invitations=sum(1 for i in group.invitations if rules.is_open(i))
        if staff
        else None,
        repo_url=group.repo_url,
    )


def detail(group: Group, viewer: User, viewer_role: UserRole | None) -> TeamDetail:
    base = summary(group, viewer, viewer_role)
    me = rules.membership(group, viewer.id)
    staff = (
        me is not None and me.role is MemberRole.LECTURER
    ) or viewer_role is UserRole.ADMIN

    members = [
        MemberOut(
            user_id=m.user_id,
            name=m.user.name,
            role=role_of(group, m),
            email=m.user.email if staff else None,
            github_username=m.user.github_username,
            joined_at=rules.as_utc(m.joined_at),
        )
        for m in sorted(
            group.members,
            key=lambda m: (m.role is not MemberRole.LECTURER, m.user.name.lower()),
        )
    ]
    invitations = (
        [
            invitation_out(i)
            for i in sorted(group.invitations, key=lambda i: i.created_at, reverse=True)
        ]
        if staff
        else []
    )
    pending = _find_user(group, group.pending_leader_id)
    return TeamDetail(
        **base.model_dump(),
        members=members,
        invitations=invitations,
        pending_leader=person(pending) if pending else None,
    )


def invitation_out(invitation: TeamInvitation) -> InvitationOut:
    return InvitationOut(
        id=invitation.id,
        email=invitation.email,
        role=invitation.role.value,
        as_leader=invitation.as_leader,
        status=rules.invitation_state(invitation),
        expires_at=rules.as_utc(invitation.expires_at),
        responded_at=rules.as_utc(invitation.responded_at),
    )


def my_invitation(invitation: TeamInvitation) -> MyInvitation:
    group = invitation.group
    inviter = None
    if invitation.invited_by_id:
        member = rules.membership(group, invitation.invited_by_id)
        inviter = member.user.name if member else None
    project = group.projects[0] if group.projects else None
    return MyInvitation(
        id=invitation.id,
        role=invitation.role.value,
        as_leader=invitation.as_leader,
        expires_at=rules.as_utc(invitation.expires_at),
        invited_by=inviter,
        team_id=group.id,
        team_code=group.code,
        team_name=group.name,
        term=group.term,
        project_title=project.title if project else None,
    )
