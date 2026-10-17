import re
import uuid
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)
from shared.contracts import UserRole

# GitHub logins: 1 to 39 letters, digits or single hyphens, not starting or ending with a hyphen.
GITHUB_LOGIN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9]|-(?=[A-Za-z0-9])){0,38}$")

Text255 = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)
]
OptionalText = Annotated[
    str | None, StringConstraints(strip_whitespace=True, max_length=255)
]

AccountType = Literal["student", "lecturer"]


def _blank_to_none(value: str | None) -> str | None:
    return value or None


class ProfileFields(BaseModel):
    """Details kept on the account. Which ones apply depends on the role."""

    institution: OptionalText = None
    # Students
    student_number: Annotated[
        str | None, StringConstraints(strip_whitespace=True, max_length=32)
    ] = None
    github_username: Annotated[
        str | None, StringConstraints(strip_whitespace=True, max_length=39)
    ] = None
    # Lecturers
    department: OptionalText = None
    title: Annotated[
        str | None, StringConstraints(strip_whitespace=True, max_length=128)
    ] = None

    # Field validators (not a model validator), so "which fields were sent" stays accurate for
    # partial updates.
    @field_validator(
        "institution", "student_number", "department", "title", mode="after"
    )
    @classmethod
    def _blank_is_none(cls, value: str | None) -> str | None:
        return _blank_to_none(value)

    @field_validator("github_username", mode="after")
    @classmethod
    def _github_login(cls, value: str | None) -> str | None:
        value = _blank_to_none(value)
        if value is not None and not GITHUB_LOGIN.match(value):
            raise ValueError("Not a valid GitHub username")
        return value


class OnboardingRequest(ProfileFields):
    account_type: AccountType
    display_name: Text255
    accept_terms: bool
    # The version of the terms the person was shown; must be the current one.
    consent_version: str

    @model_validator(mode="after")
    def _check(self):
        if not self.accept_terms:
            raise ValueError("The terms must be accepted")
        if self.account_type == "student" and not self.github_username:
            raise ValueError("github_username is required for students")
        return self


class ProfileUpdate(ProfileFields):
    display_name: Text255 | None = None


class ProfileOut(BaseModel):
    institution: str | None
    student_number: str | None
    github_username: str | None
    department: str | None
    title: str | None


class AccountOut(BaseModel):
    id: uuid.UUID
    name: str
    email: str | None
    # Can this account be matched to invitations (Keycloak verified the address)?
    email_verified: bool
    # None until onboarding is finished. Administrators always come from Keycloak.
    role: UserRole | None
    onboarding_completed: bool
    profile: ProfileOut
    consent_version: str | None
    current_consent_version: str = Field(
        description="Terms version the next sign-up must accept"
    )
