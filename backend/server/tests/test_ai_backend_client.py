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
    AIBackendError,
    get_ai_backend_client,
)
from app.core.config import settings

REQUEST = OrchestrationRequest(
    request_id="req-001",
    requester=RequesterContext(user_id="kc-123", role=UserRole.STUDENT),
    action="tutor.chat",
    student_id="ST001",
    input={"message": "Explain JWT"},
)


def client_with(handler) -> AIBackendClient:
    return AIBackendClient("http://ai-backend", 5, transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_sends_orchestration_request_and_parses_response():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/api/v1/orchestration"
        sent = json.loads(request.content)
        assert sent["request_id"] == "req-001"
        assert sent["requester"] == {"user_id": "kc-123", "role": "student"}
        return httpx.Response(200, json={"request_id": sent["request_id"], "status": "unavailable"})

    response = await client_with(handler).orchestrate(REQUEST)

    assert response.request_id == "req-001"
    assert response.status is ResultStatus.UNAVAILABLE


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
    with pytest.raises(AIBackendError):
        await client_with(handler).orchestrate(REQUEST)


@pytest.mark.asyncio
async def test_unreachable_ai_backend_raises_ai_backend_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    with pytest.raises(AIBackendError, match="request failed"):
        await client_with(handler).orchestrate(REQUEST)


def test_default_client_uses_settings():
    client = get_ai_backend_client()

    assert client._base_url == settings.AI_BACKEND_URL
    assert client._timeout == settings.AI_BACKEND_TIMEOUT_SECONDS


@pytest.mark.asyncio
async def test_sends_the_internal_token_when_configured():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["token"] = request.headers.get("x-internal-token")
        return httpx.Response(200, json={"request_id": "req-001", "status": "unavailable"})

    client = AIBackendClient(
        "http://ai-backend", 5, transport=httpx.MockTransport(handler), internal_token="s3cret"
    )
    await client.orchestrate(REQUEST)

    assert seen["token"] == "s3cret"


@pytest.mark.asyncio
async def test_omits_the_internal_token_header_when_not_configured():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["has_header"] = "x-internal-token" in request.headers
        return httpx.Response(200, json={"request_id": "req-001", "status": "unavailable"})

    await client_with(handler).orchestrate(REQUEST)

    assert seen["has_header"] is False


def test_default_client_sends_the_configured_internal_token(monkeypatch):
    monkeypatch.setattr(settings, "AI_BACKEND_INTERNAL_TOKEN", "from-settings")

    assert get_ai_backend_client()._internal_token == "from-settings"
