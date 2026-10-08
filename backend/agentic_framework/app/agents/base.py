"""Interface every specialized agent implements so the orchestrator can invoke it."""

from typing import Protocol, runtime_checkable

from shared.contracts import AgentName, AgentRequest, AgentResponse


@runtime_checkable
class BaseAgent(Protocol):
    name: AgentName

    async def handle(self, request: AgentRequest) -> AgentResponse: ...
