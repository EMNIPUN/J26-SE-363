import re
import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.schemas.account import Text255

EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
TEAM_CODE = re.compile(r"^[A-Z0-9][A-Z0-9._-]{1,62}$")
REPO_URL = re.compile(r"^https://[^\s/]+/\S+$")

MAX_STUDENTS = 60
MAX_LECTURERS = 10

TeamRole = Literal["lecturer", "leader", "member"]
InvitationState = Literal["pending", "accepted", "declined", "revoked", "expired"]


def clean_email(value: str) -> str:
    email = value.strip().lower()
    if len(email) > 320 or not EMAIL.match(email):
        raise ValueError(f"{value!r} is not a valid email address")
    return email


def clean_emails(values: list[str]) -> list[str]:
    emails = [clean_email(value) for value in values]
    if len(set(emails)) != len(emails):
        raise ValueError("The same email address appears twice")
    return emails


# --- requests --------------------------------------------------------------------------------


class InviteList(BaseModel):
    """Who to invite. Students come first on purpose: the first one is the default leader."""

    students: list[str] = Field(default_factory=list, max_length=MAX_STUDENTS)
    lecturers: list[str] = Field(default_factory=list, max_length=MAX_LECTURERS)
    # One of `students`; becomes the team leader when they accept.
    leader_email: str | None = None

    @field_validator("students", "lecturers", mode="after")
    @classmethod
    def _emails(cls, value: list[str]) -> list[str]:
        return clean_emails(value)

    @field_validator("leader_email", mode="after")
    @classmethod
    def _leader_email(cls, value: str | None) -> str | None:
        return clean_email(value) if value else None

    @model_validator(mode="after")
    def _check(self):
        if set(self.students) & set(self.lecturers):
            raise ValueError("A person cannot be invited as both student and lecturer")
        if self.leader_email and self.leader_email not in self.students:
            raise ValueError("The leader must be one of the invited students")
        return self


class TeamCreate(InviteList):
    name: Text255
    # Optional: generated from the name when empty.
    code: str | None = None
    term: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=32)
    ]
    project_title: Text255
    project_description: Annotated[
        str | None, StringConstraints(strip_whitespace=True, max_length=5000)
    ] = None

    @field_validator("code", mode="after")
    @classmethod
    def _code(cls, value: str | None) -> str | None:
        if not value or not value.strip():
            return None
        code = value.strip().upper()
        if not TEAM_CODE.match(code):
            raise ValueError(
                "Use letters, digits, dots, dashes or underscores (2 to 63 characters)"
            )
        return code


class TeamUpdate(BaseModel):
    name: Text255 | None = None
    repo_url: Annotated[
        str | None, StringConstraints(strip_whitespace=True, max_length=1024)
    ] = None

    @field_validator("repo_url", mode="after")
    @classmethod
    def _repo(cls, value: str | None) -> str | None:
        if not value:
            return None
        if not REPO_URL.match(value):
            raise ValueError("The repository URL must start with https://")
        return value


class LeaderTransferRequest(BaseModel):
    to_user_id: uuid.UUID


class InvitationLookup(BaseModel):
    token: Annotated[str, StringConstraints(min_length=10, max_length=200)]


# --- responses -------------------------------------------------------------------------------


class ProjectOut(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None


class PersonOut(BaseModel):
    user_id: uuid.UUID
    name: str


class MemberOut(PersonOut):
    role: TeamRole
    # Shown to lecturers only.
    email: str | None
    github_username: str | None
    joined_at: datetime | None


class TeamSummary(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    term: str | None
    status: Literal["forming", "active"]
    project: ProjectOut | None
    my_role: TeamRole
    leader: PersonOut | None
    student_count: int
    lecturer_count: int
    # Lecturers only: invitations still waiting for an answer.
    pending_invitations: int | None
    repo_url: str | None


class InvitationOut(BaseModel):
    """An invitation as the team's lecturers see it."""

    id: uuid.UUID
    email: str
    role: Literal["lecturer", "member"]
    as_leader: bool
    status: InvitationState
    expires_at: datetime
    responded_at: datetime | None


class TeamDetail(TeamSummary):
    members: list[MemberOut]
    # Lecturers only; empty for students.
    invitations: list[InvitationOut]
    pending_leader: PersonOut | None


class MyInvitation(BaseModel):
    """An invitation as the invited person sees it."""

    id: uuid.UUID
    role: Literal["lecturer", "member"]
    as_leader: bool
    expires_at: datetime
    invited_by: str | None
    team_id: uuid.UUID
    team_code: str
    team_name: str
    term: str | None
    project_title: str | None


class InvitationResult(BaseModel):
    email: str
    outcome: Literal["invited", "reinvited", "already_member", "already_invited"]


class InviteSummary(BaseModel):
    results: list[InvitationResult]


class TeamCreated(BaseModel):
    team: TeamDetail
    invitations: list[InvitationResult]
