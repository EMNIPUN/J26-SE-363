import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

Action = Literal["accept", "decline"]


class NotificationOut(BaseModel):
    id: uuid.UUID
    kind: str
    title: str
    body: str | None
    # A path in the web app, where the notification leads.
    link: str | None
    # What the web app needs to act on it: "team_code", and "invitation_id" for invitations.
    data: dict[str, str]
    read: bool
    created_at: datetime
    # Buttons to offer right in the notification; empty once it was answered anywhere.
    actions: list[Action]


class NotificationList(BaseModel):
    items: list[NotificationOut]
    unread_count: int
    # Pass as `before` to get the next, older page; empty when there are no more.
    next_before: datetime | None


class CategoryPreference(BaseModel):
    category: str
    label: str
    description: str
    # False for notifications that are always emailed (invitations).
    configurable: bool
    email_enabled: bool


class NotificationPreferences(BaseModel):
    categories: list[CategoryPreference]


class PreferencesUpdate(BaseModel):
    """Category name -> wants email. Unknown or non-configurable categories are refused."""

    email: dict[str, bool]
