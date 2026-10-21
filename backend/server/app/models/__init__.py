"""Core API models. Importing this package registers every table on Base.metadata,
which is what Alembic compares against (see alembic/env.py)."""

from app.models.agent_run import AgentRun, AgentRunStatus
<<<<<<< HEAD
from app.models.backlog_readiness_passport import BacklogReadinessPassport
from app.models.dart import DartEscalation, DartEvidence, DartIteration, DartSession
from app.models.decomposition_assessment import (
    CoverageAnalysisResult,
    CoverageElementRow,
    CoverageGateCheckRow,
    DecompositionAssessment,
    DecompositionToolOutput,
    InvestValidation,
    StoryAssessment,
    TaskAssessment,
    TaskCriterionResultRow,
    TaskValidationAssessment,
    UserStory,
    UserStoryTask,
)
from app.models.effort_estimation import (
    EffortEstimationAssessment,
    EffortToolOutput,
    EstimateComparison,
    ShapExplanation,
    StudentEffortEstimate,
)
from app.models.feedback import Feedback
from app.models.group import Group, GroupMember
from app.models.instructor_alert import InstructorAlert
from app.models.pipeline_session import PipelineSession
from app.models.project import Project, ProjectDocument
from app.models.quality_assessment import (
    QualityAssessment,
    QualityDimensionScore,
    QualityGateDecision,
    QualityToolOutput,
    StudentQualitySelfAssessment,
)
from app.models.requirement import Requirement
from app.models.retrieval_log import RetrievalLog
from app.models.sprint import Sprint
from app.models.sprint_backlog import SprintBacklogItem
from app.models.srs_document import SrsDocument
=======
from app.models.github import TeamGithub, TeamGithubAccess, UserGithubAccount
from app.models.group import Group, GroupMember, MemberRole, TeamStatus
from app.models.notification import Notification
from app.models.notification_preference import NotificationPreference
from app.models.project import Project, ProjectDocument
from app.models.team_invitation import InvitationStatus, TeamInvitation
from app.models.term import Term
>>>>>>> 28f368287251c65852ddd979d24c9796336443da
from app.models.user import User
from app.models.user_avatar import UserAvatar

__all__ = [
    "AgentRun",
    "AgentRunStatus",
    "BacklogReadinessPassport",
    "CoverageAnalysisResult",
    "CoverageElementRow",
    "CoverageGateCheckRow",
    "DartEscalation",
    "DartEvidence",
    "DartIteration",
    "DartSession",
    "DecompositionAssessment",
    "DecompositionToolOutput",
    "EffortEstimationAssessment",
    "EffortToolOutput",
    "EstimateComparison",
    "Feedback",
    "Group",
    "GroupMember",
<<<<<<< HEAD
    "InstructorAlert",
    "InvestValidation",
    "PipelineSession",
    "Project",
    "ProjectDocument",
    "QualityAssessment",
    "QualityDimensionScore",
    "QualityGateDecision",
    "QualityToolOutput",
    "Requirement",
    "RetrievalLog",
    "ShapExplanation",
    "Sprint",
    "SprintBacklogItem",
    "SrsDocument",
    "StoryAssessment",
    "StudentEffortEstimate",
    "StudentQualitySelfAssessment",
    "TaskAssessment",
    "TaskCriterionResultRow",
    "TaskValidationAssessment",
    "User",
    "UserStory",
    "UserStoryTask",
=======
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
>>>>>>> 28f368287251c65852ddd979d24c9796336443da
]
