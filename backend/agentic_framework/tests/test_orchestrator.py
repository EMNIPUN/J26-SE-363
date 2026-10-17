import pytest
from shared.contracts import (
    AgentName,
    AgentRequest,
    AgentResponse,
    Evidence,
    OrchestrationRequest,
    RequesterContext,
    ResultStatus,
    SelviaContext,
    StudentContext,
    UserRole,
)

from app.agents.base import BaseAgent
from app.agents.registry import build_agent_registry
from app.orchestrator import AgentExecutor, Orchestrator
from app.orchestrator.router import select_agent

STUDENT = RequesterContext(user_id="kc-123", role=UserRole.STUDENT)


class FakeAgent:
    def __init__(self, name: AgentName):
        self.name = name
        self.received: list[AgentRequest] = []

    async def handle(self, request: AgentRequest) -> AgentResponse:
        self.received.append(request)
        return AgentResponse(
            request_id=request.request_id,
            agent_name=self.name,
            status=ResultStatus.COMPLETED,
            result={"echo": request.input},
            evidence=[Evidence(source="fake", description="test evidence")],
        )


class BrokenAgent:
    name = AgentName.AEGIS

    async def handle(self, request: AgentRequest) -> AgentResponse:
        raise RuntimeError("scanner crashed")


def make_request(**overrides) -> OrchestrationRequest:
    fields = {"requester": STUDENT, "action": "tutor.chat", "input": {"message": "Explain JWT"}}
    fields.update(overrides)
    return OrchestrationRequest(**fields)


@pytest.mark.parametrize(
    ("action", "agent"),
    [
        ("planning.analyze_requirements", AgentName.PROJECT_PLANNING),
        ("tutor.chat", AgentName.ADAPTIVE_TUTOR),
        ("performance.assess_student", AgentName.PERFORMANCE_ASSESSMENT),
        ("security.scan_repository", AgentName.AEGIS),
        ("viva.prepare_questions", None),
    ],
)
def test_router_selects_agent_by_action_prefix(action, agent):
    assert select_agent(make_request(action=action)) is agent


def test_router_does_not_route_free_text_yet():
    assert select_agent(make_request(action=None, message="What groups are falling behind?")) is None


def test_registry_is_empty_until_agents_register():
    assert build_agent_registry() == {}
    assert isinstance(FakeAgent(AgentName.ADAPTIVE_TUTOR), BaseAgent)


@pytest.mark.asyncio
async def test_executor_reports_unregistered_agent_as_unavailable():
    response = await AgentExecutor({}).execute(AgentName.AEGIS, AgentRequest(action="security.scan_repository"))

    assert response.status is ResultStatus.UNAVAILABLE
    assert response.agent_name is AgentName.AEGIS


@pytest.mark.asyncio
async def test_executor_turns_agent_exception_into_failed_response():
    request = AgentRequest(action="security.scan_repository")

    response = await AgentExecutor({AgentName.AEGIS: BrokenAgent()}).execute(AgentName.AEGIS, request)

    assert response.status is ResultStatus.FAILED
    assert response.error.code == "agent_error"
    assert response.request_id == request.request_id


@pytest.mark.asyncio
async def test_orchestrator_passes_scope_and_context_to_the_agent():
    tutor = FakeAgent(AgentName.ADAPTIVE_TUTOR)
    orchestrator = Orchestrator(AgentExecutor({AgentName.ADAPTIVE_TUTOR: tutor}))
    request = make_request(group_id="G01", context=SelviaContext(student=StudentContext(student_id="ST001")))

    response = await orchestrator.handle(request)

    agent_request = tutor.received[0]
    assert agent_request.request_id == request.request_id
    assert agent_request.student_id == "ST001"
    assert agent_request.group_id == "G01"
    assert agent_request.action == "tutor.chat"
    assert agent_request.requester == STUDENT

    assert response.status is ResultStatus.COMPLETED
    assert response.result == {"echo": {"message": "Explain JWT"}}
    assert [r.agent_name for r in response.agent_responses] == [AgentName.ADAPTIVE_TUTOR]
    assert response.evidence[0].source == "fake"


@pytest.mark.asyncio
async def test_orchestrator_without_a_matching_agent_returns_unavailable():
    response = await Orchestrator(AgentExecutor({})).handle(make_request(action=None, message="Hello"))

    assert response.status is ResultStatus.UNAVAILABLE
    assert response.agent_responses == []
