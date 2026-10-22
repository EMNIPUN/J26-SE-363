"""Offline tests for POST /api/v1/tutor/chat (no SLAP, Keycloak, AI Backend, or DB)."""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from shared.contracts import OrchestrationResponse, ResultStatus, UserRole

from app.clients.slap_tutor_mint import (
    SlapTutorMintAuthError,
    SlapTutorMintConfigError,
    SlapTutorMintIdentityNotFoundError,
    SlapTutorMintNetworkError,
    SlapTutorMintProtocolError,
    SlapTutorMintTimeoutError,
    SlapTutorMintUnavailableError,
    TutorAccessToken,
)
from app.core.security import CurrentUser, TokenVerifier, get_token_verifier
from app.main import app
from app.modules.tutor.schemas import (
    PP1_DEFAULT_PROJECT_ID,
    PP1_DEFAULT_SPRINT_ID,
    PP1_DEFAULT_STUDENT_ID,
    TutorChatRequest,
    TutorCompetencyRequest,
)
from app.modules.tutor.service import (
    TUTOR_ACTION,
    TUTOR_COMPETENCY_ACTION,
    TUTOR_COMPETENCY_UNAVAILABLE_DETAIL,
    TUTOR_UNAVAILABLE_DETAIL,
    TutorChatService,
    build_competency_orchestration_request,
    build_tutor_orchestration_request,
    get_tutor_chat_service,
    is_adaptive_tutor_execution_ready,
    is_tutor_token_handoff_available,
    map_tutor_service_error,
)

ISSUER = "http://localhost:8000/auth/realms/mentor"
SIGNING_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
FAKE_TOKEN = "opaque-tutor-access-token-must-never-leak"
FAKE_MINT_SECRET = "unit-test-internal-mint-token-not-real-32chars"


def make_token(**overrides) -> str:
    now = int(time.time())
    claims = {
        "iss": ISSUER,
        "sub": "kc-student-1",
        "azp": "mentor-frontend",
        "iat": now,
        "exp": now + 300,
        "preferred_username": "it21000001",
        "realm_access": {"roles": ["student"]},
    }
    claims.update(overrides)
    claims = {k: v for k, v in claims.items() if v is not None}
    return jwt.encode(claims, SIGNING_KEY, algorithm="RS256", headers={"kid": "test-key"})


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def make_verifier() -> TokenVerifier:
    return TokenVerifier(
        issuer=ISSUER,
        allowed_clients=["mentor-frontend"],
        key_resolver=lambda token: SIGNING_KEY.public_key(),
    )


@pytest.fixture
def client():
    app.dependency_overrides[get_token_verifier] = make_verifier
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_adaptive_tutor_execution_ready_gate_is_open():
    assert is_adaptive_tutor_execution_ready() is True


def test_handoff_requires_internal_token_and_tutor_ready(monkeypatch):
    from app.modules.tutor import service as tutor_service

    monkeypatch.setattr(tutor_service.settings, "AI_BACKEND_INTERNAL_TOKEN", None)
    monkeypatch.setattr(tutor_service, "is_adaptive_tutor_execution_ready", lambda: True)
    assert is_tutor_token_handoff_available() is False

    monkeypatch.setattr(
        tutor_service.settings,
        "AI_BACKEND_INTERNAL_TOKEN",
        "unit-test-ai-backend-internal-token-32c",
    )
    # Patch the function used by is_tutor_token_handoff_available via module attribute
    monkeypatch.setattr(
        "app.modules.tutor.service.is_adaptive_tutor_execution_ready",
        lambda: True,
    )
    assert tutor_service.is_tutor_token_handoff_available() is True


def test_unauthenticated_chat_returns_401(client):
    response = client.post("/api/v1/tutor/chat", json={"message": "Hello"})
    assert response.status_code == 401
    assert FAKE_TOKEN not in response.text


@pytest.mark.parametrize(
    "roles",
    [
        ["lecturer"],
        ["admin"],
    ],
)
def test_non_student_chat_returns_403(client, roles):
    token = make_token(realm_access={"roles": roles})
    response = client.post(
        "/api/v1/tutor/chat",
        json={"message": "Hello"},
        headers=auth_header(token),
    )
    assert response.status_code == 403


def test_valid_schema_accepted_but_fails_closed_without_minting(client):
    mint = MagicMock()
    mint.mint_tutor_access_token = AsyncMock()
    ai = MagicMock()
    ai.orchestrate = AsyncMock()
    start_ai_job = MagicMock()

    service = TutorChatService(
        mint_client_factory=lambda: mint,
        ai_client_factory=lambda: ai,
        handoff_available=lambda: False,
    )
    app.dependency_overrides[get_tutor_chat_service] = lambda: service

    request_id = str(uuid4())
    response = client.post(
        "/api/v1/tutor/chat",
        json={"message": "Explain JWT", "request_id": request_id},
        headers=auth_header(make_token()),
    )

    assert response.status_code == 503
    assert response.json()["detail"] == TUTOR_UNAVAILABLE_DETAIL
    assert FAKE_TOKEN not in response.text
    mint.mint_tutor_access_token.assert_not_called()
    ai.orchestrate.assert_not_called()
    start_ai_job.assert_not_called()


def test_empty_message_rejected(client):
    response = client.post(
        "/api/v1/tutor/chat",
        json={"message": "   "},
        headers=auth_header(make_token()),
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    "payload",
    [
        {"message": "Hi", "issuer": ISSUER},
        {"message": "Hi", "subject": "kc-other"},
        {"message": "Hi", "userId": "u-1"},
        {"message": "Hi", "studentId": "ST001"},
        {"message": "Hi", "requester": {"user_id": "x", "role": "student"}},
        {"message": "Hi", "action": "planning.start"},
        {"message": "Hi", "scopes": ["tutor:evidence.read"]},
        {"message": "Hi", "input": {"message": "hijack"}},
        {"message": "Hi", "accessToken": "browser-supplied-token-must-be-rejected"},
        {"message": "Hi", "unknown": "field"},
    ],
    ids=[
        "issuer",
        "subject",
        "userId",
        "studentId",
        "requester",
        "action",
        "scopes",
        "input",
        "accessToken",
        "unknown",
    ],
)
def test_unknown_and_identity_fields_rejected(client, payload):
    response = client.post(
        "/api/v1/tutor/chat",
        json=payload,
        headers=auth_header(make_token()),
    )
    assert response.status_code == 422
    # Minted tokens must never appear; FastAPI may echo rejected request keys in 422 bodies.
    assert FAKE_TOKEN not in response.text
    assert FAKE_MINT_SECRET not in response.text


def test_build_orchestration_uses_trusted_requester_and_fixed_action():
    user = CurrentUser(user_id="kc-student-1", role=UserRole.STUDENT)
    body = TutorChatRequest(message="Explain JWT")
    request = build_tutor_orchestration_request(user, body)

    assert request.action == TUTOR_ACTION
    assert request.action == "tutor.chat"
    assert request.requester == user.to_requester()
    assert request.input == {"message": "Explain JWT"}
    assert request.student_id == PP1_DEFAULT_STUDENT_ID
    assert request.project_id == PP1_DEFAULT_PROJECT_ID
    assert request.sprint_id == PP1_DEFAULT_SPRINT_ID
    assert "accessToken" not in request.model_dump(mode="json")


def test_build_competency_orchestration_uses_pp1_defaults():
    user = CurrentUser(user_id="kc-student-1", role=UserRole.STUDENT)
    body = TutorCompetencyRequest()
    request = build_competency_orchestration_request(user, body)

    assert request.action == TUTOR_COMPETENCY_ACTION
    assert request.student_id == PP1_DEFAULT_STUDENT_ID
    assert request.project_id == PP1_DEFAULT_PROJECT_ID
    assert request.sprint_id == PP1_DEFAULT_SPRINT_ID
    assert request.input == {}
    assert request.requester == user.to_requester()


def test_unauthenticated_competency_returns_401(client):
    response = client.post("/api/v1/tutor/competency", json={})
    assert response.status_code == 401


def test_competency_fails_closed_without_handoff(client):
    mint = MagicMock()
    mint.mint_tutor_access_token = AsyncMock()
    ai = MagicMock()
    ai.orchestrate = AsyncMock()
    service = TutorChatService(
        mint_client_factory=lambda: mint,
        ai_client_factory=lambda: ai,
        handoff_available=lambda: False,
    )
    app.dependency_overrides[get_tutor_chat_service] = lambda: service

    response = client.post(
        "/api/v1/tutor/competency",
        json={},
        headers=auth_header(make_token()),
    )
    assert response.status_code == 503
    assert response.json()["detail"] == TUTOR_COMPETENCY_UNAVAILABLE_DETAIL
    mint.mint_tutor_access_token.assert_not_called()
    ai.orchestrate.assert_not_called()


@pytest.mark.asyncio
async def test_competency_mints_and_orchestrates(monkeypatch):
    from app.modules.tutor import service as tutor_service

    monkeypatch.setattr(tutor_service.settings, "KEYCLOAK_SERVER_URL", "http://localhost:8000/auth")
    monkeypatch.setattr(tutor_service.settings, "KEYCLOAK_REALM", "mentor")

    class FakeMint:
        async def mint_tutor_access_token(self, *, issuer, subject):
            return TutorAccessToken(
                access_token=FAKE_TOKEN,
                token_type="Bearer",
                expires_in=300,
                expires_at=1,
                resource="http://slap.test/mcp",
            )

    ai = MagicMock()
    ai.orchestrate = AsyncMock(
        return_value=OrchestrationResponse(
            request_id="req-comp-1",
            status=ResultStatus.COMPLETED,
            result={
                "estimates": [],
                "performance_evidence_count": 1,
                "required_knowledge": {"tasks": []},
            },
        )
    )
    service = TutorChatService(
        mint_client_factory=FakeMint,
        ai_client_factory=lambda: ai,
        handoff_available=lambda: True,
    )
    user = CurrentUser(user_id="kc-student-1", role=UserRole.STUDENT)
    result = await service.estimate_competency(user, TutorCompetencyRequest())

    ai.orchestrate.assert_awaited_once()
    args, kwargs = ai.orchestrate.await_args
    assert args[0].action == TUTOR_COMPETENCY_ACTION
    assert args[0].student_id == PP1_DEFAULT_STUDENT_ID
    assert FAKE_TOKEN not in str(args[0].model_dump(mode="json"))
    assert kwargs == {"tutor_access_token": FAKE_TOKEN}
    assert result.status is ResultStatus.COMPLETED
    assert result.result["performance_evidence_count"] == 1


@pytest.mark.asyncio
async def test_mint_uses_settings_issuer_and_passes_tutor_token_only_as_kwarg(monkeypatch):
    from app.modules.tutor import service as tutor_service

    monkeypatch.setattr(tutor_service.settings, "KEYCLOAK_SERVER_URL", "http://localhost:8000/auth")
    monkeypatch.setattr(tutor_service.settings, "KEYCLOAK_REALM", "mentor")

    captured: dict = {}

    class FakeMint:
        async def mint_tutor_access_token(self, *, issuer, subject):
            captured["issuer"] = issuer
            captured["subject"] = subject
            return TutorAccessToken(
                access_token=FAKE_TOKEN,
                token_type="Bearer",
                expires_in=300,
                expires_at=1,
                resource="http://slap.test/mcp",
            )

    ai = MagicMock()
    ai.orchestrate = AsyncMock(
        return_value=OrchestrationResponse(
            request_id="req-1",
            status=ResultStatus.UNAVAILABLE,
        )
    )
    service = TutorChatService(
        mint_client_factory=FakeMint,
        ai_client_factory=lambda: ai,
        handoff_available=lambda: True,
    )
    user = CurrentUser(user_id="kc-student-1", role=UserRole.STUDENT)

    result = await service.chat(user, TutorChatRequest(message="Hi"))

    assert captured["issuer"] == tutor_service.settings.keycloak_issuer
    assert captured["subject"] == "kc-student-1"
    ai.orchestrate.assert_awaited_once()
    args, kwargs = ai.orchestrate.await_args
    assert args[0].action == "tutor.chat"
    assert args[0].input == {"message": "Hi"}
    assert FAKE_TOKEN not in str(args[0].model_dump(mode="json"))
    assert kwargs == {"tutor_access_token": FAKE_TOKEN}
    assert result.status is ResultStatus.UNAVAILABLE
    assert FAKE_TOKEN not in result.model_dump_json()


@pytest.mark.parametrize(
    ("exc", "status", "detail_fragment"),
    [
        (SlapTutorMintIdentityNotFoundError("missing"), 409, "not linked"),
        (SlapTutorMintConfigError("cfg"), 503, "unavailable"),
        (SlapTutorMintAuthError("auth"), 503, "unavailable"),
        (SlapTutorMintUnavailableError("down"), 503, "unavailable"),
        (SlapTutorMintTimeoutError("timeout"), 503, "unavailable"),
        (SlapTutorMintNetworkError("net"), 503, "unavailable"),
        (SlapTutorMintProtocolError("bad"), 502, "failed"),
    ],
)
def test_mint_error_mapping_is_sanitized(exc, status, detail_fragment):
    code, detail = map_tutor_service_error(exc)
    assert code == status
    assert detail_fragment in detail
    assert FAKE_TOKEN not in detail
    assert FAKE_MINT_SECRET not in detail
    assert "Bearer" not in detail


def test_unlinked_identity_maps_to_409_via_route(client):
    class FakeMint:
        async def mint_tutor_access_token(self, *, issuer, subject):
            raise SlapTutorMintIdentityNotFoundError("not found")

    service = TutorChatService(
        mint_client_factory=FakeMint,
        handoff_available=lambda: True,
    )
    app.dependency_overrides[get_tutor_chat_service] = lambda: service

    response = client.post(
        "/api/v1/tutor/chat",
        json={"message": "Hello"},
        headers=auth_header(make_token()),
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "Tutor identity is not linked"
    assert FAKE_TOKEN not in response.text


@pytest.mark.parametrize(
    ("exc", "expected_status"),
    [
        (SlapTutorMintConfigError("x"), 503),
        (SlapTutorMintAuthError("x"), 503),
        (SlapTutorMintTimeoutError("x"), 503),
        (SlapTutorMintUnavailableError("x"), 503),
        (SlapTutorMintNetworkError("x"), 503),
        (SlapTutorMintProtocolError("x"), 502),
    ],
)
def test_mint_failures_map_via_route(client, exc, expected_status):
    class FakeMint:
        async def mint_tutor_access_token(self, *, issuer, subject):
            raise exc

    service = TutorChatService(
        mint_client_factory=FakeMint,
        handoff_available=lambda: True,
    )
    app.dependency_overrides[get_tutor_chat_service] = lambda: service

    response = client.post(
        "/api/v1/tutor/chat",
        json={"message": "Hello"},
        headers=auth_header(make_token()),
    )
    assert response.status_code == expected_status
    body = response.text
    assert FAKE_TOKEN not in body
    assert FAKE_MINT_SECRET not in body
    assert "Authorization" not in body


def test_public_route_fails_closed_before_mint_when_handoff_unavailable(client):
    mint = MagicMock()
    mint.mint_tutor_access_token = AsyncMock()
    ai = MagicMock()
    ai.orchestrate = AsyncMock()
    service = TutorChatService(
        mint_client_factory=lambda: mint,
        ai_client_factory=lambda: ai,
        handoff_available=lambda: False,
    )
    app.dependency_overrides[get_tutor_chat_service] = lambda: service

    response = client.post(
        "/api/v1/tutor/chat",
        json={"message": "Hello"},
        headers=auth_header(make_token()),
    )
    assert response.status_code == 503
    assert response.json()["detail"] == TUTOR_UNAVAILABLE_DETAIL
    mint.mint_tutor_access_token.assert_not_called()
    ai.orchestrate.assert_not_called()
