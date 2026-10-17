"""The agents the orchestrator can invoke.

Each agent owner adds one entry here once their agent implements BaseAgent, e.g.
    AgentName.ADAPTIVE_TUTOR: AdaptiveTutorAgent(),
Agents that are not registered yet answer with status "unavailable".
"""

from shared.contracts import AgentName

from app.agents.base import BaseAgent


def build_agent_registry() -> dict[AgentName, BaseAgent]:
    return {}
