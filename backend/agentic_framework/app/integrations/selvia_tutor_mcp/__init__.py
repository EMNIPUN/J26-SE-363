"""SELVIA Learning Assessment Platform MCP client for the Adaptive AI Tutor.

This package talks to the platform Streamable HTTP MCP endpoint (`/mcp`).
Live authentication requires an injected `TokenProvider` that returns a short-lived
tutor access token. Token minting is intentionally not implemented here.
"""

from app.integrations.selvia_tutor_mcp.client import (
    DEFAULT_ACTIVITY_LIMIT,
    MAX_ACTIVITY_LIMIT,
    TOOL_GET_CURRENT_EVIDENCE,
    TOOL_GET_LEARNING_ACTIVITIES,
    SelviaTutorMcpClient,
)
from app.integrations.selvia_tutor_mcp.errors import (
    SelviaMcpAuthError,
    SelviaMcpEnvelopeError,
    SelviaMcpError,
    SelviaMcpRecordError,
    SelviaMcpToolError,
    SelviaMcpTransportError,
    SelviaMcpValidationError,
)
from app.integrations.selvia_tutor_mcp.token_provider import (
    TokenProvider,
    UnconfiguredTokenProvider,
)

__all__ = [
    "DEFAULT_ACTIVITY_LIMIT",
    "MAX_ACTIVITY_LIMIT",
    "TOOL_GET_CURRENT_EVIDENCE",
    "TOOL_GET_LEARNING_ACTIVITIES",
    "SelviaMcpAuthError",
    "SelviaMcpEnvelopeError",
    "SelviaMcpError",
    "SelviaMcpRecordError",
    "SelviaMcpToolError",
    "SelviaMcpTransportError",
    "SelviaMcpValidationError",
    "SelviaTutorMcpClient",
    "TokenProvider",
    "UnconfiguredTokenProvider",
]
