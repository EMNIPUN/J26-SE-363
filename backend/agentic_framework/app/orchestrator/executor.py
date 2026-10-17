"""Invokes one registered agent and always returns an AgentResponse."""

import logging
from collections.abc import Mapping

from shared.contracts import (
    AgentName,
    AgentRequest,
    AgentResponse,
    ErrorInfo,
    OrchestrationRequest,
    ResultStatus,
)

from app.agents.base import BaseAgent

logger = logging.getLogger(__name__)


def build_agent_request(request: OrchestrationRequest) -> AgentRequest:
    """Pass the orchestration scope and context on to the agent unchanged."""
    return AgentRequest(
        request_id=request.request_id,
        student_id=request.student_id,
        group_id=request.group_id,
        project_id=request.project_id,
        sprint_id=request.sprint_id,
        task_id=request.task_id,
        context=request.context,
        action=request.action,
        requester=request.requester,
        input=request.input,
    )


class AgentExecutor:
    def __init__(self, registry: Mapping[AgentName, BaseAgent]):
        self._registry = dict(registry)

    async def execute(self, agent_name: AgentName, request: AgentRequest) -> AgentResponse:
        agent = self._registry.get(agent_name)
        if agent is None:
            return AgentResponse(
                request_id=request.request_id,
                agent_name=agent_name,
                status=ResultStatus.UNAVAILABLE,
                result={"detail": f"The {agent_name.value} agent is not available yet."},
            )

        try:
            return await agent.handle(request)
        except Exception as exc:
            logger.exception("Agent %s failed for request %s", agent_name.value, request.request_id)
            return AgentResponse(
                request_id=request.request_id,
                agent_name=agent_name,
                status=ResultStatus.FAILED,
                error=ErrorInfo(code="agent_error", message=str(exc)),
            )
