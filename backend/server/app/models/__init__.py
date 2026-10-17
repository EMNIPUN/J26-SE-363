"""Core API models. Importing this package registers every table on Base.metadata,
which is what Alembic compares against (see alembic/env.py)."""

from app.models.agent_run import AgentRun, AgentRunStatus
from app.models.group import Group, GroupMember
from app.models.project import Project, ProjectDocument
from app.models.user import User

__all__ = [
    "AgentRun",
    "AgentRunStatus",
    "Group",
    "GroupMember",
    "Project",
    "ProjectDocument",
    "User",
]
