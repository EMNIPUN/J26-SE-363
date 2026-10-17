"""Accounts: the database row behind a Keycloak login, and what a person tells us about themselves.

Authentication is Keycloak's job. This module owns the `users` row, which is created on the first
authenticated request, and the onboarding step where a person chooses to be a student or a
lecturer. Nobody approves that choice: the role only controls which actions the person may take
(see app/api/deps.py). Administrators are the exception; they get their role from Keycloak.
"""

from datetime import UTC, datetime

from shared.contracts import UserRole
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ApiError, conflict, forbidden
from app.core.security import CurrentUser
from app.models import User
from app.schemas.account import OnboardingRequest, ProfileFields, ProfileUpdate

# Bump when the terms or the data-processing consent change; everyone then has to accept again.
CONSENT_VERSION = "2026-10"

STUDENT_FIELDS = ("student_number", "github_username")
LECTURER_FIELDS = ("department", "title")


def normalise_email(email: str | None) -> str | None:
    return email.strip().lower() if email and email.strip() else None


def _initial_name(identity: CurrentUser) -> str:
    if identity.name and identity.name.strip():
        return identity.name.strip()
    if identity.username:
        return identity.username
    if identity.email:
        return identity.email.split("@")[0]
    return "New user"


def provision(db: Session, identity: CurrentUser) -> User:
    """The user row for this Keycloak login; created on first sight, email kept current."""
    user = db.scalar(select(User).where(User.keycloak_sub == identity.user_id))
    if user is None:
        user = User(
            keycloak_sub=identity.user_id,
            name=_initial_name(identity),
            email=normalise_email(identity.email),
        )
        db.add(user)
        try:
            db.commit()
        except IntegrityError:
            # Two first requests raced; the other one created the row.
            db.rollback()
            user = db.scalar(select(User).where(User.keycloak_sub == identity.user_id))
            if user is None:
                raise
    else:
        email = normalise_email(identity.email)
        if email and email != user.email:
            user.email = email
            db.commit()
    return user


def effective_role(identity: CurrentUser, user: User) -> UserRole | None:
    """Administrators come from Keycloak; everyone else has the role they chose in onboarding."""
    if identity.role is UserRole.ADMIN:
        return UserRole.ADMIN
    return user.role


def is_onboarded(identity: CurrentUser, user: User) -> bool:
    return identity.role is UserRole.ADMIN or user.is_onboarded


def verified_email(
    identity: CurrentUser, user: User, require_verified: bool
) -> str | None:
    """The address invitations may be matched against, or None when it cannot be trusted."""
    if require_verified and not identity.email_verified:
        return None
    return normalise_email(identity.email) or user.email


def _apply_profile(user: User, fields: ProfileFields, role: UserRole) -> None:
    user.institution = fields.institution
    if role is UserRole.STUDENT:
        user.student_number = fields.student_number
        user.github_username = (
            fields.github_username.lower() if fields.github_username else None
        )
        user.department = None
        user.title = None
    elif role is UserRole.LECTURER:
        user.department = fields.department
        user.title = fields.title
        user.student_number = None
        user.github_username = None


def _ensure_unique(
    db: Session, user: User, fields: ProfileFields, role: UserRole
) -> None:
    """Friendly conflict errors; the unique constraints remain the real guard."""
    if role is not UserRole.STUDENT:
        return
    checks = (
        (
            "student_number",
            fields.student_number,
            "student_number_taken",
            "That student number is already registered",
        ),
        (
            "github_username",
            fields.github_username.lower() if fields.github_username else None,
            "github_username_taken",
            "That GitHub username is already linked to another account",
        ),
    )
    for column, value, code, message in checks:
        if value is None:
            continue
        owner = db.scalar(
            select(User).where(getattr(User, column) == value, User.id != user.id)
        )
        if owner is not None:
            raise conflict(code, message)


def complete_onboarding(
    db: Session, user: User, identity: CurrentUser, request: OnboardingRequest
) -> User:
    if identity.role is UserRole.ADMIN or user.is_onboarded:
        raise conflict("already_onboarded", "This account is already set up")
    if request.consent_version != CONSENT_VERSION:
        raise ApiError(
            409,
            "consent_outdated",
            "The terms changed. Reload the page and accept again.",
        )

    role = UserRole(request.account_type)
    _ensure_unique(db, user, request, role)
    user.role = role
    user.name = request.display_name
    _apply_profile(user, request, role)
    user.consent_version = CONSENT_VERSION
    now = datetime.now(UTC)
    user.consent_at = now
    user.onboarding_completed_at = now
    _commit(db)
    return user


def update_profile(
    db: Session, user: User, identity: CurrentUser, update: ProfileUpdate
) -> User:
    role = effective_role(identity, user)
    if role is None:
        raise forbidden("onboarding_required", "Finish setting up your account first")
    if role is UserRole.ADMIN:
        raise forbidden(
            "profile_managed_by_keycloak",
            "Administrator profiles are managed in Keycloak",
        )

    # Only the fields that were sent change; the role-specific ones only for that role.
    sent = update.model_fields_set
    merged = ProfileFields(
        institution=update.institution if "institution" in sent else user.institution,
        student_number=update.student_number
        if "student_number" in sent
        else user.student_number,
        github_username=update.github_username
        if "github_username" in sent
        else user.github_username,
        department=update.department if "department" in sent else user.department,
        title=update.title if "title" in sent else user.title,
    )
    if role is UserRole.STUDENT and not merged.github_username:
        raise conflict(
            "github_username_required", "A GitHub username is required for students"
        )
    _ensure_unique(db, user, merged, role)
    _apply_profile(user, merged, role)
    if update.display_name:
        user.name = update.display_name
    _commit(db)
    return user


def _commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        text = str(exc.orig)
        if "github_username" in text:
            raise conflict(
                "github_username_taken",
                "That GitHub username is already linked to another account",
            ) from exc
        if "student_number" in text:
            raise conflict(
                "student_number_taken", "That student number is already registered"
            ) from exc
        raise
