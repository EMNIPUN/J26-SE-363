"""Request-scoped short-lived tutor MCP access token for Adaptive Tutor only.

The token arrives from the Core API in ``X-SELVIA-Tutor-Token`` after service auth.
It must never be logged, persisted, or treated as the AI Backend service credential.
"""

from __future__ import annotations

from contextvars import ContextVar, Token

TUTOR_ACCESS_TOKEN_HEADER = "X-SELVIA-Tutor-Token"
TUTOR_CHAT_ACTION = "tutor.chat"

_tutor_access_token: ContextVar[str | None] = ContextVar("selvia_tutor_access_token", default=None)


def set_request_tutor_access_token(token: str) -> Token:
    """Bind the opaque tutor token to this request's context. Returns a reset token."""
    return _tutor_access_token.set(token)


def reset_request_tutor_access_token(reset_token: Token) -> None:
    _tutor_access_token.reset(reset_token)


def get_request_tutor_access_token() -> str | None:
    """Return the request-scoped tutor token, if any (never log the value)."""
    return _tutor_access_token.get()


class RequestScopedTutorTokenProvider:
    """TokenProvider that reads the request-scoped tutor access token for MCP calls."""

    async def get_access_token(self) -> str:
        from app.integrations.selvia_tutor_mcp.errors import SelviaMcpAuthError

        token = get_request_tutor_access_token()
        if not token:
            raise SelviaMcpAuthError(
                "No request-scoped tutor access token is available for this request"
            )
        return token
