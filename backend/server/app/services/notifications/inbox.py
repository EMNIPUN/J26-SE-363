"""A person's notifications: listing, reading, closing, and their email preferences."""

import uuid
from datetime import timedelta

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.core.errors import not_found
from app.models import Notification, NotificationPreference, User
from app.schemas.team import MyInvitation
from app.services import team_rules as rules
from app.services.notifications.catalog import CATEGORIES, Category, Kind

PAGE = 30
MAX_PAGE = 50
RETENTION_DAYS = 90


def prune(db: Session, user: User) -> None:
    """Notifications are a recent-events view, not an archive: drop the old ones."""
    cutoff = rules.utcnow() - timedelta(days=RETENTION_DAYS)
    db.execute(
        delete(Notification).where(
            Notification.user_id == user.id, Notification.created_at < cutoff
        )
    )


def list_for(
    db: Session, user: User, *, limit: int = PAGE, before=None
) -> list[Notification]:
    query = select(Notification).where(Notification.user_id == user.id)
    if before is not None:
        query = query.where(Notification.created_at < before)
    query = query.order_by(Notification.created_at.desc(), Notification.id.desc())
    return list(db.scalars(query.limit(min(limit, MAX_PAGE))))


def unread_count(db: Session, user: User) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(Notification)
            .where(Notification.user_id == user.id, Notification.read_at.is_(None))
        )
        or 0
    )


def _own(db: Session, user: User, notification_id: uuid.UUID) -> Notification:
    row = db.get(Notification, notification_id)
    if (
        row is None or row.user_id != user.id
    ):  # someone else's looks the same as missing
        raise not_found("Notification not found")
    return row


def mark_read(db: Session, user: User, notification_id: uuid.UUID) -> None:
    row = _own(db, user, notification_id)
    if row.read_at is None:
        row.read_at = rules.utcnow()
    db.commit()


def mark_all_read(db: Session, user: User) -> None:
    db.execute(
        update(Notification)
        .where(Notification.user_id == user.id, Notification.read_at.is_(None))
        .values(read_at=rules.utcnow())
    )
    db.commit()


def dismiss(db: Session, user: User, notification_id: uuid.UUID) -> None:
    db.delete(_own(db, user, notification_id))
    db.commit()


def resolve(db: Session, user_id: uuid.UUID, kind: Kind, ref: str) -> None:
    """The thing it asked about was answered (anywhere): close it and stop offering its buttons.
    Does not commit."""
    now = rules.utcnow()
    for row in db.scalars(
        select(Notification).where(
            Notification.user_id == user_id,
            Notification.kind == kind.value,
            Notification.ref == ref,
            Notification.resolved_at.is_(None),
        )
    ):
        row.resolved_at = now
        row.read_at = row.read_at or now


def sync_invitations(
    db: Session, user: User, open_invitations: list[MyInvitation]
) -> None:
    """Show each invitation the person can answer as a notification, and close the ones that
    were answered, withdrawn or have expired.

    This runs when the notifications are read, not when the invitation is sent: an invitation
    can be sent before the person has an account, and only an account whose email Keycloak has
    verified may see it. Commits if anything changed."""
    rows = {
        row.ref: row
        for row in db.scalars(
            select(Notification).where(
                Notification.user_id == user.id,
                Notification.kind == Kind.TEAM_INVITATION.value,
            )
        )
    }
    changed = False
    still_open = set()
    for invitation in open_invitations:
        ref = str(invitation.id)
        still_open.add(ref)
        if ref in rows:
            continue
        who = invitation.invited_by or "Someone"
        role = "a lecturer" if invitation.role == "lecturer" else "a team member"
        db.add(
            Notification(
                user_id=user.id,
                kind=Kind.TEAM_INVITATION.value,
                title=f"{who} invited you to {invitation.team_name}",
                body=f"As {role}.",
                link="/invitations",
                data={"invitation_id": ref, "team_code": invitation.team_code},
                ref=ref,
            )
        )
        changed = True
    now = rules.utcnow()
    for ref, row in rows.items():
        if ref not in still_open and row.resolved_at is None:
            row.resolved_at = now
            row.read_at = row.read_at or now
            changed = True
    if changed:
        db.commit()


# --- email preferences ---------------------------------------------------------------------------


def preferences(db: Session, user_id: uuid.UUID) -> dict[Category, bool]:
    """Is email wanted for each category? On unless the person turned it off."""
    chosen = {
        row.category: row.email_enabled
        for row in db.scalars(
            select(NotificationPreference).where(
                NotificationPreference.user_id == user_id
            )
        )
    }
    return {
        category: True
        if not info.email_configurable
        else chosen.get(category.value, True)
        for category, info in CATEGORIES.items()
    }


def set_preferences(db: Session, user: User, changes: dict[Category, bool]) -> None:
    for category, wanted in changes.items():
        if not CATEGORIES[category].email_configurable:
            continue
        row = db.scalar(
            select(NotificationPreference).where(
                NotificationPreference.user_id == user.id,
                NotificationPreference.category == category.value,
            )
        )
        if row is None:
            db.add(
                NotificationPreference(
                    user_id=user.id, category=category.value, email_enabled=wanted
                )
            )
        else:
            row.email_enabled = wanted
    db.commit()
