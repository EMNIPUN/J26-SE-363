"""Core API models. Importing this package registers every table on Base.metadata,
which is what Alembic compares against (see alembic/env.py)."""

from app.models.agent_run import AgentRun, AgentRunStatus
from app.models.github import TeamGithub, TeamGithubAccess, UserGithubAccount
from app.models.group import Group, GroupMember, MemberRole, TeamStatus
from app.models.notification import Notification
from app.models.notification_preference import NotificationPreference
from app.models.project import Project, ProjectDocument
from app.models.team_invitation import InvitationStatus, TeamInvitation
from app.models.term import Term
from app.models.user import User
from app.models.user_avatar import UserAvatar

__all__ = [
    "AgentRun",
    "AgentRunStatus",
    "Group",
    "GroupMember",
    "InvitationStatus",
    "MemberRole",
    "TeamGithub",
    "TeamGithubAccess",
    "UserGithubAccount",
    "Notification",
    "NotificationPreference",
    "Project",
    "ProjectDocument",
    "TeamInvitation",
    "TeamStatus",
    "Term",
    "User",
    "UserAvatar",
]
