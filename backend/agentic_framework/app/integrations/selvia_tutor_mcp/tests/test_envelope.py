import json

import pytest
from mcp.types import CallToolResult, TextContent

from app.integrations.selvia_tutor_mcp.envelope import (
    extract_envelope,
    require_success_records,
)
from app.integrations.selvia_tutor_mcp.errors import (
    SelviaMcpEnvelopeError,
    SelviaMcpToolError,
)


def _result(
    *,
    structured: dict | None = None,
    text: str | None = None,
    is_error: bool = False,
    include_structured: bool = True,
) -> CallToolResult:
    content = []
    if text is not None:
        content.append(TextContent(type="text", text=text))
    kwargs: dict = {
        "content": content,
        "isError": is_error,
    }
    if include_structured:
        kwargs["structuredContent"] = structured
    return CallToolResult(**kwargs)


def test_prefers_structured_content_over_text():
    structured = {"ok": True, "data": {"records": [{"id": "from-structured"}]}}
    result = _result(
        structured=structured,
        text=json.dumps({"ok": True, "data": {"records": [{"id": "from-text"}]}}),
    )

    assert extract_envelope(result) == structured


def test_falls_back_to_text_json_when_structured_missing():
    envelope = {"ok": True, "data": {"records": []}}
    result = _result(text=json.dumps(envelope), include_structured=False)

    assert extract_envelope(result) == envelope


def test_malformed_text_json_raises():
    result = _result(text="{not-json", include_structured=False)

    with pytest.raises(SelviaMcpEnvelopeError):
        extract_envelope(result)


def test_missing_envelope_raises():
    result = _result(include_structured=False)

    with pytest.raises(SelviaMcpEnvelopeError):
        extract_envelope(result)


def test_success_empty_records():
    records = require_success_records(
        {"ok": True, "data": {"records": []}},
        is_error=False,
    )
    assert records == []


def test_ok_false_raises_tool_error():
    with pytest.raises(SelviaMcpToolError) as exc_info:
        require_success_records(
            {
                "ok": False,
                "error": {"code": "VALIDATION_ERROR", "message": "bad filters"},
            },
            is_error=True,
        )

    assert exc_info.value.code == "VALIDATION_ERROR"
    assert exc_info.value.message == "bad filters"


def test_success_without_records_raises():
    with pytest.raises(SelviaMcpEnvelopeError):
        require_success_records({"ok": True, "data": {}}, is_error=False)
