"""What can be notified, and how each kind behaves. The one list to read before adding a kind."""

from dataclasses import dataclass
from enum import Enum


class Category(str, Enum):
    INVITATIONS = "invitations"
    LEADERSHIP = "leadership"
    ACTIVITY = "activity"


@dataclass(frozen=True)
class CategoryInfo:
    label: str
    description: str
    # Can the person switch the email off? Invitations cannot: without the email link a person
    # who has no account yet would never learn they were invited.
    email_configurable: bool


CATEGORIES: dict[Category, CategoryInfo] = {
    Category.INVITATIONS: CategoryInfo(
        "Invitations", "When someone invites you to a team.", email_configurable=False
    ),
    Category.LEADERSHIP: CategoryInfo(
        "Team leadership",
        "Offers to lead a team, and answers to the offers you made.",
        email_configurable=True,
    ),
    Category.ACTIVITY: CategoryInfo(
        "Team activity",
        "Answers to your invitations, and people leaving or being removed.",
        email_configurable=True,
    ),
}


class Kind(str, Enum):
    TEAM_INVITATION = "team_invitation"
    INVITATION_ANSWERED = "invitation_answered"
    LEADERSHIP_OFFERED = "leadership_offered"
    LEADERSHIP_ANSWERED = "leadership_answered"
    LEADERSHIP_WITHDRAWN = "leadership_withdrawn"
    MEMBER_LEFT = "member_left"
    MEMBER_REMOVED = "member_removed"


CATEGORY_OF: dict[Kind, Category] = {
    Kind.TEAM_INVITATION: Category.INVITATIONS,
    Kind.INVITATION_ANSWERED: Category.ACTIVITY,
    Kind.LEADERSHIP_OFFERED: Category.LEADERSHIP,
    Kind.LEADERSHIP_ANSWERED: Category.LEADERSHIP,
    Kind.LEADERSHIP_WITHDRAWN: Category.LEADERSHIP,
    Kind.MEMBER_LEFT: Category.ACTIVITY,
    Kind.MEMBER_REMOVED: Category.ACTIVITY,
}

# Kinds the person answers right from the notification (Accept / Decline) while they are open.
ACTIONABLE: frozenset[Kind] = frozenset({Kind.TEAM_INVITATION, Kind.LEADERSHIP_OFFERED})
