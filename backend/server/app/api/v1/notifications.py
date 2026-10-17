"""The signed-in person's notifications and their email preferences.

GET    /api/v1/me/notifications                  newest first, with the unread count (?limit, ?before)
POST   /api/v1/me/notifications/{id}/read        mark one read
POST   /api/v1/me/notifications/read-all         mark everything read
DELETE /api/v1/me/notifications/{id}             dismiss one
GET    /api/v1/me/notification-preferences       which emails are wanted
PUT    /api/v1/me/notification-preferences       change them

Notifications are created by the code that causes them (app/services/notifications); there is no
endpoint to create one. Answering an invitation or a leadership offer uses the existing endpoints
for those; the answered notification then closes itself.
"""

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import Account, get_onboarded_account
from app.core.errors import bad_request
from app.database.session import get_db
from app.models import Notification
from app.schemas.notification import (
    CategoryPreference,
    NotificationList,
    NotificationOut,
    NotificationPreferences,
    PreferencesUpdate,
)
from app.services import invitations, team_views
from app.services.notifications import ACTIONABLE, CATEGORIES, Category, inbox

router = APIRouter(prefix="/me", tags=["Notifications"])

Onboarded = Annotated[Account, Depends(get_onboarded_account)]
Db = Annotated[Session, Depends(get_db)]


def _out(row: Notification) -> NotificationOut:
    actionable = row.kind in {k.value for k in ACTIONABLE} and row.resolved_at is None
    return NotificationOut(
        id=row.id,
        kind=row.kind,
        title=row.title,
        body=row.body,
        link=row.link,
        data={k: str(v) for k, v in (row.data or {}).items()},
        read=row.read_at is not None,
        created_at=row.created_at,
        actions=["accept", "decline"] if actionable else [],
    )


@router.get(
    "/notifications", response_model=NotificationList, summary="My notifications"
)
def list_notifications(
    account: Onboarded,
    db: Db,
    limit: Annotated[int, Query(ge=1, le=inbox.MAX_PAGE)] = inbox.PAGE,
    before: datetime | None = None,
) -> NotificationList:
    user = account.user
    email = account.matching_email
    # Bring invitations into the list (and close answered ones) before reading it.
    mine = (
        [team_views.my_invitation(i) for i in invitations.open_for_email(db, email)]
        if email
        else []
    )
    inbox.sync_invitations(db, user, mine)
    if before is None:
        inbox.prune(db, user)
        db.commit()
    rows = inbox.list_for(db, user, limit=limit + 1, before=before)
    page = rows[:limit]
    return NotificationList(
        items=[_out(row) for row in page],
        unread_count=inbox.unread_count(db, user),
        next_before=page[-1].created_at if len(rows) > limit else None,
    )


@router.post(
    "/notifications/read-all",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Mark everything read",
)
def read_all(account: Onboarded, db: Db) -> Response:
    inbox.mark_all_read(db, account.user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/notifications/{notification_id}/read",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Mark one notification read",
)
def read_one(notification_id: uuid.UUID, account: Onboarded, db: Db) -> Response:
    inbox.mark_read(db, account.user, notification_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    "/notifications/{notification_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Dismiss a notification",
)
def dismiss(notification_id: uuid.UUID, account: Onboarded, db: Db) -> Response:
    inbox.dismiss(db, account.user, notification_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _preferences(db: Session, account: Account) -> NotificationPreferences:
    wanted = inbox.preferences(db, account.user.id)
    return NotificationPreferences(
        categories=[
            CategoryPreference(
                category=category.value,
                label=info.label,
                description=info.description,
                configurable=info.email_configurable,
                email_enabled=wanted[category],
            )
            for category, info in CATEGORIES.items()
        ]
    )


@router.get(
    "/notification-preferences",
    response_model=NotificationPreferences,
    summary="Which notification emails I want",
)
def read_preferences(account: Onboarded, db: Db) -> NotificationPreferences:
    return _preferences(db, account)


@router.put(
    "/notification-preferences",
    response_model=NotificationPreferences,
    summary="Change which notification emails I want",
)
def update_preferences(
    body: PreferencesUpdate, account: Onboarded, db: Db
) -> NotificationPreferences:
    changes: dict[Category, bool] = {}
    for name, wanted in body.email.items():
        try:
            category = Category(name)
        except ValueError:
            raise bad_request(
                "unknown_category", f"Unknown category {name!r}"
            ) from None
        if not CATEGORIES[category].email_configurable:
            raise bad_request(
                "not_configurable",
                f"{CATEGORIES[category].label} emails are always sent",
            )
        changes[category] = wanted
    inbox.set_preferences(db, account.user, changes)
    return _preferences(db, account)
