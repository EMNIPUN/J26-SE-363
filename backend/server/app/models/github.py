import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin


class UserGithubAccount(TimestampMixin, Base):
    """The GitHub account a person proved to own by signing in to GitHub from the system.

    `github_id` is GitHub's own number, so a renamed account stays the same account; `login`
    is what GitHub called it at the last sign-in (lower case). It differs from
    `users.github_username`, which the person typed.
    """

    __tablename__ = "user_github_accounts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    github_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    login: Mapped[str] = mapped_column(String(64), index=True)
    avatar_url: Mapped[str | None] = mapped_column(String(1024))
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class TeamGithub(TimestampMixin, Base):
    """The GitHub App installation of a team and the one repository chosen from it.

    The installation is made by the team leader on their own GitHub account (or organisation);
    `repo_full_name` stays empty until the leader picks the repository the team works in.
    """

    __tablename__ = "team_github"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    group_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("groups.id", ondelete="CASCADE"), unique=True
    )
    installation_id: Mapped[int] = mapped_column(BigInteger)
    account_login: Mapped[str | None] = mapped_column(String(64))
    repo_full_name: Mapped[str | None] = mapped_column(String(255))
    repo_id: Mapped[int | None] = mapped_column(BigInteger)
    repo_private: Mapped[bool] = mapped_column(Boolean, default=False)
    linked_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )


class TeamGithubAccess(TimestampMixin, Base):
    """What GitHub said a member's linked account may do on the team repository, and when."""

    __tablename__ = "team_github_access"
    __table_args__ = (UniqueConstraint("group_id", "user_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    group_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("groups.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    permission: Mapped[str] = mapped_column(String(8))  # none | read | write | admin
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
