"""Unit tests for SelviaTutorMcpClient (mocked MCP session; no live platform)."""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

import pytest
from mcp.types import CallToolResult, TextContent

from app.agents.adaptive_tutor.tests.fixtures.evidence_data import (
    LEARNING_BEHAVIOUR,
    PERFORMANCE_EVIDENCE,
)
from app.integrations.selvia_tutor_mcp import (
    DEFAULT_ACTIVITY_LIMIT,
    TOOL_GET_CURRENT_EVIDENCE,
    TOOL_GET_LEARNING_ACTIVITIES,
    SelviaMcpAuthError,
    SelviaMcpEnvelopeError,
    SelviaMcpRecordError,
    SelviaMcpToolError,
    SelviaMcpTransportError,
    SelviaMcpValidationError,
    SelviaTutorMcpClient,
    UnconfiguredTokenProvider,
)
from mcp import MCPError


class StaticTokenProvider:
    def __init__(self, token: str = "test-tutor-token"):
        self.token = token
        self.calls = 0

    async def get_access_token(self) -> str:
        self.calls += 1
        return self.token


class RecordingSession:
    def __init__(self, result: CallToolResult | Exception):
        self._result = result
        self.calls: list[tuple[str, dict[str, Any] | None]] = []

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> CallToolResult:
        self.calls.append((name, arguments))
        if isinstance(self._result, Exception):
            raise self._result
        return self._result


def _tool_result(
    envelope: dict[str, Any] | None,
    *,
    is_error: bool = False,
    structured: bool = True,
    text: str | None = None,
) -> CallToolResult:
    content: list[TextContent] = []
    if text is not None:
        content.append(TextContent(type="text", text=text))
    elif envelope is not None:
        content.append(TextContent(type="text", text=json.dumps(envelope)))

    kwargs: dict[str, Any] = {"content": content, "isError": is_error}
    if structured:
        kwargs["structuredContent"] = envelope
    return CallToolResult(**kwargs)


def _client_with_session(
    session: RecordingSession,
    *,
    token_provider: Any | None = None,
    captured: dict[str, Any] | None = None,
) -> SelviaTutorMcpClient:
    store = captured if captured is not None else {}

    @asynccontextmanager
    async def factory(mcp_url: str, access_token: str):
        store["mcp_url"] = mcp_url
        store["access_token"] = access_token
        yield session

    return SelviaTutorMcpClient(
        "http://127.0.0.1:5000/mcp",
        token_provider if token_provider is not None else StaticTokenProvider(),
        session_factory=factory,
    )


@pytest.mark.asyncio
async def test_get_current_evidence_success_maps_fixtures():
    envelope = {"ok": True, "data": {"records": PERFORMANCE_EVIDENCE}}
    session = RecordingSession(_tool_result(envelope))
    client = _client_with_session(session)

    records = await client.get_current_evidence(
        course_id="course-101",
        concept_id="concept-101",
    )

    assert len(records) == 4
    assert records[0].id == "evidence-001"
    assert records[0].course_id == "course-101"
    assert records[2].score is None
    assert records[3].concept_id is None
    assert session.calls == [
        (
            TOOL_GET_CURRENT_EVIDENCE,
            {"courseId": "course-101", "conceptId": "concept-101"},
        )
    ]


@pytest.mark.asyncio
async def test_get_current_evidence_empty_records():
    session = RecordingSession(_tool_result({"ok": True, "data": {"records": []}}))
    client = _client_with_session(session)

    records = await client.get_current_evidence()

    assert records == []
    assert session.calls == [(TOOL_GET_CURRENT_EVIDENCE, None)]


@pytest.mark.asyncio
async def test_get_learning_activities_success_and_default_limit():
    envelope = {"ok": True, "data": {"records": LEARNING_BEHAVIOUR}}
    session = RecordingSession(_tool_result(envelope))
    client = _client_with_session(session)

    records = await client.get_learning_activities(
        activity_type="LESSON_VIEWED",
        target_type="LESSON",
    )

    assert len(records) == 2
    assert records[0].activity_type == "LESSON_VIEWED"
    assert records[0].duration_seconds is None
    assert records[1].duration_seconds == 240
    assert session.calls[0][0] == TOOL_GET_LEARNING_ACTIVITIES
    assert session.calls[0][1] == {
        "limit": DEFAULT_ACTIVITY_LIMIT,
        "activityType": "LESSON_VIEWED",
        "targetType": "LESSON",
    }


@pytest.mark.asyncio
async def test_optional_filters_and_datetime_serialization():
    session = RecordingSession(_tool_result({"ok": True, "data": {"records": []}}))
    client = _client_with_session(session)
    occurred_from = datetime(2026, 10, 15, 9, 0, tzinfo=UTC)

    await client.get_learning_activities(
        course_id="course-101",
        occurred_from=occurred_from,
        occurred_to="2026-10-15T12:00:00+00:00",
        limit=10,
    )

    assert session.calls[0][1] == {
        "limit": 10,
        "courseId": "course-101",
        "occurredFrom": occurred_from.isoformat(),
        "occurredTo": "2026-10-15T12:00:00+00:00",
    }


@pytest.mark.asyncio
async def test_invalid_limit_rejected_before_tool_call():
    session = RecordingSession(_tool_result({"ok": True, "data": {"records": []}}))
    client = _client_with_session(session)

    with pytest.raises(SelviaMcpValidationError):
        await client.get_learning_activities(limit=0)
    with pytest.raises(SelviaMcpValidationError):
        await client.get_learning_activities(limit=201)
    assert session.calls == []


@pytest.mark.asyncio
async def test_malformed_envelope_raises():
    session = RecordingSession(_tool_result({"ok": True, "data": {"notRecords": []}}))
    client = _client_with_session(session)

    with pytest.raises(SelviaMcpEnvelopeError):
        await client.get_current_evidence()


@pytest.mark.asyncio
async def test_tool_error_envelope_raises_typed_error():
    session = RecordingSession(
        _tool_result(
            {
                "ok": False,
                "error": {
                    "code": "FORBIDDEN",
                    "message": "You do not have permission to perform this action.",
                },
            },
            is_error=True,
        )
    )
    client = _client_with_session(session)

    with pytest.raises(SelviaMcpToolError) as exc_info:
        await client.get_current_evidence()

    assert exc_info.value.code == "FORBIDDEN"


@pytest.mark.asyncio
async def test_is_error_without_envelope_raises_tool_error():
    session = RecordingSession(
        CallToolResult(
            content=[TextContent(type="text", text="not-json")],
            isError=True,
        )
    )
    client = _client_with_session(session)

    with pytest.raises(SelviaMcpToolError) as exc_info:
        await client.get_learning_activities()

    assert exc_info.value.code == "INTERNAL_ERROR"


@pytest.mark.asyncio
async def test_invalid_record_raises_record_error():
    bad = {**PERFORMANCE_EVIDENCE[0], "status": "NOT_A_STATUS"}
    session = RecordingSession(_tool_result({"ok": True, "data": {"records": [bad]}}))
    client = _client_with_session(session)

    with pytest.raises(SelviaMcpRecordError):
        await client.get_current_evidence()


@pytest.mark.asyncio
async def test_token_provider_injected_into_session_factory():
    provider = StaticTokenProvider("opaque-tutor-token")
    captured: dict[str, Any] = {}
    session = RecordingSession(_tool_result({"ok": True, "data": {"records": []}}))
    client = _client_with_session(
        session,
        token_provider=provider,
        captured=captured,
    )

    await client.get_current_evidence()

    assert provider.calls == 1
    assert captured["mcp_url"] == "http://127.0.0.1:5000/mcp"
    assert captured["access_token"] == "opaque-tutor-token"


@pytest.mark.asyncio
async def test_unconfigured_token_provider_blocks_live_auth():
    client = SelviaTutorMcpClient(
        "http://127.0.0.1:5000/mcp",
        UnconfiguredTokenProvider(),
    )

    with pytest.raises(SelviaMcpAuthError):
        await client.get_current_evidence()


@pytest.mark.asyncio
async def test_empty_token_from_provider_raises_auth_error():
    class EmptyTokenProvider:
        async def get_access_token(self) -> str:
            return "   "

    session = RecordingSession(_tool_result({"ok": True, "data": {"records": []}}))
    client = _client_with_session(session, token_provider=EmptyTokenProvider())

    with pytest.raises(SelviaMcpAuthError):
        await client.get_current_evidence()
    assert session.calls == []


@pytest.mark.asyncio
async def test_transport_failure_from_session_factory_is_typed():
    @asynccontextmanager
    async def factory(mcp_url: str, access_token: str):
        raise SelviaMcpTransportError("MCP protocol error while connecting.")
        yield  # pragma: no cover

    client = SelviaTutorMcpClient(
        "http://127.0.0.1:5000/mcp",
        StaticTokenProvider(),
        session_factory=factory,
    )

    with pytest.raises(SelviaMcpTransportError):
        await client.get_current_evidence()


@pytest.mark.asyncio
async def test_call_tool_exception_mapped_to_transport_error():
    session = RecordingSession(MCPError(-32000, "connection reset"))
    client = _client_with_session(session)

    with pytest.raises(SelviaMcpTransportError):
        await client.get_current_evidence()


@pytest.mark.asyncio
async def test_text_only_success_envelope():
    envelope = {"ok": True, "data": {"records": PERFORMANCE_EVIDENCE[:1]}}
    session = RecordingSession(
        _tool_result(None, structured=False, text=json.dumps(envelope))
    )
    client = _client_with_session(session)

    records = await client.get_current_evidence()

    assert len(records) == 1
    assert records[0].percentage == 40


@pytest.mark.asyncio
async def test_blank_mcp_url_rejected():
    with pytest.raises(SelviaMcpValidationError):
        SelviaTutorMcpClient("  ")
