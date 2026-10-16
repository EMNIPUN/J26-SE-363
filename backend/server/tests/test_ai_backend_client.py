import json

import httpx
import pytest
from shared.contracts import (
    OrchestrationRequest,
    RequesterContext,
    ResultStatus,
    UserRole,
)

from app.clients.ai_backend import (
    AIBackendClient,
    AIBackendConfigError,
    AIBackendError,
    TUTOR_ACCESS_TOKEN_HEADER,
    get_ai_backend_client,
)
from app.core.config import settings

INTERNAL = "unit-test-ai-backend-internal-token-32c"
TUTOR_TOKEN = "opaque-tutor-access-token-for-unit-tests-only"

REQUEST = OrchestrationRequest(
    request_id="req-001",
    requester=RequesterContext(user_id="kc-123", role=UserRole.STUDENT),
    action="tutor.chat",
    student_id="ST001",
    input={"message": "Explain JWT"},
)


def client_with(handler, *, internal_token: str = INTERNAL) -> AIBackendClient:
    return AIBackendClient(
        "http://ai-backend",
        5,
        internal_token,
        transport=httpx.MockTransport(handler),
    )


@pytest.mark.asyncio
async def test_sends_orchestration_request_with_service_auth_and_parses_response():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/api/v1/orchestration"
        assert request.headers.get("Authorization") == f"Bearer {INTERNAL}"
        assert TUTOR_ACCESS_TOKEN_HEADER not in request.headers
        sent = json.loads(request.content)
        assert sent["request_id"] == "req-001"
        assert sent["requester"] == {"user_id": "kc-123", "role": "student"}
        assert TUTOR_TOKEN not in json.dumps(sent)
        assert INTERNAL not in json.dumps(sent)
        return httpx.Response(200, json={"request_id": sent["request_id"], "status": "unavailable"})

    response = await client_with(handler).orchestrate(REQUEST)

    assert response.request_id == "req-001"
    assert response.status is ResultStatus.UNAVAILABLE


@pytest.mark.asyncio
async def test_tutor_token_sent_only_in_dedicated_header():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("Authorization") == f"Bearer {INTERNAL}"
        assert request.headers.get(TUTOR_ACCESS_TOKEN_HEADER) == TUTOR_TOKEN
        sent = json.loads(request.content)
        dumped = json.dumps(sent)
        assert TUTOR_TOKEN not in dumped
        assert "accessToken" not in dumped
        assert INTERNAL not in dumped
        return httpx.Response(200, json={"request_id": sent["request_id"], "status": "unavailable"})

    await client_with(handler).orchestrate(REQUEST, tutor_access_token=TUTOR_TOKEN)


@pytest.mark.asyncio
async def test_blank_tutor_token_rejected_before_request():
    called = False

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal called
        called = True
        return httpx.Response(200, json={"request_id": "x", "status": "unavailable"})

    with pytest.raises(AIBackendError, match="tutor_access_token"):
        await client_with(handler).orchestrate(REQUEST, tutor_access_token="  ")
    assert called is False


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "handler",
    [
        lambda request: httpx.Response(500, json={"detail": "boom"}),
        lambda request: httpx.Response(200, json={"status": "completed"}),
        lambda request: httpx.Response(200, text="not json"),
    ],
    ids=["http-error", "missing-request-id", "not-json"],
)
async def test_bad_ai_backend_responses_raise_ai_backend_error(handler):
    with pytest.raises(AIBackendError) as raised:
        await client_with(handler).orchestrate(REQUEST)
    assert INTERNAL not in str(raised.value)
    assert TUTOR_TOKEN not in str(raised.value)


@pytest.mark.asyncio
async def test_unreachable_ai_backend_raises_ai_backend_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    with pytest.raises(AIBackendError, match="request failed"):
        await client_with(handler).orchestrate(REQUEST)


def test_constructor_requires_internal_token():
    with pytest.raises(AIBackendConfigError, match="AI_BACKEND_INTERNAL_TOKEN"):
        AIBackendClient("http://ai-backend", 5, "")


def test_default_client_requires_configured_internal_token(monkeypatch):
    monkeypatch.setattr(settings, "AI_BACKEND_INTERNAL_TOKEN", None)
    with pytest.raises(AIBackendConfigError, match="not configured"):
        get_ai_backend_client()


def test_default_client_uses_settings(monkeypatch):
    monkeypatch.setattr(settings, "AI_BACKEND_INTERNAL_TOKEN", INTERNAL)
    client = get_ai_backend_client()

    assert client._base_url == settings.AI_BACKEND_URL.rstrip("/")
    assert client._timeout == settings.AI_BACKEND_TIMEOUT_SECONDS
    assert client._internal_token == INTERNAL
