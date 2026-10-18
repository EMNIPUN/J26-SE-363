"""Profile pictures.

A person's picture is either one they uploaded (kept in user_avatars, at most 512 KB, JPEG, PNG or
WebP, checked by its first bytes and not by what the client claims) or the one their sign-in
provider gave (an address in users.picture_url). An upload wins. The web app shrinks pictures to
256 px before sending, so they are small.

Who can see a picture: its owner, administrators and people who share a team with them.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, aliased

from app.core.errors import ApiError, bad_request, not_found
from app.models import GroupMember, User, UserAvatar

MAX_BYTES = 512 * 1024
MAX_ADDRESS = 1024


def detect_type(data: bytes) -> str | None:
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if len(data) > 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def set_avatar(db: Session, user: User, data: bytes) -> None:
    if not data:
        raise bad_request("empty_image", "No picture was sent")
    if len(data) > MAX_BYTES:
        raise too_large()
    kind = detect_type(data)
    if kind is None:
        raise bad_request("unsupported_image", "Use a JPEG, PNG or WebP picture")
    row = db.get(UserAvatar, user.id)
    if row is None:
        db.add(UserAvatar(user_id=user.id, content_type=kind, data=data))
    else:
        row.content_type, row.data = kind, data
    user.avatar_updated_at = datetime.now(UTC)
    db.commit()


def remove_avatar(db: Session, user: User) -> None:
    row = db.get(UserAvatar, user.id)
    if row is not None:
        db.delete(row)
    user.avatar_updated_at = None
    db.commit()


def too_large() -> ApiError:
    return ApiError(413, "image_too_large", "The picture is too large (500 KB at most)")


def clean_address(value: str | None) -> str | None:
    """A provider's picture address, if it is a plain web address of a sensible length."""
    if not value or len(value) > MAX_ADDRESS:
        return None
    return value if value.lower().startswith(("https://", "http://")) else None


def picture_of(user: User) -> str | None:
    """What clients show: the API path of an uploaded picture, else the provider's address."""
    if user.avatar_updated_at is not None:
        stamp = user.avatar_updated_at
        stamp = stamp if stamp.tzinfo else stamp.replace(tzinfo=UTC)
        return f"/users/{user.id}/avatar?v={int(stamp.timestamp())}"
    return user.picture_url


def shares_team(db: Session, one: uuid.UUID, other: uuid.UUID) -> bool:
    mine, theirs = aliased(GroupMember), aliased(GroupMember)
    return (
        db.scalar(
            select(mine.id)
            .join(theirs, theirs.group_id == mine.group_id)
            .where(mine.user_id == one, theirs.user_id == other)
            .limit(1)
        )
        is not None
    )


def visible_avatar(
    db: Session, viewer: User, owner_id: uuid.UUID, *, is_admin: bool
) -> UserAvatar:
    """The picture, or "not found" (also when it exists but this person may not see it)."""
    allowed = viewer.id == owner_id or is_admin or shares_team(db, viewer.id, owner_id)
    row = db.get(UserAvatar, owner_id) if allowed else None
    if row is None:
        raise not_found("No picture")
    return row
