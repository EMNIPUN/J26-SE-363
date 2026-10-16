"""Typed errors for the SELVIA tutor MCP integration."""


class SelviaMcpError(Exception):
    """Base error for SELVIA platform MCP client failures."""


class SelviaMcpAuthError(SelviaMcpError):
    """Authentication failed or a tutor access token is unavailable."""


class SelviaMcpTransportError(SelviaMcpError):
    """MCP transport, session, or HTTP connectivity failed."""


class SelviaMcpToolError(SelviaMcpError):
    """The MCP tool returned a Contract C failure envelope or isError result."""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


class SelviaMcpEnvelopeError(SelviaMcpError):
    """The MCP tool result could not be parsed as a Contract C envelope."""


class SelviaMcpRecordError(SelviaMcpError):
    """A record in a successful envelope failed tutor schema validation."""


class SelviaMcpValidationError(SelviaMcpError):
    """Client-side filter or argument validation failed before the tool call."""
