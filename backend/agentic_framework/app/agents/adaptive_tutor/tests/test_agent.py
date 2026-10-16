"""Offline unit tests for AdaptiveTutorAgent (mocked MCP; no network/DB/queue)."""

from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from typing import Any
from uuid import uuid4

import pytest
from mcp.types import CallToolResult, TextContent
from shared.contracts import AgentName, AgentRequest, RequesterContext, ResultStatus, UserRole

from app.agents.adaptive_tutor.agent import AdaptiveTutorAgent
from app.agents.adaptive_tutor.tests.fixtures.evidence_data import (
    LEARNING_BEHAVIOUR,
    PERFORMANCE_EVIDENCE,
)
from app.agents.registry import build_agent_registry
from app.core.tutor_token_context import (
    RequestScopedTutorTokenProvider,
    get_request_tutor_access_token,
    reset_request_tutor_access_token,
    set_request_tutor_access_token,
)
from app.integrations.selvia_tutor_mcp import (
    TOOL_GET_CURRENT_EVIDENCE,
    TOOL_GET_LEARNING_ACTIVITIES,
    SelviaMcpAuthError,
    SelviaMcpToolError,
    SelviaMcpTransportError,
    SelviaTutorMcpClient,
)
from app.orchestrator.factory import get_orchestrator

FAKE_TOKEN = "opaque-tutor-access-token-must-never-leak-in-responses"
FAKE_TOKEN_B = "second-opaque-tutor-token-for-concurrency-tests-xx"


class RecordingSession:
    def __init__(self, results: dict[str, CallToolResult | Exception]):
        self._results = results
        self.calls: list[tuple[str, dict[str, Any] | None]] = []

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> CallToolResult:
        self.calls.append((name, arguments))
        result = self._results[name]
        if isinstance(result, Exception):
            raise result
        return result


def _tool_result(envelope: dict[str, Any]) -> CallToolResult:
    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(envelope))],
        structuredContent=envelope,
        isError=False,
    )


def _mcp_client(
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
        "http://127.0.0.1:9/mcp",
        token_provider if token_provider is not None else RequestScopedTutorTokenProvider(),
        session_factory=factory,
    )


def _request(**overrides: Any) -> AgentRequest:
    fields: dict[str, Any] = {
        "request_id": str(uuid4()),
        "action": "tutor.chat",
        "requester": RequesterContext(user_id="kc-1", role=UserRole.STUDENT),
        "input": {"message": "Explain JWT"},
    }
    fields.update(overrides)
    return AgentRequest(**fields)


def _assert_no_token_leak(payload: Any) -> None:
    text = payload if isinstance(payload, str) else json.dumps(payload, default=str)
    assert FAKE_TOKEN not in text
    assert FAKE_TOKEN_B not in text
    assert "Authorization" not in text


def test_registry_registers_only_adaptive_tutor():
    get_orchestrator.cache_clear()
    registry = build_agent_registry()
    assert set(registry.keys()) == {AgentName.ADAPTIVE_TUTOR}
    agent = registry[AgentName.ADAPTIVE_TUTOR]
    assert agent.name is AgentName.ADAPTIVE_TUTOR
    assert isinstance(agent, AdaptiveTutorAgent)


@pytest.mark.asyncio
async def test_unsupported_action_and_invalid_message():
    agent = AdaptiveTutorAgent(mcp_url=None)
    unsupported = await agent.handle(_request(action="tutor.sprint_guidance"))
    assert unsupported.status is ResultStatus.UNAVAILABLE
    _assert_no_token_leak(unsupported.model_dump(mode="json"))

    invalid = await agent.handle(_request(input={"message": "  "}))
    assert invalid.status is ResultStatus.FAILED
    assert invalid.error is not None
    assert invalid.error.code == "invalid_input"


@pytest.mark.asyncio
async def test_missing_mcp_url_returns_unavailable():
    agent = AdaptiveTutorAgent(mcp_url=None)
    reset = set_request_tutor_access_token(FAKE_TOKEN)
    try:
        response = await agent.handle(_request())
    finally:
        reset_request_tutor_access_token(reset)

    assert response.status is ResultStatus.UNAVAILABLE
    assert "not configured" in response.result["detail"]
    _assert_no_token_leak(response.model_dump(mode="json"))


@pytest.mark.asyncio
async def test_missing_request_token_fails_closed():
    session = RecordingSession({})
    agent = AdaptiveTutorAgent(mcp_client=_mcp_client(session))
    assert get_request_tutor_access_token() is None

    response = await agent.handle(_request())

    assert response.status is ResultStatus.UNAVAILABLE
    assert "token" in response.result["detail"].lower()
    assert session.calls == []
    _assert_no_token_leak(response.model_dump(mode="json"))


@pytest.mark.asyncio
async def test_mcp_success_returns_retrieved_records_only():
    session = RecordingSession(
        {
            TOOL_GET_CURRENT_EVIDENCE: _tool_result(
                {"ok": True, "data": {"records": PERFORMANCE_EVIDENCE}}
            ),
            TOOL_GET_LEARNING_ACTIVITIES: _tool_result(
                {"ok": True, "data": {"records": LEARNING_BEHAVIOUR}}
            ),
        }
    )
    captured: dict[str, Any] = {}
    agent = AdaptiveTutorAgent(
        mcp_client=_mcp_client(session, captured=captured),
    )
    reset = set_request_tutor_access_token(FAKE_TOKEN)
    try:
        response = await agent.handle(_request(student_id="student-fixture-1"))
    finally:
        reset_request_tutor_access_token(reset)

    assert response.status is ResultStatus.COMPLETED
    assert response.result["adaptive_decision"] is None
    assert response.result["student_message"] == "Explain JWT"
    assert len(response.result["performance_evidence"]) == len(PERFORMANCE_EVIDENCE)
    assert len(response.result["learning_activities"]) == len(LEARNING_BEHAVIOUR)
    # Fixture student ids differ; normalization may skip some — never invent competency.
    assert "competency_estimates" not in response.result
    assert captured["access_token"] == FAKE_TOKEN
    _assert_no_token_leak(response.model_dump(mode="json"))
    assert FAKE_TOKEN not in json.dumps(response.result)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("exc", "expected_status", "detail_fragment"),
    [
        (SelviaMcpAuthError("auth"), ResultStatus.UNAVAILABLE, "authentication"),
        (SelviaMcpTransportError("timeout"), ResultStatus.UNAVAILABLE, "unavailable"),
        (
            SelviaMcpToolError("INTERNAL_ERROR", f"leak {FAKE_TOKEN}"),
            ResultStatus.FAILED,
            None,
        ),
    ],
)
async def test_mcp_failures_are_sanitized(exc, expected_status, detail_fragment):
    session = RecordingSession(
        {
            TOOL_GET_CURRENT_EVIDENCE: exc,
            TOOL_GET_LEARNING_ACTIVITIES: _tool_result({"ok": True, "data": {"records": []}}),
        }
    )
    agent = AdaptiveTutorAgent(mcp_client=_mcp_client(session))
    reset = set_request_tutor_access_token(FAKE_TOKEN)
    try:
        response = await agent.handle(_request())
    finally:
        reset_request_tutor_access_token(reset)

    assert response.status is expected_status
    payload = response.model_dump(mode="json")
    _assert_no_token_leak(payload)
    if detail_fragment:
        assert detail_fragment in response.result["detail"].lower()
    if response.error is not None:
        assert FAKE_TOKEN not in response.error.message


@pytest.mark.asyncio
async def test_concurrent_tasks_isolate_tutor_tokens():
    provider = RequestScopedTutorTokenProvider()
    seen: dict[str, str] = {}

    async def worker(label: str, token: str) -> None:
        reset = set_request_tutor_access_token(token)
        try:
            await asyncio.sleep(0.02)
            seen[label] = await provider.get_access_token()
            await asyncio.sleep(0.02)
            assert await provider.get_access_token() == token
        finally:
            reset_request_tutor_access_token(reset)

    await asyncio.gather(
        worker("a", FAKE_TOKEN),
        worker("b", FAKE_TOKEN_B),
    )
    assert seen == {"a": FAKE_TOKEN, "b": FAKE_TOKEN_B}
    assert get_request_tutor_access_token() is None
