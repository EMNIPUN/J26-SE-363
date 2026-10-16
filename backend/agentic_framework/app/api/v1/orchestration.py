"""Entry point for AI requests coming from the Core API."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from shared.contracts import OrchestrationRequest, OrchestrationResponse

from app.api.dependencies import get_orchestrator
from app.core.internal_auth import require_internal_service
from app.core.tutor_token_context import (
    TUTOR_ACCESS_TOKEN_HEADER,
    TUTOR_CHAT_ACTION,
    reset_request_tutor_access_token,
    set_request_tutor_access_token,
)
from app.orchestrator import Orchestrator

router = APIRouter(tags=["Orchestration"])


@router.post(
    "/orchestration",
    response_model=OrchestrationResponse,
    dependencies=[Depends(require_internal_service)],
)
async def orchestrate(
    request: OrchestrationRequest,
    http_request: Request,
    orchestrator: Annotated[Orchestrator, Depends(get_orchestrator)],
) -> OrchestrationResponse:
    """Run orchestration for an authenticated Core API caller.

    Optional ``X-SELVIA-Tutor-Token`` is accepted only when ``action`` is ``tutor.chat``.
    The token is bound to request-scoped context and cleared when the handler returns.
    """
    tutor_header = http_request.headers.get(TUTOR_ACCESS_TOKEN_HEADER)
    reset_token = None
    if tutor_header is not None:
        if not tutor_header.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tutor token header must not be empty",
            )
        if request.action != TUTOR_CHAT_ACTION:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tutor token is not allowed for this action",
            )
        reset_token = set_request_tutor_access_token(tutor_header)

    try:
        return await orchestrator.handle(request)
    finally:
        if reset_token is not None:
            reset_request_tutor_access_token(reset_token)
