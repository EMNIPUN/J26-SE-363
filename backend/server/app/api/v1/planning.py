"""Project Planning REST endpoints (Core API side).

The frontend calls these; they build an OrchestrationRequest with a ``planning.*``
action and forward it to the AI Backend's Main Orchestrator over HTTP (fast path),
persist the result, then return it. The requester identity always comes from the
verified Keycloak token, never from the request body.

    POST /api/v1/planning/srs                                upload an SRS .docx -> extract + quality
    POST /api/v1/planning/quality                            score typed-in requirements
    GET  /api/v1/planning/quality                            latest stored result per requirement
    GET  /api/v1/planning/quality/{ref}/history              all stored versions of one requirement
    GET  /api/v1/planning/srs/template                       download the backend-generated SRS template (public)
    GET  /api/v1/planning/stories                            list all persisted user stories
    POST /api/v1/planning/stories                            create/update a user story
    PATCH /api/v1/planning/stories/{story_ref}               patch a user story
    DELETE /api/v1/planning/stories/{story_ref}              delete a user story
    POST /api/v1/planning/decomposition                      run decomposition analysis
    GET  /api/v1/planning/decomposition                      latest stored result per requirement
    GET  /api/v1/planning/decomposition/{ref}/history        all stored versions of one requirement
"""

from __future__ import annotations

import base64
import logging
from typing import Annotated, Any

from fastapi import (
    APIRouter,
    Depends,
    File,
    Header,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from pydantic import BaseModel, Field
from shared.contracts import (
    OrchestrationRequest,
    RequesterContext,
    ResultStatus,
    UserRole,
)
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.clients.ai_backend import AIBackendError, get_ai_backend_client
from app.core.security import CurrentUser, get_current_user
from app.database.session import get_db
from app.modules.planning import decomposition_service, service, story_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/planning", tags=["Project Planning"])

DEFAULT_THRESHOLD = 75
MAX_SRS_BYTES = 5 * 1024 * 1024  # 5 MB
DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


# --- request bodies ---------------------------------------------------------


class RequirementIn(BaseModel):
    id: str
    text: str
    type: str = "unknown"


class QualityRequest(BaseModel):
    requirements: list[RequirementIn] = Field(min_length=1)
    threshold: int = DEFAULT_THRESHOLD
    project_id: str | None = None


class StoryIn(BaseModel):
    id: str
    requirement_ref: str
    title: str
    acceptance_criteria: str = ""
    status: str = "Draft"
    invest_result: dict | None = None
    tasks: list[dict] = Field(default_factory=list)
    bugs: list[dict] = Field(default_factory=list)


class StoryPatch(BaseModel):
    title: str | None = None
    acceptance_criteria: str | None = None
    status: str | None = None
    invest_result: dict | None = None
    tasks: list[dict] | None = None
    bugs: list[dict] | None = None


class DecompositionRequest(BaseModel):
    requirement: RequirementIn
    stories: list[dict] = Field(min_length=1)
    threshold: int = DEFAULT_THRESHOLD
    project_id: str | None = None


# --- helpers ----------------------------------------------------------------


def _scope(x_team_id: str | None, project_id: str | None) -> str | None:
    """Persistence scope: an explicit project id, else the team id the frontend sends."""
    return (project_id or x_team_id or "").strip() or None


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


async def _persist(db: Session, scope: str | None, items: list[dict[str, Any]]) -> None:
    """Best-effort: a storage hiccup must not fail an already-successful analysis."""
    if not scope or not items:
        return
    try:
        await run_in_threadpool(service.save_results, db, scope, items)
    except Exception:
        logger.exception("Failed to persist quality results for scope %s", scope)


def _items_from_quality(quality: dict[str, Any] | None, text_by_ref: dict[str, str]) -> list[dict[str, Any]]:
    results = (quality or {}).get("requirements", []) if quality else []
    return [
        {
            "requirement_ref": r["id"],
            "requirement_text": text_by_ref.get(r["id"], ""),
            "result": r,
        }
        for r in results
    ]


# --- endpoints --------------------------------------------------------------


@router.post("/quality", summary="Analyze requirement quality (6 IEEE 830 dimensions)")
async def analyze_quality(
    body: QualityRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    x_team_id: Annotated[str | None, Header()] = None,
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
    result = await _orchestrate(request)
    text_by_ref = {r.id: r.text for r in body.requirements}
    await _persist(db, _scope(x_team_id, body.project_id), _items_from_quality(result, text_by_ref))
    return result


@router.post("/srs", summary="Upload an SRS .docx and extract + score its requirements")
async def upload_srs(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    file: Annotated[UploadFile, File(description="SRS document (.docx)")],
    threshold: Annotated[int, Query()] = DEFAULT_THRESHOLD,
    project_id: Annotated[str | None, Query()] = None,
    x_team_id: Annotated[str | None, Header()] = None,
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
    result = await _orchestrate(request)
    text_by_ref = {r["id"]: r.get("text", "") for r in result.get("requirements", [])}
    await _persist(db, _scope(x_team_id, project_id), _items_from_quality(result.get("quality"), text_by_ref))
    return result


@router.get("/quality", summary="Latest stored quality result per requirement")
async def get_quality(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    x_team_id: Annotated[str | None, Header()] = None,
    project_id: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    scope = _scope(x_team_id, project_id)
    if not scope:
        return {"project_id": None, "requirements": []}
    rows = await run_in_threadpool(service.latest_results, db, scope)
    return {"project_id": scope, "requirements": rows}


@router.get("/quality/{requirement_ref}/history", summary="Stored versions of one requirement")
async def get_history(
    requirement_ref: str,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    x_team_id: Annotated[str | None, Header()] = None,
    project_id: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    scope = _scope(x_team_id, project_id)
    versions = await run_in_threadpool(service.history, db, scope, requirement_ref) if scope else []
    return {"requirement_ref": requirement_ref, "versions": versions}


@router.get("/srs/template", summary="Download the backend-generated SRS template (.docx)")
async def srs_template() -> Response:
    request = OrchestrationRequest(
        requester=RequesterContext(user_id="public", role=UserRole.STUDENT),
        action="planning.get_srs_template",
        input={},
    )
    result = await _orchestrate(request)
    data = base64.b64decode(result["file_base64"])
    return Response(
        content=data,
        media_type=DOCX_MEDIA_TYPE,
        headers={"Content-Disposition": 'attachment; filename="SRS_Template.docx"'},
    )


# --- Story CRUD endpoints ---------------------------------------------------


@router.get("/stories", summary="List all persisted user stories")
async def list_stories(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    x_team_id: Annotated[str | None, Header()] = None,
    project_id: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    scope = _scope(x_team_id, project_id)
    if not scope:
        return {"project_id": None, "stories": []}
    rows = await run_in_threadpool(story_service.list_stories, db, scope)
    return {"project_id": scope, "stories": rows}


@router.post("/stories", summary="Create or update a user story")
async def create_story(
    body: StoryIn,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    x_team_id: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    scope = _scope(x_team_id, None)
    if not scope:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-Team-Id header required.")
    data = {
        "id": body.id,
        "title": body.title,
        "acceptance_criteria": body.acceptance_criteria,
        "status": body.status,
        "invest_result": body.invest_result,
        "tasks": body.tasks,
        "bugs": body.bugs,
    }
    row = await run_in_threadpool(
        story_service.upsert_story, db, scope, body.requirement_ref, body.id, data
    )
    return {"ok": True, "story": row}


@router.patch("/stories/{story_ref}", summary="Patch a user story")
async def patch_story(
    story_ref: str,
    body: StoryPatch,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    x_team_id: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    scope = _scope(x_team_id, None)
    if not scope:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-Team-Id header required.")
    rows = await run_in_threadpool(story_service.list_stories, db, scope)
    existing = next((r for r in rows if r["story_ref"] == story_ref), None)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Story not found.")
    data = existing["data"]
    patch = body.model_dump(exclude_none=True)
    data.update(patch)
    row = await run_in_threadpool(
        story_service.upsert_story, db, scope, existing["requirement_ref"], story_ref, data
    )
    return {"ok": True, "story": row}


@router.delete("/stories/{story_ref}", summary="Delete a user story")
async def delete_story(
    story_ref: str,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    x_team_id: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    scope = _scope(x_team_id, None)
    if not scope:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-Team-Id header required.")
    deleted = await run_in_threadpool(story_service.delete_story, db, scope, story_ref)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Story not found.")
    return {"ok": True}


# --- Decomposition endpoints ------------------------------------------------


@router.post("/decomposition", summary="Run decomposition analysis on stories against a requirement")
async def analyze_decomposition(
    body: DecompositionRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    x_team_id: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    request = OrchestrationRequest(
        requester=user.to_requester(),
        action="planning.analyze_decomposition",
        project_id=body.project_id,
        input={
            "requirement": {"id": body.requirement.id, "text": body.requirement.text, "type": body.requirement.type},
            "stories": body.stories,
            "options": {"threshold": body.threshold},
        },
    )
    result = await _orchestrate(request)

    scope = _scope(x_team_id, body.project_id)
    decomp_result = result.get("result")
    if scope and decomp_result:
        try:
            await run_in_threadpool(
                decomposition_service.save_result,
                db, scope, body.requirement.id, body.requirement.text, decomp_result,
            )
        except Exception:
            logger.exception("Failed to persist decomposition result for scope %s", scope)

        stories_invest = decomp_result.get("stories", [])
        for si in stories_invest:
            sid = si.get("story_id", "")
            invest_data = {
                k: si[k] for k in ("independent", "negotiable", "valuable", "estimable", "small", "testable", "overall_pass")
                if k in si
            }
            if sid and invest_data:
                try:
                    rows = await run_in_threadpool(story_service.list_stories, db, scope)
                    match = next((r for r in rows if r["story_ref"] == sid), None)
                    if match:
                        match["data"]["invest_result"] = invest_data
                        await run_in_threadpool(
                            story_service.upsert_story, db, scope,
                            match["requirement_ref"], sid, match["data"],
                        )
                except Exception:
                    logger.exception("Failed to back-fill invest_result for story %s", sid)

    return result


@router.get("/decomposition", summary="Latest stored decomposition result per requirement")
async def get_decomposition(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    x_team_id: Annotated[str | None, Header()] = None,
    project_id: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    scope = _scope(x_team_id, project_id)
    if not scope:
        return {"project_id": None, "results": []}
    rows = await run_in_threadpool(decomposition_service.latest_results, db, scope)
    return {"project_id": scope, "results": rows}


@router.get("/decomposition/{requirement_ref}/history", summary="Stored versions of one requirement's decomposition")
async def get_decomposition_history(
    requirement_ref: str,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    x_team_id: Annotated[str | None, Header()] = None,
    project_id: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    scope = _scope(x_team_id, project_id)
    versions = await run_in_threadpool(decomposition_service.history, db, scope, requirement_ref) if scope else []
    return {"requirement_ref": requirement_ref, "versions": versions}
