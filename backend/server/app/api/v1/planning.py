"""Project Planning REST endpoints (Core API side).

The frontend calls these; they build an OrchestrationRequest with a ``planning.*``
action and forward it to the AI Backend's Main Orchestrator over HTTP (fast path),
then return the agent's structured result. The requester identity always comes
from the verified Keycloak token, never from the request body.

    POST /api/v1/planning/srs       upload an SRS .docx -> extract + quality
    POST /api/v1/planning/quality   score typed-in requirements
"""

from __future__ import annotations

import base64
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field
from shared.contracts import OrchestrationRequest, ResultStatus

from app.clients.ai_backend import AIBackendError, get_ai_backend_client
from app.core.security import CurrentUser, get_current_user

router = APIRouter(prefix="/planning", tags=["Project Planning"])

DEFAULT_THRESHOLD = 75
MAX_SRS_BYTES = 5 * 1024 * 1024  # 5 MB


# --- request bodies ---------------------------------------------------------


class RequirementIn(BaseModel):
    id: str
    text: str
    type: str = "unknown"


class QualityRequest(BaseModel):
    requirements: list[RequirementIn] = Field(min_length=1)
    threshold: int = DEFAULT_THRESHOLD
    project_id: str | None = None


# --- helpers ----------------------------------------------------------------


async def _orchestrate(request: OrchestrationRequest) -> dict[str, Any]:
    try:
        response = await get_ai_backend_client().orchestrate(request)
    except AIBackendError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI backend unavailable: {exc}",
        ) from exc

    if response.status is ResultStatus.UNAVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The planning agent is not available.",
        )
    if response.status is ResultStatus.FAILED:
        message = response.error.message if response.error else "Planning agent failed."
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message)
    return response.result


# --- endpoints --------------------------------------------------------------


@router.post("/quality", summary="Analyze requirement quality (6 IEEE 830 dimensions)")
async def analyze_quality(
    body: QualityRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    request = OrchestrationRequest(
        requester=user.to_requester(),
        action="planning.analyze_quality",
        project_id=body.project_id,
        input={
            "requirements": [r.model_dump() for r in body.requirements],
            "options": {"threshold": body.threshold},
        },
    )
    return await _orchestrate(request)


@router.post("/srs", summary="Upload an SRS .docx and extract + score its requirements")
async def upload_srs(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    file: Annotated[UploadFile, File(description="SRS document (.docx)")],
    threshold: Annotated[int, Query()] = DEFAULT_THRESHOLD,
    project_id: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    filename = (file.filename or "").lower()
    if not filename.endswith(".docx"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .docx files are supported. Download the SRS template and upload it filled in.",
        )

    data = await file.read()
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The uploaded file is empty.")
    if len(data) > MAX_SRS_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large (max 5 MB).")

    request = OrchestrationRequest(
        requester=user.to_requester(),
        action="planning.extract_requirements",
        project_id=project_id,
        input={
            "file_base64": base64.b64encode(data).decode(),
            "filename": file.filename,
            "options": {"analyze_quality": True, "threshold": threshold},
        },
    )
    return await _orchestrate(request)
