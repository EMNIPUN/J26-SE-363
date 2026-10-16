"""POST /api/v1/tutor/chat — authenticated student tutor chat (sync, fail-closed)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from shared.contracts import UserRole

from app.clients.ai_backend import AIBackendError
from app.clients.slap_tutor_mint import SlapTutorMintError
from app.core.security import CurrentUser, require_roles
from app.modules.tutor.schemas import TutorChatRequest, TutorChatResponse
from app.modules.tutor.service import (
    TutorChatService,
    TutorExecutionUnavailable,
    get_tutor_chat_service,
    map_tutor_service_error,
)

router = APIRouter(prefix="/tutor", tags=["Tutor"])


@router.post(
    "/chat",
    response_model=TutorChatResponse,
    summary="Send a tutor chat message",
)
async def tutor_chat(
    body: TutorChatRequest,
    user: Annotated[CurrentUser, Depends(require_roles(UserRole.STUDENT))],
    service: Annotated[TutorChatService, Depends(get_tutor_chat_service)],
) -> TutorChatResponse:
    """Authenticate the student and validate the body.

    Minting and AI Backend calls remain gated until a secure token handoff exists.
    """
    try:
        return await service.chat(user, body)
    except (TutorExecutionUnavailable, SlapTutorMintError, AIBackendError) as exc:
        code, detail = map_tutor_service_error(exc)
        raise HTTPException(status_code=code, detail=detail) from exc
