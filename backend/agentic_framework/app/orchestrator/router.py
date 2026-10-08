"""Decides which agent handles a request.

Known actions are routed by their prefix ("tutor.chat" -> Adaptive Tutor) using
the shared ACTION_PREFIX_TO_AGENT map. Free-text requests (`message` without
`action`) are not routed yet; LLM-based routing is a later step.
"""

from shared.contracts import AgentName, OrchestrationRequest, agent_for_action


def select_agent(request: OrchestrationRequest) -> AgentName | None:
    return agent_for_action(request.action)
