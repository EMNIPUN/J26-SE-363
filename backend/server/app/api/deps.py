"""Request dependencies for the signed-in person.

    get_account            the database user plus the verified token (creates the row on first sight)
    get_onboarded_account  same, but refuses accounts that have not finished onboarding
    require_account_role   same, and the account's role must be one of those listed

Roles come from the database (what the person chose in onboarding), except administrators, who
come from Keycloak. `app.core.security.require_roles` still works for admin-only endpoints.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated

from fastapi import BackgroundTasks, Depends
from shared.contracts import UserRole
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import forbidden
from app.core.security import CurrentUser, get_current_user
from app.database.session import get_db
from app.models import User
from app.services import accounts
from app.services.email import EmailService, get_email_service
from app.services.notifications import Notifier


@dataclass
class Account:
    user: User
    identity: CurrentUser

    @property
    def role(self) -> UserRole | None:
        return accounts.effective_role(self.identity, self.user)

    @property
    def onboarded(self) -> bool:
        return accounts.is_onboarded(self.identity, self.user)

    @property
    def matching_email(self) -> str | None:
        """The email to match invitations against; None if Keycloak has not verified it."""
        return accounts.verified_email(
            self.identity, self.user, settings.REQUIRE_VERIFIED_EMAIL
        )


def get_account(
    identity: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Account:
    return Account(user=accounts.provision(db, identity), identity=identity)


def get_onboarded_account(account: Annotated[Account, Depends(get_account)]) -> Account:
    if not account.onboarded:
        raise forbidden("onboarding_required", "Finish setting up your account first")
    return account


def require_account_role(*roles: UserRole) -> Callable[[Account], Account]:
    def check(account: Annotated[Account, Depends(get_onboarded_account)]) -> Account:
        if account.role not in roles:
            raise forbidden("role_not_allowed", "Your account type cannot do this")
        return account

    return check


def get_notifier(
    db: Annotated[Session, Depends(get_db)],
    mailer: Annotated[EmailService, Depends(get_email_service)],
    background: BackgroundTasks,
) -> Notifier:
    """The one way a request tells people about what it did (in the app and by email)."""
    return Notifier(db, mailer, background)


Notify = Annotated[Notifier, Depends(get_notifier)]
