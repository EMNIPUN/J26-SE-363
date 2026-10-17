"""Contract between the Core API and the AI Backend (POST /api/v1/orchestration)."""

from typing import Any

from pydantic import Field, model_validator

from shared.contracts.agent import ACTION_PATTERN, AgentResponse, ResultFields
from shared.contracts.context import RequesterContext, ScopedRequest


class OrchestrationRequest(ScopedRequest):
    """Sent by the Core API after it has verified the user and built the context.

    Use `action` for a known capability (e.g. "tutor.chat"), or `message` for a
    free-text request the orchestrator has to interpret (e.g. lecturer chat).
    """

    requester: RequesterContext
    action: str | None = Field(default=None, pattern=ACTION_PATTERN)
    message: str | None = None
    input: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _action_or_message(self) -> "OrchestrationRequest":
        if not self.action and not self.message:
            raise ValueError("either action or message is required")
        return self


class OrchestrationResponse(ResultFields):
    """Final orchestrator answer; `agent_responses` lists every agent that took part."""

    request_id: str
    agent_responses: list[AgentResponse] = Field(default_factory=list)
