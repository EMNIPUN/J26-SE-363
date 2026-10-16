"""Async Streamable HTTP client for the SELVIA platform tutor MCP server."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from datetime import datetime
from typing import Any, Protocol

import httpx2
from mcp.client.streamable_http import streamable_http_client
from mcp.types import CallToolResult
from pydantic import ValidationError

from app.agents.adaptive_tutor.schemas import (
    LearningBehaviourRecord,
    PerformanceEvidenceRecord,
)
from app.integrations.selvia_tutor_mcp.envelope import (
    extract_envelope,
    require_success_records,
)
from app.integrations.selvia_tutor_mcp.errors import (
    SelviaMcpAuthError,
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
from mcp import Client, MCPError

TOOL_GET_CURRENT_EVIDENCE = "get_current_evidence"
TOOL_GET_LEARNING_ACTIVITIES = "get_learning_activities"

DEFAULT_ACTIVITY_LIMIT = 50
MAX_ACTIVITY_LIMIT = 200


class McpToolSession(Protocol):
    """Minimal MCP session surface used by this client (for tests and the SDK Client)."""

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> CallToolResult: ...


SessionFactory = Callable[
    [str, str],
    AbstractAsyncContextManager[McpToolSession],
]


@asynccontextmanager
async def open_streamable_http_session(
    mcp_url: str,
    access_token: str,
) -> AsyncIterator[Client]:
    """Open a Streamable HTTP MCP session with Bearer auth; always closes resources."""
    try:
        async with httpx2.AsyncClient(
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=httpx2.Timeout(30.0, read=300.0),
        ) as http_client:
            transport = streamable_http_client(mcp_url, http_client=http_client)
            async with Client(transport) as client:
                yield client
    except SelviaMcpError:
        raise
    except httpx2.HTTPStatusError as exc:
        status = exc.response.status_code if exc.response is not None else None
        if status in {401, 403}:
            raise SelviaMcpAuthError(
                "Tutor MCP authentication was rejected by the platform."
            ) from exc
        raise SelviaMcpTransportError(
            "HTTP error while connecting to the SELVIA tutor MCP endpoint."
        ) from exc
    except httpx2.HTTPError as exc:
        raise SelviaMcpTransportError(
            "HTTP transport error while connecting to the SELVIA tutor MCP endpoint."
        ) from exc
    except MCPError as exc:
        raise SelviaMcpTransportError(
            "MCP protocol error while connecting to the SELVIA tutor MCP endpoint."
        ) from exc
    except OSError as exc:
        raise SelviaMcpTransportError(
            "Network error while connecting to the SELVIA tutor MCP endpoint."
        ) from exc


class SelviaTutorMcpClient:
    """Shared integration client for ``get_current_evidence`` and ``get_learning_activities``.

    Does not estimate competency, invent student identity, or mint tutor tokens.
    ``mcp_url`` must match the platform ``MCP_RESOURCE_URL`` (token audience), typically
    ending in ``/mcp``.
    """

    def __init__(
        self,
        mcp_url: str,
        token_provider: TokenProvider | None = None,
        *,
        session_factory: SessionFactory | None = None,
    ) -> None:
        if not isinstance(mcp_url, str) or not mcp_url.strip():
            raise SelviaMcpValidationError(
                "mcp_url is required and must be the platform MCP resource URL."
            )
        self._mcp_url = mcp_url.strip()
        self._token_provider: TokenProvider = (
            token_provider
            if token_provider is not None
            else UnconfiguredTokenProvider()
        )
        self._session_factory = session_factory or open_streamable_http_session

    @asynccontextmanager
    async def _session(self) -> AsyncIterator[McpToolSession]:
        token = await self._token_provider.get_access_token()
        if not isinstance(token, str) or not token.strip():
            raise SelviaMcpAuthError("Token provider returned an empty access token.")
        async with self._session_factory(self._mcp_url, token) as session:
            yield session

    async def get_current_evidence(
        self,
        *,
        course_id: str | None = None,
        concept_id: str | None = None,
    ) -> list[PerformanceEvidenceRecord]:
        """Call ``get_current_evidence`` and map records to ``PerformanceEvidenceRecord``."""
        arguments = _optional_string_args(
            courseId=course_id,
            conceptId=concept_id,
        )
        raw_records = await self._invoke_tool(
            TOOL_GET_CURRENT_EVIDENCE,
            arguments or None,
        )
        return [
            _validate_record(PerformanceEvidenceRecord, item, index)
            for index, item in enumerate(raw_records)
        ]

    async def get_learning_activities(
        self,
        *,
        course_id: str | None = None,
        activity_type: str | None = None,
        target_type: str | None = None,
        occurred_from: str | datetime | None = None,
        occurred_to: str | datetime | None = None,
        limit: int | None = None,
    ) -> list[LearningBehaviourRecord]:
        """Call ``get_learning_activities`` and map records to ``LearningBehaviourRecord``."""
        resolved_limit = DEFAULT_ACTIVITY_LIMIT if limit is None else limit
        if (
            not isinstance(resolved_limit, int)
            or isinstance(resolved_limit, bool)
            or resolved_limit < 1
            or resolved_limit > MAX_ACTIVITY_LIMIT
        ):
            raise SelviaMcpValidationError(
                f"limit must be an integer between 1 and {MAX_ACTIVITY_LIMIT}."
            )

        arguments: dict[str, Any] = {"limit": resolved_limit}
        arguments.update(
            _optional_string_args(
                courseId=course_id,
                activityType=activity_type,
                targetType=target_type,
            )
        )
        from_iso = _to_iso8601(occurred_from, field_name="occurredFrom")
        to_iso = _to_iso8601(occurred_to, field_name="occurredTo")
        if from_iso is not None:
            arguments["occurredFrom"] = from_iso
        if to_iso is not None:
            arguments["occurredTo"] = to_iso

        raw_records = await self._invoke_tool(
            TOOL_GET_LEARNING_ACTIVITIES,
            arguments,
        )
        return [
            _validate_record(LearningBehaviourRecord, item, index)
            for index, item in enumerate(raw_records)
        ]

    async def _invoke_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None,
    ) -> list[Any]:
        try:
            async with self._session() as session:
                result = await session.call_tool(tool_name, arguments)
        except SelviaMcpError:
            raise
        except MCPError as exc:
            raise SelviaMcpTransportError(
                f"MCP tool call failed for {tool_name}."
            ) from exc
        except httpx2.HTTPStatusError as exc:
            status = exc.response.status_code if exc.response is not None else None
            if status in {401, 403}:
                raise SelviaMcpAuthError(
                    "Tutor MCP authentication was rejected by the platform."
                ) from exc
            raise SelviaMcpTransportError(
                f"HTTP error during MCP tool call for {tool_name}."
            ) from exc
        except httpx2.HTTPError as exc:
            raise SelviaMcpTransportError(
                f"HTTP transport error during MCP tool call for {tool_name}."
            ) from exc
        except OSError as exc:
            raise SelviaMcpTransportError(
                f"Network error during MCP tool call for {tool_name}."
            ) from exc

        # Duck-typed mocks in unit tests may not be CallToolResult instances.
        if not isinstance(result, CallToolResult) and (
            not hasattr(result, "content") or not hasattr(result, "structured_content")
        ):
            raise SelviaMcpTransportError(
                f"MCP tool call for {tool_name} returned an unexpected result type."
            )

        try:
            envelope = extract_envelope(result)
            return require_success_records(
                envelope,
                is_error=bool(getattr(result, "is_error", False)),
            )
        except SelviaMcpToolError:
            raise
        except SelviaMcpError:
            # If the transport marked isError but envelope parsing failed, still surface
            # a tool failure rather than a silent empty list.
            if bool(getattr(result, "is_error", False)):
                raise SelviaMcpToolError(
                    "INTERNAL_ERROR",
                    f"MCP tool {tool_name} failed without a usable error envelope.",
                ) from None
            raise


def _optional_string_args(**fields: str | None) -> dict[str, str]:
    arguments: dict[str, str] = {}
    for key, value in fields.items():
        if value is None:
            continue
        if not isinstance(value, str) or not value.strip():
            raise SelviaMcpValidationError(
                f"{key} must be a non-empty string when provided."
            )
        arguments[key] = value
    return arguments


def _to_iso8601(
    value: str | datetime | None,
    *,
    field_name: str,
) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, str) and value.strip():
        return value.strip()
    raise SelviaMcpValidationError(
        f"{field_name} must be an ISO-8601 string or datetime when provided."
    )


def _validate_record(model_cls: type[Any], item: Any, index: int) -> Any:
    try:
        return model_cls.model_validate(item)
    except ValidationError as exc:
        raise SelviaMcpRecordError(
            f"Record at index {index} failed {model_cls.__name__} validation."
        ) from exc
