"""Tutor routes — authenticated student chat + PP1 competency analysis."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from shared.contracts import UserRole

from app.clients.ai_backend import AIBackendError
from app.clients.slap_tutor_mint import SlapTutorMintError
from app.core.security import CurrentUser, require_roles
from app.modules.tutor.schemas import (
    TutorChatRequest,
    TutorChatResponse,
    TutorCompetencyRequest,
    TutorCompetencyResponse,
)
from app.modules.tutor.service import (
    TutorChatService,
    TutorExecutionUnavailable,
    get_tutor_chat_service,
    map_tutor_service_error,
)

logger = logging.getLogger(__name__)

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
        logger.warning("tutor.chat failed type=%s status=%s detail=%s", type(exc).__name__, code, detail)
        raise HTTPException(status_code=code, detail=detail) from exc


@router.post(
    "/competency",
    response_model=TutorCompetencyResponse,
    summary="Run required-knowledge + BKT competency analysis",
)
async def tutor_competency(
    body: TutorCompetencyRequest,
    user: Annotated[CurrentUser, Depends(require_roles(UserRole.STUDENT))],
    service: Annotated[TutorChatService, Depends(get_tutor_chat_service)],
) -> TutorCompetencyResponse:
    """Mint a tutor token and run ``tutor.estimate_competency`` on the AI Backend."""
    try:
        return await service.estimate_competency(user, body)
    except (TutorExecutionUnavailable, SlapTutorMintError, AIBackendError) as exc:
        code, detail = map_tutor_service_error(exc)
        logger.warning(
            "tutor.competency failed type=%s status=%s detail=%s",
            type(exc).__name__,
            code,
            detail,
        )
        raise HTTPException(status_code=code, detail=detail) from exc
