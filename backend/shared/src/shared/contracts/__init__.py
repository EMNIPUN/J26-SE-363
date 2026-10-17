"""Shared Pydantic contracts used by the Core API, the AI Backend and all agents."""

from shared.contracts.agent import (
    ACTION_PREFIX_TO_AGENT,
    AgentName,
    AgentRequest,
    AgentResponse,
    ErrorInfo,
    Evidence,
    NextAction,
    ResultStatus,
    agent_for_action,
)
from shared.contracts.context import (
    GroupContext,
    ProjectContext,
    RequesterContext,
    SelviaContext,
    SprintContext,
    StudentContext,
    TaskContext,
    UserRole,
)
from shared.contracts.orchestration import OrchestrationRequest, OrchestrationResponse

__all__ = [
    "ACTION_PREFIX_TO_AGENT",
    "AgentName",
    "AgentRequest",
    "AgentResponse",
    "ErrorInfo",
    "Evidence",
    "GroupContext",
    "NextAction",
    "OrchestrationRequest",
    "OrchestrationResponse",
    "ProjectContext",
    "RequesterContext",
    "ResultStatus",
    "SelviaContext",
    "SprintContext",
    "StudentContext",
    "TaskContext",
    "UserRole",
    "agent_for_action",
]
