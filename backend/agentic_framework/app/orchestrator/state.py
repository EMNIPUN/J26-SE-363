from typing import TypedDict

from shared.contracts import (
    AgentName,
    AgentResponse,
    OrchestrationRequest,
    OrchestrationResponse,
)


class OrchestratorState(TypedDict, total=False):
    request: OrchestrationRequest
    target_agent: AgentName | None
    agent_responses: list[AgentResponse]
    response: OrchestrationResponse
