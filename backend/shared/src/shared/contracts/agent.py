"""Generic contract between the Main Orchestrator and every specialized agent.

Agents receive an AgentRequest and return an AgentResponse. Agent-specific
input/output models live inside each agent's own directory and travel in
`AgentRequest.input` / `AgentResponse.result`.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator

from shared.contracts.context import RequesterContext, ScopedRequest

ACTION_PATTERN = r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$"


class AgentName(str, Enum):
    PROJECT_PLANNING = "project_planning"
    ADAPTIVE_TUTOR = "adaptive_tutor"
    PERFORMANCE_ASSESSMENT = "performance_assessment"
    AEGIS = "aegis"


ACTION_PREFIX_TO_AGENT: dict[str, AgentName] = {
    "planning": AgentName.PROJECT_PLANNING,
    "tutor": AgentName.ADAPTIVE_TUTOR,
    "performance": AgentName.PERFORMANCE_ASSESSMENT,
    "security": AgentName.AEGIS,
}


def agent_for_action(action: str | None) -> AgentName | None:
    """The agent that owns an action, found from its prefix ("tutor.chat" -> Adaptive Tutor)."""
    if not action:
        return None
    return ACTION_PREFIX_TO_AGENT.get(action.split(".", 1)[0])


class ResultStatus(str, Enum):
    COMPLETED = "completed"
    WAITING_FOR_INPUT = "waiting_for_input"
    UNAVAILABLE = "unavailable"
    FAILED = "failed"


class Evidence(BaseModel):
    """A piece of evidence that supports a result (commit, quiz score, scanner finding...)."""

    source: str
    description: str
    reference: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)


class NextAction(BaseModel):
    """A follow-up the orchestrator may perform.

    Agents never call each other. To involve another agent, an agent returns a
    NextAction with `target_agent` set and the orchestrator decides what to do.
    """

    type: str
    description: str | None = None
    target_agent: AgentName | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class ErrorInfo(BaseModel):
    code: str
    message: str
    retryable: bool = False


class ResultFields(BaseModel):
    """Fields shared by agent and orchestration responses."""

    status: ResultStatus
    result: dict[str, Any] = Field(default_factory=dict)
    evidence: list[Evidence] = Field(default_factory=list)
    next_action: NextAction | None = None
    error: ErrorInfo | None = None

    @model_validator(mode="after")
    def _failed_requires_error(self) -> "ResultFields":
        if self.status is ResultStatus.FAILED and self.error is None:
            raise ValueError("error is required when status is 'failed'")
        return self


class AgentRequest(ScopedRequest):
    """Request from the orchestrator to one agent.

    `action` names the capability, written as "<area>.<action>" (e.g. "tutor.chat").
    """

    action: str = Field(pattern=ACTION_PATTERN)
    requester: RequesterContext | None = None
    input: dict[str, Any] = Field(default_factory=dict)


class AgentResponse(ResultFields):
    request_id: str
    agent_name: AgentName
