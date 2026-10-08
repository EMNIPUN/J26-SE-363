"""Main Orchestrator LangGraph: route -> execute agent -> finalize.

This is the foundation only: one agent per request. Multi-step workflows
(acting on an agent's `next_action`) are added later.
"""

from langgraph.graph import END, START, StateGraph
from shared.contracts import OrchestrationRequest, OrchestrationResponse, ResultStatus

from app.orchestrator.executor import AgentExecutor, build_agent_request
from app.orchestrator.router import select_agent
from app.orchestrator.state import OrchestratorState


def build_orchestrator_graph(executor: AgentExecutor):
    async def route(state: OrchestratorState) -> OrchestratorState:
        return {"target_agent": select_agent(state["request"])}

    async def execute(state: OrchestratorState) -> OrchestratorState:
        agent_request = build_agent_request(state["request"])
        agent_response = await executor.execute(state["target_agent"], agent_request)
        return {"agent_responses": [*state.get("agent_responses", []), agent_response]}

    def finalize(state: OrchestratorState) -> OrchestratorState:
        request = state["request"]
        agent_responses = state.get("agent_responses", [])
        if not agent_responses:
            response = OrchestrationResponse(
                request_id=request.request_id,
                status=ResultStatus.UNAVAILABLE,
                result={"detail": "No agent could be selected for this request yet."},
            )
        else:
            last = agent_responses[-1]
            response = OrchestrationResponse(
                request_id=request.request_id,
                status=last.status,
                result=last.result,
                evidence=[item for r in agent_responses for item in r.evidence],
                next_action=last.next_action,
                error=last.error,
                agent_responses=agent_responses,
            )
        return {"response": response}

    def after_route(state: OrchestratorState) -> str:
        return "execute" if state.get("target_agent") else "finalize"

    graph = StateGraph(OrchestratorState)
    graph.add_node("route", route)
    graph.add_node("execute", execute)
    graph.add_node("finalize", finalize)
    graph.add_edge(START, "route")
    graph.add_conditional_edges("route", after_route, ["execute", "finalize"])
    graph.add_edge("execute", "finalize")
    graph.add_edge("finalize", END)
    return graph.compile()


class Orchestrator:
    def __init__(self, executor: AgentExecutor):
        self._graph = build_orchestrator_graph(executor)

    async def handle(self, request: OrchestrationRequest) -> OrchestrationResponse:
        final_state = await self._graph.ainvoke({"request": request})
        return final_state["response"]
