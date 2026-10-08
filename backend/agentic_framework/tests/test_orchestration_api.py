import pytest
from fastapi.testclient import TestClient
from shared.contracts import (
    AgentName,
    AgentRequest,
    AgentResponse,
    OrchestrationResponse,
    ResultStatus,
)

from app.api.dependencies import get_orchestrator
from app.main import app
from app.orchestrator import AgentExecutor, Orchestrator

VALID_REQUEST = {
    "request_id": "req-001",
    "requester": {"user_id": "kc-123", "role": "student"},
    "action": "tutor.chat",
    "student_id": "ST001",
    "group_id": "G01",
    "project_id": "P-01",
    "context": {"project": {"project_id": "P-01", "title": "Online Food Ordering System"}},
    "input": {"message": "Explain JWT"},
}


class EchoTutor:
    name = AgentName.ADAPTIVE_TUTOR

    async def handle(self, request: AgentRequest) -> AgentResponse:
        return AgentResponse(
            request_id=request.request_id,
            agent_name=self.name,
            status=ResultStatus.COMPLETED,
            result={"answer": f"Echo: {request.input['message']}"},
        )


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_ai_backend_starts(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "UP"


def test_orchestration_accepts_the_shared_request_and_returns_placeholder(client):
    response = client.post("/api/v1/orchestration", json=VALID_REQUEST)

    assert response.status_code == 200
    body = OrchestrationResponse.model_validate(response.json())
    assert body.request_id == "req-001"
    assert body.status is ResultStatus.UNAVAILABLE
    assert body.agent_responses[0].agent_name is AgentName.ADAPTIVE_TUTOR


@pytest.mark.parametrize(
    "broken",
    [
        {k: v for k, v in VALID_REQUEST.items() if k != "requester"},
        {**VALID_REQUEST, "action": None},
        {**VALID_REQUEST, "action": "not-an-action"},
        {**VALID_REQUEST, "project_id": "P-99"},
    ],
)
def test_orchestration_rejects_invalid_requests(client, broken):
    assert client.post("/api/v1/orchestration", json=broken).status_code == 422


def test_orchestration_uses_registered_agents(client):
    app.dependency_overrides[get_orchestrator] = lambda: Orchestrator(
        AgentExecutor({AgentName.ADAPTIVE_TUTOR: EchoTutor()})
    )

    response = client.post("/api/v1/orchestration", json=VALID_REQUEST)

    body = OrchestrationResponse.model_validate(response.json())
    assert body.status is ResultStatus.COMPLETED
    assert body.result == {"answer": "Echo: Explain JWT"}
