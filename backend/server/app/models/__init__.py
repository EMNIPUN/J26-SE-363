"""Core API models. Importing this package registers every table on Base.metadata,
which is what Alembic compares against (see alembic/env.py)."""

from app.models.agent_run import AgentRun, AgentRunStatus
from app.models.dart_case import DartCaseRecord
from app.models.decomposition import DecompositionRecord
from app.models.group import Group, GroupMember
from app.models.project import Project, ProjectDocument
from app.models.requirement_quality import RequirementQualityRecord
from app.models.user import User
from app.models.user_story import UserStoryRecord

__all__ = [
    "AgentRun",
    "AgentRunStatus",
    "DartCaseRecord",
    "DecompositionRecord",
    "Group",
    "GroupMember",
    "Project",
    "ProjectDocument",
    "RequirementQualityRecord",
    "User",
    "UserStoryRecord",
]
