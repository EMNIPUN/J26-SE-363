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
from app.core.config import settings
from app.core.tutor_token_context import TUTOR_ACCESS_TOKEN_HEADER, get_request_tutor_access_token
from app.main import app
from app.orchestrator import AgentExecutor, Orchestrator

INTERNAL = "unit-test-ai-backend-internal-token-32c"
TUTOR_TOKEN = "opaque-tutor-access-token-for-unit-tests-only"
OTHER_ACTION_REQUEST = {
    "request_id": "req-002",
    "requester": {"user_id": "kc-123", "role": "student"},
    "action": "planning.start",
    "input": {"goal": "plan"},
}

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

COMPETENCY_REQUEST = {
    "request_id": "req-003",
    "requester": {"user_id": "kc-123", "role": "student"},
    "action": "tutor.estimate_competency",
    "student_id": "ST001",
    "project_id": "P-CAMPUS",
    "sprint_id": "sprint-02",
    "input": {},
}


class EchoTutor:
    name = AgentName.ADAPTIVE_TUTOR

    async def handle(self, request: AgentRequest) -> AgentResponse:
        # Prove request-scoped token is visible to the agent path without returning it.
        assert get_request_tutor_access_token() == TUTOR_TOKEN
        return AgentResponse(
            request_id=request.request_id,
            agent_name=self.name,
            status=ResultStatus.COMPLETED,
            result={"answer": f"Echo: {request.input['message']}"},
        )


class EchoTutorNoToken:
    name = AgentName.ADAPTIVE_TUTOR

    async def handle(self, request: AgentRequest) -> AgentResponse:
        assert get_request_tutor_access_token() is None
        return AgentResponse(
            request_id=request.request_id,
            agent_name=self.name,
            status=ResultStatus.COMPLETED,
            result={"answer": f"Echo: {request.input['message']}"},
        )


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(settings, "INTERNAL_TOKEN", INTERNAL)
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def auth_headers(**extra) -> dict[str, str]:
    return {"X-Internal-Token": INTERNAL, **extra}


def test_ai_backend_starts(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "UP"


def test_orchestration_rejects_missing_service_credential(client):
    response = client.post("/api/v1/orchestration", json=VALID_REQUEST)
    assert response.status_code == 401
    assert INTERNAL not in response.text
    assert TUTOR_TOKEN not in response.text


def test_orchestration_rejects_invalid_service_credential(client):
    response = client.post(
        "/api/v1/orchestration",
        json=VALID_REQUEST,
        headers={"X-Internal-Token": "wrong-token-that-is-long-enough-xx"},
    )
    assert response.status_code == 401
    assert INTERNAL not in response.text


def test_orchestration_fails_closed_when_internal_token_unset(client, monkeypatch):
    monkeypatch.setattr(settings, "INTERNAL_TOKEN", None)
    response = client.post(
        "/api/v1/orchestration",
        json=VALID_REQUEST,
        headers=auth_headers(),
    )
    assert response.status_code == 503
    assert "not configured" in response.json()["detail"]


def test_orchestration_accepts_the_shared_request_and_returns_placeholder(client):
    response = client.post(
        "/api/v1/orchestration",
        json=VALID_REQUEST,
        headers=auth_headers(),
    )

    assert response.status_code == 200
    body = OrchestrationResponse.model_validate(response.json())
    assert body.request_id == "req-001"
    assert body.status is ResultStatus.UNAVAILABLE
    assert body.agent_responses[0].agent_name is AgentName.ADAPTIVE_TUTOR
    assert TUTOR_TOKEN not in response.text
    assert INTERNAL not in response.text


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
    assert (
        client.post("/api/v1/orchestration", json=broken, headers=auth_headers()).status_code
        == 422
    )


def test_orchestration_uses_registered_agents(client):
    app.dependency_overrides[get_orchestrator] = lambda: Orchestrator(
        AgentExecutor({AgentName.ADAPTIVE_TUTOR: EchoTutorNoToken()})
    )

    response = client.post(
        "/api/v1/orchestration",
        json=VALID_REQUEST,
        headers=auth_headers(),
    )

    body = OrchestrationResponse.model_validate(response.json())
    assert body.status is ResultStatus.COMPLETED
    assert body.result == {"answer": "Echo: Explain JWT"}
    assert TUTOR_TOKEN not in response.text


def test_tutor_token_header_bound_for_tutor_chat_only(client):
    app.dependency_overrides[get_orchestrator] = lambda: Orchestrator(
        AgentExecutor({AgentName.ADAPTIVE_TUTOR: EchoTutor()})
    )

    response = client.post(
        "/api/v1/orchestration",
        json=VALID_REQUEST,
        headers=auth_headers(**{TUTOR_ACCESS_TOKEN_HEADER: TUTOR_TOKEN}),
    )

    assert response.status_code == 200
    body = OrchestrationResponse.model_validate(response.json())
    assert body.status is ResultStatus.COMPLETED
    assert TUTOR_TOKEN not in response.text
    assert get_request_tutor_access_token() is None


def test_tutor_token_header_bound_for_estimate_competency(client):
    class EchoCompetencyTutor:
        name = AgentName.ADAPTIVE_TUTOR

        async def handle(self, request: AgentRequest) -> AgentResponse:
            assert get_request_tutor_access_token() == TUTOR_TOKEN
            return AgentResponse(
                request_id=request.request_id,
                agent_name=self.name,
                status=ResultStatus.COMPLETED,
                result={"estimates": []},
            )

    app.dependency_overrides[get_orchestrator] = lambda: Orchestrator(
        AgentExecutor({AgentName.ADAPTIVE_TUTOR: EchoCompetencyTutor()})
    )

    response = client.post(
        "/api/v1/orchestration",
        json=COMPETENCY_REQUEST,
        headers=auth_headers(**{TUTOR_ACCESS_TOKEN_HEADER: TUTOR_TOKEN}),
    )

    assert response.status_code == 200
    body = OrchestrationResponse.model_validate(response.json())
    assert body.status is ResultStatus.COMPLETED
    assert TUTOR_TOKEN not in response.text
    assert get_request_tutor_access_token() is None


def test_tutor_token_header_rejected_for_non_tutor_action(client):
    response = client.post(
        "/api/v1/orchestration",
        json=OTHER_ACTION_REQUEST,
        headers=auth_headers(**{TUTOR_ACCESS_TOKEN_HEADER: TUTOR_TOKEN}),
    )
    assert response.status_code == 400
    assert "not allowed" in response.json()["detail"]
    assert TUTOR_TOKEN not in response.text
    assert get_request_tutor_access_token() is None


def test_empty_tutor_token_header_rejected(client):
    response = client.post(
        "/api/v1/orchestration",
        json=VALID_REQUEST,
        headers=auth_headers(**{TUTOR_ACCESS_TOKEN_HEADER: "   "}),
    )
    assert response.status_code == 400
    assert get_request_tutor_access_token() is None


def test_tutor_token_alone_does_not_authorize(client):
    response = client.post(
        "/api/v1/orchestration",
        json=VALID_REQUEST,
        headers={TUTOR_ACCESS_TOKEN_HEADER: TUTOR_TOKEN},
    )
    assert response.status_code == 401


def test_tutor_token_cleared_after_agent_exception(client):
    class BoomTutor:
        name = AgentName.ADAPTIVE_TUTOR

        async def handle(self, request: AgentRequest) -> AgentResponse:
            assert get_request_tutor_access_token() == TUTOR_TOKEN
            raise RuntimeError("simulated agent failure")

    app.dependency_overrides[get_orchestrator] = lambda: Orchestrator(
        AgentExecutor({AgentName.ADAPTIVE_TUTOR: BoomTutor()})
    )

    response = client.post(
        "/api/v1/orchestration",
        json=VALID_REQUEST,
        headers=auth_headers(**{TUTOR_ACCESS_TOKEN_HEADER: TUTOR_TOKEN}),
    )

    # Executor converts agent exceptions into FAILED responses; route finally still clears token.
    assert response.status_code == 200
    body = OrchestrationResponse.model_validate(response.json())
    assert body.status is ResultStatus.FAILED
    assert TUTOR_TOKEN not in response.text
    assert get_request_tutor_access_token() is None


def test_tutor_token_cleared_after_success(client):
    app.dependency_overrides[get_orchestrator] = lambda: Orchestrator(
        AgentExecutor({AgentName.ADAPTIVE_TUTOR: EchoTutor()})
    )

    response = client.post(
        "/api/v1/orchestration",
        json=VALID_REQUEST,
        headers=auth_headers(**{TUTOR_ACCESS_TOKEN_HEADER: TUTOR_TOKEN}),
    )
    assert response.status_code == 200
    assert get_request_tutor_access_token() is None
