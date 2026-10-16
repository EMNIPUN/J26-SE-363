"""Tutor access-token injection for the SELVIA MCP client.

The platform signs short-lived tutor JWTs with ``MCP_TUTOR_TOKEN_SECRET``. That secret
must never live in this Python project. Callers inject a ``TokenProvider`` that obtains
an opaque bearer token through an explicitly configured, secure provisioning path once
one exists on the platform.
"""

from typing import Protocol, runtime_checkable

from app.integrations.selvia_tutor_mcp.errors import SelviaMcpAuthError


@runtime_checkable
class TokenProvider(Protocol):
    """Supplies a short-lived opaque tutor access token for MCP Bearer auth."""

    async def get_access_token(self) -> str:
        """Return a tutor access token string. Never log or print the value."""


class UnconfiguredTokenProvider:
    """Default provider that blocks live MCP auth until provisioning is designed."""

    async def get_access_token(self) -> str:
        raise SelviaMcpAuthError(
            "Tutor access token provisioning is not configured. "
            "Inject a TokenProvider that returns a short-lived tutor token once a "
            "secure platform issuance path exists. Do not mint tokens in this client "
            "and do not use MCP_TUTOR_TOKEN_SECRET or a login JWT here."
        )
