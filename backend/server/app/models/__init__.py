"""Core API models. Importing this package registers every table on Base.metadata,
which is what Alembic compares against (see alembic/env.py)."""

from app.models.agent_run import AgentRun, AgentRunStatus
from app.models.dart import DartEscalation, DartEvidence, DartIteration, DartSession
from app.models.decomposition_assessment import (
    CoverageAnalysisResult,
    DecompositionAssessment,
    DecompositionToolOutput,
    InvestValidation,
    UserStory,
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
from app.models.user import User

__all__ = [
    "AgentRun",
    "AgentRunStatus",
    "CoverageAnalysisResult",
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
    "StudentEffortEstimate",
    "StudentQualitySelfAssessment",
    "User",
    "UserStory",
]
