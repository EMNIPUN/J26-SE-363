"""HTTP client for immediate AI requests: Core API -> AI Backend -> Main Orchestrator."""

import httpx
from shared.contracts import OrchestrationRequest, OrchestrationResponse

from app.core.config import settings

ORCHESTRATION_PATH = "/api/v1/orchestration"


class AIBackendError(Exception):
    """The AI Backend could not be reached or returned an invalid response."""


class AIBackendClient:
    def __init__(
        self,
        base_url: str,
        timeout_seconds: float,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self._base_url = base_url
        self._timeout = timeout_seconds
        self._transport = transport

    async def orchestrate(self, request: OrchestrationRequest) -> OrchestrationResponse:
        try:
            async with httpx.AsyncClient(
                base_url=self._base_url, timeout=self._timeout, transport=self._transport
            ) as client:
                response = await client.post(ORCHESTRATION_PATH, json=request.model_dump(mode="json"))
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise AIBackendError(f"AI Backend request failed: {exc}") from exc

        try:
            return OrchestrationResponse.model_validate(response.json())
        except ValueError as exc:
            raise AIBackendError(f"AI Backend returned an invalid response: {exc}") from exc


def get_ai_backend_client() -> AIBackendClient:
    return AIBackendClient(settings.AI_BACKEND_URL, settings.AI_BACKEND_TIMEOUT_SECONDS)
