"""Invitations, from the invited person's side.

GET  /api/v1/me/invitations               invitations waiting for me
GET  /api/v1/invitations/sent             invitations I sent that nobody has answered (lecturers)
POST /api/v1/invitations/lookup           what the link in an invitation email is about
POST /api/v1/invitations/{id}/accept      join the team
POST /api/v1/invitations/{id}/decline     say no

They are matched to the account's verified email, so only the person they were sent to can
answer, even if the link is forwarded. Lecturers invite from the team (see teams.py).
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Response, status
from shared.contracts import UserRole
from sqlalchemy.orm import Session

from app.api.deps import Account, get_onboarded_account, require_account_role
from app.database.session import get_db
from app.schemas.team import InvitationLookup, MyInvitation, SentInvitation, TeamSummary
from app.services import invitations, team_views
from app.services.email import EmailService, get_email_service

router = APIRouter(tags=["Invitations"])

Onboarded = Annotated[Account, Depends(get_onboarded_account)]
Lecturer = Annotated[Account, Depends(require_account_role(UserRole.LECTURER))]
Db = Annotated[Session, Depends(get_db)]
Mailer = Annotated[EmailService, Depends(get_email_service)]


@router.get(
    "/me/invitations", response_model=list[MyInvitation], summary="My invitations"
)
def my_invitations(account: Onboarded, db: Db) -> list[MyInvitation]:
    email = account.matching_email
    if email is None:
        return []
    return [team_views.my_invitation(i) for i in invitations.open_for_email(db, email)]


@router.get(
    "/invitations/sent",
    response_model=list[SentInvitation],
    summary="Invitations I sent that are waiting for an answer",
)
def sent_invitations(account: Lecturer, db: Db) -> list[SentInvitation]:
    return [
        team_views.sent_invitation(i) for i in invitations.sent_by(db, account.user)
    ]


@router.post(
    "/invitations/lookup",
    response_model=MyInvitation,
    summary="Open an invitation link",
)
def lookup_invitation(
    body: InvitationLookup, account: Onboarded, db: Db
) -> MyInvitation:
    invitation = invitations.lookup_by_token(db, body.token, account.matching_email)
    return team_views.my_invitation(invitation)


@router.post(
    "/invitations/{invitation_id}/accept",
    response_model=TeamSummary,
    summary="Accept an invitation",
)
def accept_invitation(
    invitation_id: uuid.UUID,
    account: Onboarded,
    db: Db,
    mailer: Mailer,
    background: BackgroundTasks,
) -> TeamSummary:
    group, emails = invitations.respond(
        db,
        account.user,
        account.role,
        account.matching_email,
        invitation_id,
        accept=True,
        email_service=mailer,
    )
    for message in emails:
        background.add_task(mailer.deliver, message)
    return team_views.summary(group, account.user, account.role)


@router.post(
    "/invitations/{invitation_id}/decline",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Decline an invitation",
)
def decline_invitation(
    invitation_id: uuid.UUID,
    account: Onboarded,
    db: Db,
    mailer: Mailer,
    background: BackgroundTasks,
) -> Response:
    _, emails = invitations.respond(
        db,
        account.user,
        account.role,
        account.matching_email,
        invitation_id,
        accept=False,
        email_service=mailer,
    )
    for message in emails:
        background.add_task(mailer.deliver, message)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
