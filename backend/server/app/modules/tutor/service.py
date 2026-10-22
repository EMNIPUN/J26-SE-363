"""Tutor chat orchestration for the Core API.

Mints a short-lived SLAP tutor token only when secure Core→AI handoff exists and
the Adaptive Tutor execution path is known to be ready. Otherwise fails closed
without minting, without calling the AI Backend, and without enqueueing jobs.
"""

from __future__ import annotations

import inspect
from typing import Callable

from shared.contracts import OrchestrationRequest, OrchestrationResponse

from app.clients.ai_backend import AIBackendClient, AIBackendError, get_ai_backend_client
from app.clients.slap_tutor_mint import (
    SlapTutorMintAuthError,
    SlapTutorMintClient,
    SlapTutorMintConfigError,
    SlapTutorMintError,
    SlapTutorMintIdentityNotFoundError,
    SlapTutorMintNetworkError,
    SlapTutorMintProtocolError,
    SlapTutorMintTimeoutError,
    SlapTutorMintUnavailableError,
    TutorAccessToken,
    get_slap_tutor_mint_client,
)
from app.core.config import settings
from app.core.security import CurrentUser
from app.modules.tutor.schemas import (
    PP1_DEFAULT_PROJECT_ID,
    PP1_DEFAULT_SPRINT_ID,
    PP1_DEFAULT_STUDENT_ID,
    TutorChatRequest,
    TutorChatResponse,
    TutorCompetencyRequest,
    TutorCompetencyResponse,
)

TUTOR_ACTION = "tutor.chat"
TUTOR_COMPETENCY_ACTION = "tutor.estimate_competency"
TUTOR_UNAVAILABLE_DETAIL = "Tutor chat execution is not yet configured"
TUTOR_COMPETENCY_UNAVAILABLE_DETAIL = "Tutor competency execution is not yet configured"


class TutorExecutionUnavailable(Exception):
    """Secure tutor execution (token handoff + registered agent) is not available."""


def is_adaptive_tutor_execution_ready() -> bool:
    """Core-side gate for a registered, operational Adaptive Tutor in the AI Backend.

    True once ``AdaptiveTutorAgent`` is registered in the AI Backend agent registry and
    mint → MCP smoke has been verified. Still requires configured
    ``AI_BACKEND_INTERNAL_TOKEN`` (see ``is_tutor_token_handoff_available``) and a linked
    ExternalIdentity for minting. Pedagogy/competency algorithms remain out of scope.
    """
    return True


def is_tutor_token_handoff_available() -> bool:
    """True only when secure handoff is implemented and downstream tutor execution is ready.

    Checks:
    1. ``AIBackendClient.orchestrate`` accepts ``tutor_access_token`` (header channel).
    2. ``AI_BACKEND_INTERNAL_TOKEN`` is configured (service auth for Core→AI).
    3. Adaptive Tutor execution is known ready (registered/operational).
    """
    params = inspect.signature(AIBackendClient.orchestrate).parameters
    if "tutor_access_token" not in params:
        return False
    if not settings.ai_backend_internal_token_configured:
        return False
    if not is_adaptive_tutor_execution_ready():
        return False
    return True


def build_tutor_orchestration_request(
    user: CurrentUser,
    body: TutorChatRequest,
) -> OrchestrationRequest:
    """Build the internal orchestration payload from trusted Core values only."""
    kwargs: dict = {
        "requester": user.to_requester(),
        "action": TUTOR_ACTION,
        "input": {"message": body.message},
        # PP1 fixture student so chat evidence normalizer has a stable student_id.
        "student_id": PP1_DEFAULT_STUDENT_ID,
        "project_id": PP1_DEFAULT_PROJECT_ID,
        "sprint_id": PP1_DEFAULT_SPRINT_ID,
    }
    if body.request_id is not None:
        kwargs["request_id"] = str(body.request_id)
    return OrchestrationRequest(**kwargs)


def build_competency_orchestration_request(
    user: CurrentUser,
    body: TutorCompetencyRequest,
) -> OrchestrationRequest:
    """Build estimate_competency orchestration from trusted Core + PP1 sprint defaults."""
    payload_input: dict = {}
    if body.concept_ids:
        payload_input["concept_ids"] = list(body.concept_ids)
    kwargs: dict = {
        "requester": user.to_requester(),
        "action": TUTOR_COMPETENCY_ACTION,
        "student_id": PP1_DEFAULT_STUDENT_ID,
        "project_id": (body.project_id or PP1_DEFAULT_PROJECT_ID),
        "sprint_id": (body.sprint_id or PP1_DEFAULT_SPRINT_ID),
        "input": payload_input,
    }
    if body.request_id is not None:
        kwargs["request_id"] = str(body.request_id)
    return OrchestrationRequest(**kwargs)


class TutorChatService:
    def __init__(
        self,
        mint_client_factory: Callable[[], SlapTutorMintClient] = get_slap_tutor_mint_client,
        ai_client_factory: Callable[[], AIBackendClient] = get_ai_backend_client,
        handoff_available: Callable[[], bool] = is_tutor_token_handoff_available,
    ):
        self._mint_client_factory = mint_client_factory
        self._ai_client_factory = ai_client_factory
        self._handoff_available = handoff_available

    async def chat(self, user: CurrentUser, body: TutorChatRequest) -> TutorChatResponse:
        if not self._handoff_available():
            raise TutorExecutionUnavailable(TUTOR_UNAVAILABLE_DETAIL)

        mint_client = self._mint_client_factory()
        minted = await mint_client.mint_tutor_access_token(
            issuer=settings.keycloak_issuer,
            subject=user.user_id,
        )
        request = build_tutor_orchestration_request(user, body)
        self._assert_token_not_in_orchestration(request, minted)

        ai_client = self._ai_client_factory()
        response = await ai_client.orchestrate(
            request,
            tutor_access_token=minted.access_token,
        )
        return orchestration_to_tutor_response(response)

    async def estimate_competency(
        self,
        user: CurrentUser,
        body: TutorCompetencyRequest,
    ) -> TutorCompetencyResponse:
        if not self._handoff_available():
            raise TutorExecutionUnavailable(TUTOR_COMPETENCY_UNAVAILABLE_DETAIL)

        print(
            f"[tutor.estimate_competency] Core handoff start "
            f"user_id={user.user_id} project_id={body.project_id!r} "
            f"sprint_id={body.sprint_id!r}",
            flush=True,
        )

        mint_client = self._mint_client_factory()
        minted = await mint_client.mint_tutor_access_token(
            issuer=settings.keycloak_issuer,
            subject=user.user_id,
        )
        request = build_competency_orchestration_request(user, body)
        self._assert_token_not_in_orchestration(request, minted)

        ai_client = self._ai_client_factory()
        response = await ai_client.orchestrate(
            request,
            tutor_access_token=minted.access_token,
        )
        result = orchestration_to_competency_response(response)
        evidence_count = (
            result.result.get("performance_evidence_count")
            if isinstance(result.result, dict)
            else None
        )
        print(
            f"[tutor.estimate_competency] Core handoff done "
            f"status={result.status} performance_evidence_count={evidence_count}",
            flush=True,
        )
        return result

    @staticmethod
    def _assert_token_not_in_orchestration(
        request: OrchestrationRequest,
        minted: TutorAccessToken,
    ) -> None:
        payload = request.model_dump(mode="json")
        serialized = str(payload)
        if minted.access_token and minted.access_token in serialized:
            raise TutorExecutionUnavailable(TUTOR_UNAVAILABLE_DETAIL)


def get_tutor_chat_service() -> TutorChatService:
    return TutorChatService()


def map_tutor_service_error(exc: Exception) -> tuple[int, str]:
    """Map service/mint errors to sanitized (status_code, detail) pairs."""
    if isinstance(exc, TutorExecutionUnavailable):
        detail = str(exc) if str(exc) else TUTOR_UNAVAILABLE_DETAIL
        return 503, detail
    if isinstance(exc, SlapTutorMintIdentityNotFoundError):
        return 409, "Tutor identity is not linked"
    if isinstance(
        exc,
        (
            SlapTutorMintConfigError,
            SlapTutorMintAuthError,
            SlapTutorMintUnavailableError,
            SlapTutorMintTimeoutError,
            SlapTutorMintNetworkError,
        ),
    ):
        return 503, "Tutor token minting is temporarily unavailable"
    if isinstance(exc, SlapTutorMintProtocolError):
        return 502, "Tutor token minting failed"
    if isinstance(exc, AIBackendError):
        return 502, "AI Backend request failed"
    if isinstance(exc, SlapTutorMintError):
        return 503, "Tutor token minting is temporarily unavailable"
    raise exc


def orchestration_to_tutor_response(response: OrchestrationResponse) -> TutorChatResponse:
    return TutorChatResponse(
        request_id=response.request_id,
        status=response.status,
        result=response.result,
        evidence=response.evidence,
        next_action=response.next_action,
        error=response.error,
    )


def orchestration_to_competency_response(
    response: OrchestrationResponse,
) -> TutorCompetencyResponse:
    return TutorCompetencyResponse(
        request_id=response.request_id,
        status=response.status,
        result=response.result or {},
        error=response.error,
    )
