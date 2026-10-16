"""Unit tests for SlapTutorMintClient (httpx.MockTransport; no network or DB)."""

from __future__ import annotations

import inspect
import json

import httpx
import pytest

from app.clients.slap_tutor_mint import (
    MINT_PATH,
    SlapTutorMintAuthError,
    SlapTutorMintClient,
    SlapTutorMintConfigError,
    SlapTutorMintIdentityNotFoundError,
    SlapTutorMintNetworkError,
    SlapTutorMintProtocolError,
    SlapTutorMintTimeoutError,
    SlapTutorMintUnavailableError,
    TutorAccessToken,
    get_slap_tutor_mint_client,
)
from app.core.config import Settings

FAKE_BASE = "http://slap.test"
FAKE_MINT_TOKEN = "unit-test-internal-mint-token-not-real-32chars"
FAKE_ISSUER = "http://localhost:8000/auth/realms/mentor"
FAKE_SUBJECT = "kc-subject-abc"
FAKE_ACCESS_TOKEN = "opaque-tutor-access-token-for-unit-tests-only"
FAKE_RESOURCE = "http://slap.test/mcp"

SUCCESS_BODY = {
    "success": True,
    "data": {
        "accessToken": FAKE_ACCESS_TOKEN,
        "tokenType": "Bearer",
        "expiresIn": 300,
        "expiresAt": 1_700_000_0300,
        "resource": FAKE_RESOURCE,
    },
}


def client_with(handler, *, mint_token: str = FAKE_MINT_TOKEN) -> SlapTutorMintClient:
    return SlapTutorMintClient(
        FAKE_BASE,
        mint_token,
        5.0,
        transport=httpx.MockTransport(handler),
    )


def _assert_message_has_no_secrets(message: str) -> None:
    assert FAKE_MINT_TOKEN not in message
    assert FAKE_ACCESS_TOKEN not in message
    assert "Authorization" not in message
    assert "Bearer " not in message


@pytest.mark.asyncio
async def test_posts_to_exact_mint_path_with_issuer_and_subject_only():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["path"] = request.url.path
        captured["auth"] = request.headers.get("Authorization")
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json=SUCCESS_BODY)

    result = await client_with(handler).mint_tutor_access_token(
        issuer=FAKE_ISSUER,
        subject=FAKE_SUBJECT,
    )

    assert captured["method"] == "POST"
    assert captured["path"] == MINT_PATH
    assert captured["path"] == "/api/v1/internal/tutor-access-tokens"
    assert captured["auth"] == f"Bearer {FAKE_MINT_TOKEN}"
    assert captured["body"] == {"issuer": FAKE_ISSUER, "subject": FAKE_SUBJECT}
    assert "expiresInSeconds" not in captured["body"]
    assert "scopes" not in captured["body"]
    assert "studentId" not in captured["body"]
    assert "userId" not in captured["body"]

    assert isinstance(result, TutorAccessToken)
    assert result.access_token == FAKE_ACCESS_TOKEN
    assert result.token_type == "Bearer"
    assert result.expires_in == 300
    assert result.expires_at == 1_700_000_0300
    assert result.resource == FAKE_RESOURCE


def test_mint_method_rejects_student_id_and_scopes_kwargs():
    sig = inspect.signature(SlapTutorMintClient.mint_tutor_access_token)
    assert list(sig.parameters) == ["self", "issuer", "subject"]
    assert "student_id" not in sig.parameters
    assert "studentId" not in sig.parameters
    assert "scopes" not in sig.parameters
    assert "user_id" not in sig.parameters


@pytest.mark.asyncio
async def test_blank_issuer_or_subject_fails_closed_before_request():
    called = False

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal called
        called = True
        return httpx.Response(200, json=SUCCESS_BODY)

    client = client_with(handler)
    with pytest.raises(SlapTutorMintConfigError, match="issuer"):
        await client.mint_tutor_access_token(issuer="  ", subject=FAKE_SUBJECT)
    with pytest.raises(SlapTutorMintConfigError, match="subject"):
        await client.mint_tutor_access_token(issuer=FAKE_ISSUER, subject="")
    assert called is False


def test_constructor_fails_closed_on_missing_config():
    with pytest.raises(SlapTutorMintConfigError, match="SLAP_BASE_URL"):
        SlapTutorMintClient("", FAKE_MINT_TOKEN, 5.0)
    with pytest.raises(SlapTutorMintConfigError, match="INTERNAL_TUTOR_MINT_TOKEN"):
        SlapTutorMintClient(FAKE_BASE, "  ", 5.0)
    with pytest.raises(SlapTutorMintConfigError, match="TIMEOUT"):
        SlapTutorMintClient(FAKE_BASE, FAKE_MINT_TOKEN, 0)


def test_settings_blank_slap_values_are_unset():
    cfg = Settings(
        SLAP_BASE_URL="   ",
        INTERNAL_TUTOR_MINT_TOKEN="",
        _env_file=None,
    )
    assert cfg.SLAP_BASE_URL is None
    assert cfg.INTERNAL_TUTOR_MINT_TOKEN is None
    assert cfg.slap_tutor_mint_configured is False


def test_get_slap_tutor_mint_client_fails_closed_when_unconfigured(monkeypatch):
    from app.clients import slap_tutor_mint as mint_mod

    monkeypatch.setattr(mint_mod.settings, "SLAP_BASE_URL", None)
    monkeypatch.setattr(mint_mod.settings, "INTERNAL_TUTOR_MINT_TOKEN", None)
    with pytest.raises(SlapTutorMintConfigError, match="not configured"):
        get_slap_tutor_mint_client()


def test_get_slap_tutor_mint_client_uses_settings_when_configured(monkeypatch):
    from app.clients import slap_tutor_mint as mint_mod

    monkeypatch.setattr(mint_mod.settings, "SLAP_BASE_URL", FAKE_BASE)
    monkeypatch.setattr(mint_mod.settings, "INTERNAL_TUTOR_MINT_TOKEN", FAKE_MINT_TOKEN)
    monkeypatch.setattr(mint_mod.settings, "SLAP_TUTOR_MINT_TIMEOUT_SECONDS", 7.5)
    client = get_slap_tutor_mint_client()
    assert client._base_url == FAKE_BASE
    assert client._timeout == 7.5
    assert client._mint_token == FAKE_MINT_TOKEN


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "exc_type"),
    [
        (401, SlapTutorMintAuthError),
        (403, SlapTutorMintAuthError),
        (404, SlapTutorMintIdentityNotFoundError),
        (503, SlapTutorMintUnavailableError),
        (500, SlapTutorMintProtocolError),
        (422, SlapTutorMintProtocolError),
    ],
)
async def test_http_error_status_mapping(status, exc_type):
    leaky_body = {
        "detail": f"leak {FAKE_MINT_TOKEN} {FAKE_ACCESS_TOKEN}",
        "accessToken": FAKE_ACCESS_TOKEN,
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json=leaky_body)

    with pytest.raises(exc_type) as raised:
        await client_with(handler).mint_tutor_access_token(
            issuer=FAKE_ISSUER,
            subject=FAKE_SUBJECT,
        )
    _assert_message_has_no_secrets(str(raised.value))


@pytest.mark.asyncio
async def test_timeout_raises_sanitized_timeout_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("read timed out", request=request)

    with pytest.raises(SlapTutorMintTimeoutError) as raised:
        await client_with(handler).mint_tutor_access_token(
            issuer=FAKE_ISSUER,
            subject=FAKE_SUBJECT,
        )
    _assert_message_has_no_secrets(str(raised.value))
    assert FAKE_MINT_TOKEN not in str(raised.value.__cause__)


@pytest.mark.asyncio
async def test_network_failure_raises_sanitized_network_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    with pytest.raises(SlapTutorMintNetworkError) as raised:
        await client_with(handler).mint_tutor_access_token(
            issuer=FAKE_ISSUER,
            subject=FAKE_SUBJECT,
        )
    _assert_message_has_no_secrets(str(raised.value))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "body",
    [
        "not-json",
        {"success": True},
        {"success": True, "data": {"accessToken": FAKE_ACCESS_TOKEN}},
        {
            "success": False,
            "data": {
                "accessToken": FAKE_ACCESS_TOKEN,
                "tokenType": "Bearer",
                "expiresIn": 300,
                "expiresAt": 1,
                "resource": FAKE_RESOURCE,
            },
        },
        {
            "accessToken": FAKE_ACCESS_TOKEN,
            "tokenType": "Bearer",
            "expiresIn": 300,
            "expiresAt": 1,
            "resource": FAKE_RESOURCE,
        },
    ],
    ids=[
        "not-json",
        "missing-data",
        "incomplete-data",
        "success-false",
        "unwrapped-flat-body",
    ],
)
async def test_malformed_or_unexpected_response_raises_protocol_error(body):
    def handler(request: httpx.Request) -> httpx.Response:
        if body == "not-json":
            return httpx.Response(200, text="not-json")
        return httpx.Response(200, json=body)

    with pytest.raises(SlapTutorMintProtocolError) as raised:
        await client_with(handler).mint_tutor_access_token(
            issuer=FAKE_ISSUER,
            subject=FAKE_SUBJECT,
        )
    _assert_message_has_no_secrets(str(raised.value))


@pytest.mark.asyncio
async def test_bearer_header_uses_configured_token_without_logging_it_in_exceptions():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == f"Bearer {FAKE_MINT_TOKEN}"
        return httpx.Response(401, json={"error": FAKE_MINT_TOKEN})

    with pytest.raises(SlapTutorMintAuthError) as raised:
        await client_with(handler).mint_tutor_access_token(
            issuer=FAKE_ISSUER,
            subject=FAKE_SUBJECT,
        )
    _assert_message_has_no_secrets(str(raised.value))
