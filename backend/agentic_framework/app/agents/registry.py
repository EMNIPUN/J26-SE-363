"""The agents the orchestrator can invoke.

Each agent owner adds one entry here once their agent implements BaseAgent, e.g.
    AgentName.ADAPTIVE_TUTOR: AdaptiveTutorAgent(),
Agents that are not registered yet answer with status "unavailable".
"""

from shared.contracts import AgentName

from app.agents.adaptive_tutor.agent import AdaptiveTutorAgent
from app.agents.base import BaseAgent
from app.core.config import settings
from app.core.tutor_token_context import RequestScopedTutorTokenProvider


def build_agent_registry() -> dict[AgentName, BaseAgent]:
    """Build the live agent map. Construction must not open network connections."""
    return {
        AgentName.ADAPTIVE_TUTOR: AdaptiveTutorAgent(
            mcp_url=settings.TUTOR_MCP_URL,
            token_provider=RequestScopedTutorTokenProvider(),
        ),
    }
