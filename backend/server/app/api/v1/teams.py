"""Teams: the groups a lecturer creates and students join.

GET    /api/v1/me/teams                               my teams (the home page)
POST   /api/v1/teams                                  step 1: create a pending team (lecturers)
PUT    /api/v1/teams/{team}/project                   step 2: the project's title and description
POST   /api/v1/teams/{team}/activate                  last step: open the team and send the invitations
DELETE /api/v1/teams/{team}                           discard a team that is still pending
GET    /api/v1/teams/{team}                           team, members and, for lecturers, invitations
PATCH  /api/v1/teams/{team}                           rename (lecturers), set repository (leader too)
POST   /api/v1/teams/{team}/invitations               invite more students or lecturers
POST   /api/v1/teams/{team}/invitations/{id}/resend   send an invitation again with a fresh link
DELETE /api/v1/teams/{team}/invitations/{id}          withdraw an invitation
DELETE /api/v1/teams/{team}/members/{user}            remove a member, or leave the team
POST   /api/v1/teams/{team}/leader-transfer           offer leadership to a student member
POST   /api/v1/teams/{team}/leader-transfer/accept    the offered student accepts
POST   /api/v1/teams/{team}/leader-transfer/decline   ... or declines
DELETE /api/v1/teams/{team}/leader-transfer           withdraw the offer

`{team}` is the team's id or its code (e.g. J26-SE-363). Teams are only visible to their members:
anyone else gets 404.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Response, status
from shared.contracts import UserRole
from sqlalchemy.orm import Session

from app.api.deps import Account, get_onboarded_account, require_account_role
from app.database.session import get_db
from app.schemas.team import (
    InvitationOut,
    InviteList,
    InviteSummary,
    LeaderTransferRequest,
    ProjectUpdate,
    TeamCreate,
    TeamDetail,
    TeamSummary,
    TeamUpdate,
)
from app.services import invitations, team_views, teams
from app.services.email import EmailService, get_email_service

router = APIRouter(tags=["Teams"])

Onboarded = Annotated[Account, Depends(get_onboarded_account)]
Lecturer = Annotated[Account, Depends(require_account_role(UserRole.LECTURER))]
Db = Annotated[Session, Depends(get_db)]
Mailer = Annotated[EmailService, Depends(get_email_service)]


def _is_admin(account: Account) -> bool:
    return account.role is UserRole.ADMIN


def _detail(group, account: Account) -> TeamDetail:
    return team_views.detail(group, account.user, account.role)


@router.get("/me/teams", response_model=list[TeamSummary], summary="My teams")
def list_my_teams(account: Onboarded, db: Db) -> list[TeamSummary]:
    return [
        team_views.summary(g, account.user, account.role)
        for g in teams.my_teams(db, account.user)
    ]


@router.post(
    "/teams",
    response_model=TeamDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Create a team (step 1)",
)
def create_team(body: TeamCreate, account: Lecturer, db: Db) -> TeamDetail:
    return _detail(teams.create_team(db, account.user, body), account)


@router.get("/teams/{team}", response_model=TeamDetail, summary="A team")
def read_team(team: str, account: Onboarded, db: Db) -> TeamDetail:
    group, _ = teams.team_for(db, team, account.user, is_admin=_is_admin(account))
    return _detail(group, account)


@router.patch("/teams/{team}", response_model=TeamDetail, summary="Edit a team")
def edit_team(team: str, body: TeamUpdate, account: Onboarded, db: Db) -> TeamDetail:
    group, member = teams.team_for(db, team, account.user)
    teams.update_team(db, group, account.user, member, body)
    db.commit()
    return _detail(group, account)


@router.put(
    "/teams/{team}/project",
    response_model=TeamDetail,
    summary="Set the project (step 2)",
)
def set_project(
    team: str, body: ProjectUpdate, account: Lecturer, db: Db
) -> TeamDetail:
    group, member = teams.team_for(db, team, account.user)
    teams.require_lecturer(member)
    teams.set_project(group, account.user, body)
    db.commit()
    return _detail(group, account)


@router.post(
    "/teams/{team}/activate",
    response_model=TeamDetail,
    summary="Finish setting up a team",
)
def activate_team(
    team: str,
    account: Lecturer,
    db: Db,
    mailer: Mailer,
    background: BackgroundTasks,
) -> TeamDetail:
    group, member = teams.team_for(db, team, account.user)
    teams.require_lecturer(member)
    for message in teams.activate_team(group, account.user, mailer):
        background.add_task(mailer.deliver, message)
    db.commit()
    return _detail(group, account)


@router.delete(
    "/teams/{team}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Discard a team that is still being set up",
)
def discard_team(team: str, account: Lecturer, db: Db) -> Response:
    group, member = teams.team_for(db, team, account.user)
    teams.require_lecturer(member)
    teams.discard_team(db, group)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- invitations (lecturer side) -------------------------------------------------------------


@router.post(
    "/teams/{team}/invitations", response_model=InviteSummary, summary="Invite people"
)
def invite_people(
    team: str,
    body: InviteList,
    account: Lecturer,
    db: Db,
    mailer: Mailer,
    background: BackgroundTasks,
) -> InviteSummary:
    group, member = teams.team_for(db, team, account.user)
    teams.require_lecturer(member)
    invited = invitations.invite(
        db,
        group,
        account.user,
        mailer,
        students=body.students,
        lecturers=body.lecturers,
        leader_email=body.leader_email,
    )
    db.commit()
    for message in invited.emails:
        background.add_task(mailer.deliver, message)
    return InviteSummary(results=invited.results)


@router.post(
    "/teams/{team}/invitations/{invitation_id}/resend",
    response_model=InvitationOut,
    summary="Send an invitation again",
)
def resend_invitation(
    team: str,
    invitation_id: uuid.UUID,
    account: Lecturer,
    db: Db,
    mailer: Mailer,
    background: BackgroundTasks,
) -> InvitationOut:
    group, member = teams.team_for(db, team, account.user)
    teams.require_lecturer(member)
    message = invitations.resend(group, invitation_id, account.user, mailer)
    db.commit()
    background.add_task(mailer.deliver, message)
    return team_views.invitation_out(
        next(i for i in group.invitations if i.id == invitation_id)
    )


@router.delete(
    "/teams/{team}/invitations/{invitation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Withdraw an invitation",
)
def withdraw_invitation(
    team: str, invitation_id: uuid.UUID, account: Lecturer, db: Db
) -> Response:
    group, member = teams.team_for(db, team, account.user)
    teams.require_lecturer(member)
    invitations.revoke(group, invitation_id)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- members ---------------------------------------------------------------------------------


@router.delete(
    "/teams/{team}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a member or leave",
)
def remove_member(
    team: str, user_id: uuid.UUID, account: Onboarded, db: Db
) -> Response:
    group, member = teams.team_for(db, team, account.user)
    teams.remove_member(group, account.user, member, user_id)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- leadership ------------------------------------------------------------------------------


@router.post(
    "/teams/{team}/leader-transfer",
    response_model=TeamDetail,
    summary="Offer leadership",
)
def offer_leadership(
    team: str,
    body: LeaderTransferRequest,
    account: Onboarded,
    db: Db,
    mailer: Mailer,
    background: BackgroundTasks,
) -> TeamDetail:
    group, member = teams.team_for(db, team, account.user)
    message = teams.start_leader_transfer(
        group, account.user, member, body.to_user_id, mailer
    )
    db.commit()
    if message is not None:
        background.add_task(mailer.deliver, message)
    return _detail(group, account)


@router.post(
    "/teams/{team}/leader-transfer/accept",
    response_model=TeamDetail,
    summary="Accept leadership",
)
def accept_leadership(
    team: str, account: Onboarded, db: Db, mailer: Mailer, background: BackgroundTasks
) -> TeamDetail:
    group, _ = teams.team_for(db, team, account.user)
    for message in teams.respond_to_leader_transfer(
        group, account.user, accept=True, email_service=mailer
    ):
        background.add_task(mailer.deliver, message)
    db.commit()
    return _detail(group, account)


@router.post(
    "/teams/{team}/leader-transfer/decline",
    response_model=TeamDetail,
    summary="Decline leadership",
)
def decline_leadership(
    team: str, account: Onboarded, db: Db, mailer: Mailer, background: BackgroundTasks
) -> TeamDetail:
    group, _ = teams.team_for(db, team, account.user)
    for message in teams.respond_to_leader_transfer(
        group, account.user, accept=False, email_service=mailer
    ):
        background.add_task(mailer.deliver, message)
    db.commit()
    return _detail(group, account)


@router.delete(
    "/teams/{team}/leader-transfer",
    response_model=TeamDetail,
    summary="Withdraw the leadership offer",
)
def withdraw_leadership_offer(team: str, account: Onboarded, db: Db) -> TeamDetail:
    group, member = teams.team_for(db, team, account.user)
    teams.cancel_leader_transfer(group, account.user, member)
    db.commit()
    return _detail(group, account)
