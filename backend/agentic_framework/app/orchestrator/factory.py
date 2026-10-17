"""The one Orchestrator instance used by both the HTTP route and the background worker."""

from functools import lru_cache

from app.agents.registry import build_agent_registry
from app.orchestrator.executor import AgentExecutor
from app.orchestrator.graph import Orchestrator


@lru_cache
def get_orchestrator() -> Orchestrator:
    return Orchestrator(AgentExecutor(build_agent_registry()))
