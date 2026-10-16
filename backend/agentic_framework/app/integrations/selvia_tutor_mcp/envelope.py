"""Parse Contract C envelopes from MCP CallToolResult payloads."""

from __future__ import annotations

import json
from typing import Any

from mcp.types import CallToolResult, TextContent

from app.integrations.selvia_tutor_mcp.errors import (
    SelviaMcpEnvelopeError,
    SelviaMcpToolError,
)

KNOWN_ERROR_CODES = frozenset(
    {
        "VALIDATION_ERROR",
        "UNAUTHENTICATED",
        "FORBIDDEN",
        "DEPENDENCY_UNAVAILABLE",
        "INTERNAL_ERROR",
    }
)


def extract_envelope(result: CallToolResult) -> dict[str, Any]:
    """Return the Contract C envelope from structuredContent and/or text content.

    Prefers ``structured_content`` when it is a dict. Falls back to the first
    ``TextContent`` part whose ``text`` parses as a JSON object. Does not invent
    an envelope when neither representation is usable.
    """
    structured = result.structured_content
    if isinstance(structured, dict):
        return structured

    if structured is not None:
        raise SelviaMcpEnvelopeError(
            "MCP tool structuredContent must be a JSON object when present."
        )

    text_blob = _first_json_object_text(result)
    if text_blob is None:
        raise SelviaMcpEnvelopeError(
            "MCP tool result has neither a structuredContent object nor JSON text content."
        )

    try:
        parsed = json.loads(text_blob)
    except json.JSONDecodeError as exc:
        raise SelviaMcpEnvelopeError(
            "MCP tool text content is not valid JSON."
        ) from exc

    if not isinstance(parsed, dict):
        raise SelviaMcpEnvelopeError(
            "MCP tool text content must decode to a JSON object."
        )
    return parsed


def require_success_records(envelope: dict[str, Any], *, is_error: bool) -> list[Any]:
    """Validate a Contract C envelope and return ``data.records`` on success.

    Raises ``SelviaMcpToolError`` for ``ok: false`` (and for ``isError`` without a
    usable failure envelope). Raises ``SelviaMcpEnvelopeError`` for malformed success
    shapes. Empty ``records`` is a valid success.
    """
    if "ok" not in envelope:
        raise SelviaMcpEnvelopeError("MCP envelope is missing the required 'ok' field.")

    ok = envelope["ok"]
    if ok is False:
        raise _tool_error_from_envelope(envelope)

    if ok is not True:
        raise SelviaMcpEnvelopeError("MCP envelope 'ok' must be a boolean.")

    if is_error:
        raise SelviaMcpToolError(
            "INTERNAL_ERROR",
            "MCP tool marked isError but returned an ok:true envelope.",
        )

    data = envelope.get("data")
    if not isinstance(data, dict):
        raise SelviaMcpEnvelopeError(
            "Successful MCP envelope must include an object 'data' field."
        )

    if "records" not in data:
        raise SelviaMcpEnvelopeError(
            "Successful MCP envelope data must include a 'records' field."
        )

    records = data["records"]
    if not isinstance(records, list):
        raise SelviaMcpEnvelopeError(
            "Successful MCP envelope data.records must be an array."
        )

    return records


def _tool_error_from_envelope(envelope: dict[str, Any]) -> SelviaMcpToolError:
    error = envelope.get("error")
    if not isinstance(error, dict):
        return SelviaMcpToolError(
            "INTERNAL_ERROR",
            "MCP tool returned ok:false without a usable error object.",
        )

    code = error.get("code")
    message = error.get("message")
    if not isinstance(code, str) or not code.strip():
        code = "INTERNAL_ERROR"
    elif code not in KNOWN_ERROR_CODES:
        # Preserve unknown platform codes rather than inventing a different one.
        code = code.strip()

    if not isinstance(message, str) or not message.strip():
        message = "The MCP tool reported a failure."
    else:
        message = message.strip()

    return SelviaMcpToolError(code, message)


def _first_json_object_text(result: CallToolResult) -> str | None:
    for part in result.content or []:
        if isinstance(part, TextContent) and isinstance(part.text, str):
            stripped = part.text.strip()
            if stripped.startswith("{"):
                return part.text
    return None
