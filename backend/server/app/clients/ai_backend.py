"""HTTP client for immediate AI requests: Core API -> AI Backend -> Main Orchestrator."""

from __future__ import annotations

import httpx
from shared.contracts import OrchestrationRequest, OrchestrationResponse

from app.core.config import settings

ORCHESTRATION_PATH = "/api/v1/orchestration"
# Dedicated channel for short-lived tutor MCP tokens (never put in JSON / jobs / logs).
TUTOR_ACCESS_TOKEN_HEADER = "X-SELVIA-Tutor-Token"
INTERNAL_TOKEN_HEADER = "X-Internal-Token"


class AIBackendError(Exception):
    """The AI Backend could not be reached or returned an invalid response."""


class AIBackendConfigError(AIBackendError):
    """AI Backend client is missing required internal service configuration."""


class AIBackendClient:
    def __init__(
        self,
        base_url: str,
        timeout_seconds: float,
        internal_token: str,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        if not base_url or not base_url.strip():
            raise AIBackendConfigError("AI_BACKEND_URL is not configured")
        if not internal_token or not internal_token.strip():
            raise AIBackendConfigError("AI_BACKEND_INTERNAL_TOKEN is not configured")

        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds
        self._internal_token = internal_token
        self._transport = transport

    async def orchestrate(
        self,
        request: OrchestrationRequest,
        *,
        tutor_access_token: str | None = None,
    ) -> OrchestrationResponse:
        """POST orchestration JSON authenticated as the Core API service.

        Optional ``tutor_access_token`` is sent only in ``X-SELVIA-Tutor-Token``.
        It is never merged into the request body.
        """
        # The AI Backend trusts the requester in the body, so it only accepts callers
        # that hold the shared secret.
        headers = {
            INTERNAL_TOKEN_HEADER: self._internal_token,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if tutor_access_token is not None:
            if not isinstance(tutor_access_token, str) or not tutor_access_token.strip():
                raise AIBackendError(
                    "tutor_access_token must be a non-empty string when provided"
                )
            headers[TUTOR_ACCESS_TOKEN_HEADER] = tutor_access_token

        body = request.model_dump(mode="json")
        if tutor_access_token and tutor_access_token in str(body):
            raise AIBackendError(
                "Refusing to send orchestration JSON that embeds a tutor token"
            )

        try:
            async with httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout,
                transport=self._transport,
            ) as client:
                response = await client.post(
                    ORCHESTRATION_PATH, json=body, headers=headers
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise AIBackendError(
                f"AI Backend request failed with status {exc.response.status_code}"
            ) from exc
        except httpx.HTTPError as exc:
            raise AIBackendError("AI Backend request failed") from exc

        try:
            return OrchestrationResponse.model_validate(response.json())
        except ValueError as exc:
            raise AIBackendError("AI Backend returned an invalid response") from exc


def get_ai_backend_client() -> AIBackendClient:
    if not settings.ai_backend_internal_token_configured:
        raise AIBackendConfigError(
            "AI Backend internal service credential is not configured "
            "(set AI_BACKEND_INTERNAL_TOKEN)"
        )
    assert settings.AI_BACKEND_INTERNAL_TOKEN is not None
    return AIBackendClient(
        settings.AI_BACKEND_URL,
        settings.AI_BACKEND_TIMEOUT_SECONDS,
        settings.AI_BACKEND_INTERNAL_TOKEN,
    )
