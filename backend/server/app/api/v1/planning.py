"""Project Planning REST endpoints (Core API side).

Endpoints forward to the AI Backend for agent execution, then
persist results in normalized ``rqa_*`` tables via service modules.

Session management
    POST /planning/sessions                create pipeline session
    GET  /planning/sessions/active         active session for scope
    GET  /planning/sessions/{id}           session detail

SRS & quality
    POST /planning/srs                     upload SRS .docx -> extract + quality
    GET  /planning/srs/template            download backend-generated SRS template
    POST /planning/quality                 analyze requirement quality
    GET  /planning/quality                 latest stored quality results
    GET  /planning/quality/gate            quality gate decision
    GET  /planning/quality/{ref}/history   stored quality versions

Stories
    GET  /planning/stories                 list user stories
    POST /planning/stories                 create / update a user story
    PATCH /planning/stories/{ref}          patch a user story
    DELETE /planning/stories/{ref}         soft-delete a user story

Tasks
    POST /planning/stories/{ref}/tasks              create a task/subtask
    PATCH /planning/stories/{ref}/tasks/{id}        edit a task/subtask
    DELETE /planning/stories/{ref}/tasks/{id}       delete a task/subtask
    POST /planning/stories/{ref}/tasks/validate     run AI task validation
    GET  /planning/stories/{ref}/tasks/validation   latest stored task validation

Decomposition
    POST /planning/decomposition           run decomposition analysis
    GET  /planning/decomposition           latest stored results
    GET  /planning/decomposition/gate      decomposition gate decision

Estimation
    POST /planning/estimates               save student effort estimate
    GET  /planning/estimates               list estimates for session
    POST /planning/estimates/{ref}/confirm confirm estimate -> backlog

Backlog
    GET  /planning/backlog                 list sprint backlog items
    POST /planning/backlog                 create backlog item
    PATCH /planning/backlog/{id}           update item
    DELETE /planning/backlog/{id}          delete item

DART
    POST /planning/dart/arbitrate          trigger DART arbitration
    GET  /planning/dart/cases              list DART sessions
    GET  /planning/dart/cases/{id}         single DART session
    PATCH /planning/dart/cases/{id}/resolve resolve a DART session

Feedback & alerts
    GET  /planning/feedback                list feedback for session
    PATCH /planning/feedback/{id}/view     mark feedback viewed
    GET  /planning/instructor/alerts       list instructor alerts
    PATCH /planning/instructor/alerts/{id} resolve alert
"""

from __future__ import annotations

import base64
import logging
import uuid as _uuid
from datetime import UTC, datetime
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
from pydantic import AliasChoices, BaseModel, Field, field_validator
from shared.contracts import (
    OrchestrationRequest,
    RequesterContext,
    ResultStatus,
    UserRole,
)
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.clients.ai_backend import (
    AIBackendError,
    get_ai_backend_client,
)
from app.core.security import CurrentUser, get_current_user
from app.database.session import get_db
from app.models.enums import AssessmentStatus, ParseStatus, PipelineStage, Priority, StoryStatus, TaskStatus
from app.models.group import Group, GroupMember
from app.models.pipeline_session import PipelineSession
from app.models.project import Project
from app.models.requirement import Requirement
from app.models.srs_document import SrsDocument
from app.models.user import User
from app.modules.planning import (
    dart_service,
    decomposition_service,
    estimation_service,
    feedback_service,
    jira_service,
    passport_service,
    pipeline_session_service,
    quality_service,
    requirement_service,
    sprint_backlog_service,
)

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/planning", tags=["Project Planning"]
)

DEFAULT_THRESHOLD = 75
MAX_SRS_BYTES = 5 * 1024 * 1024
DOCX_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument"
    ".wordprocessingml.document"
)

# Temporary bootstrap context until the real user/group/project provisioning
# flow is connected. Remove this fallback once those records are created by
# the academic administration/import workflow.
TEMPORARY_SHARED_GROUP_CODE = "J26-SE-363"
TEMPORARY_SHARED_GROUP_NAME = "Group 07 — SELVIA Platform"
TEMPORARY_SHARED_PROJECT_TITLE = "Multi-agent Engineering Network for Task Orchestration & Review"


# ── request / response bodies ────────────────────────────────


class RequirementIn(BaseModel):
    id: str
    text: str
    type: str = "unknown"


class QualityRequest(BaseModel):
    requirements: list[RequirementIn] = Field(min_length=1)
    threshold: int = DEFAULT_THRESHOLD
    project_id: str | None = None


class StoryIn(BaseModel):
    # Deprecated for input compatibility; the service always allocates the
    # immutable SCRUM-<number> issue key.
    id: str | None = None
    requirement_ref: str
    title: str
    as_a: str | None = None
    i_want: str | None = None
    so_that: str | None = None
    # A user story is fully represented by its agile statement and acceptance
    # criteria.  Keep this optional for older clients/data that still send it.
    description: str = ""
    acceptance_criteria: list[str] = Field(default_factory=list)
    priority: str = "medium"


class StoryPatch(BaseModel):
    title: str | None = None
    as_a: str | None = None
    i_want: str | None = None
    so_that: str | None = None
    description: str | None = None
    acceptance_criteria: list[str] | None = None
    priority: str | None = None
    status: str | None = None


class StoryTaskIn(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: str = ""
    priority: Priority = Priority.MEDIUM
    parent_task_id: _uuid.UUID | None = None


class StoryTaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = None
    priority: Priority | None = None
    status: str | None = None


class TaskValidationRequest(BaseModel):
    tasks: list[dict] = Field(min_length=1)
    project_id: str | None = None


class DecompositionRequest(BaseModel):
    requirement: RequirementIn
    stories: list[dict] = Field(min_length=1)
    threshold: int = DEFAULT_THRESHOLD
    project_id: str | None = None


ALLOWED_FIBONACCI_POINTS = {1, 2, 3, 5, 8, 13}


class EstimateIn(BaseModel):
    story_ref: str
    story_points: int = Field(
        validation_alias=AliasChoices("story_points", "estimated_story_points")
    )
    hours: float | None = Field(
        default=None,
        validation_alias=AliasChoices("hours", "estimated_hours"),
    )
    basis: str | None = Field(
        default=None,
        validation_alias=AliasChoices("basis", "estimation_basis"),
    )
    technique: str = "fibonacci"

    @field_validator("story_points")
    @classmethod
    def validate_fibonacci(cls, v: int) -> int:
        if v not in ALLOWED_FIBONACCI_POINTS:
            raise ValueError(
                f"Invalid story-point value {v}. Supported Fibonacci values are: "
                f"{sorted(ALLOWED_FIBONACCI_POINTS)}"
            )
        return v


class BacklogItemIn(BaseModel):
    user_story_id: str
    requirement_id: str
    story_points: int
    description: str | None = None
    hours: float | None = None
    estimation_source: str = "student_only"


class BacklogItemPatch(BaseModel):
    status: str | None = None
    priority: str | None = None
    assigned_to: str | None = None
    sprint_id: str | None = None
    task_description: str | None = None


class DartArbitrateRequest(BaseModel):
    requirement: RequirementIn
    trigger_reason: str = "manual"
    source_stage: str = "quality"
    source_result: dict = Field(default_factory=dict)
    stories: list[dict] = Field(default_factory=list)
    project_id: str | None = None


class DartResolveRequest(BaseModel):
    status: str = "resolved"
    note: str = ""


class JiraSyncIn(BaseModel):
    base_url: str | None = None
    email: str | None = None
    api_token: str | None = None
    project_key: str | None = None
    project_id: str | None = None
    force_resync: bool = False
    story_refs: list[str] | None = None
    story_points: dict[str, int | float] | None = None


class JiraSprintSyncIn(BaseModel):
    sprint_id: _uuid.UUID | None = None
    base_url: str | None = None
    email: str | None = None
    api_token: str | None = None
    project_key: str | None = None
    project_id: str | None = None


class JiraFetchIn(BaseModel):
    """Optional connection overrides for a manual Jira execution refresh."""
    base_url: str | None = None
    email: str | None = None
    api_token: str | None = None
    project_key: str | None = None
    project_id: str | None = None


class JiraTransitionIn(BaseModel):
    issue_key: str
    target_status: str
    # Required only for a parent-story completion transition. This is an
    # explicit student acknowledgement that its acceptance criteria and DoD
    # were checked; Jira task completion alone is not sufficient.
    acceptance_criteria_confirmed: bool = False
    project_id: str | None = None
    base_url: str | None = None
    email: str | None = None
    api_token: str | None = None



# ── helpers ──────────────────────────────────────────────────


def _normalize_team_code(raw: str) -> str:
    s = raw.strip()
    if s.lower().startswith("grp-"):
        s = s[4:]
    return s.upper()


def _resolve_group_project(
    db: Session,
    x_team_id: str | None,
    project_id: str | None = None,
) -> tuple[_uuid.UUID, _uuid.UUID] | None:
    if not x_team_id:
        return None
    code = _normalize_team_code(x_team_id)
    group = db.scalars(
        select(Group).where(Group.code == code)
    ).first()
    if not group:
        return None

    proj = None
    if project_id:
        try:
            pid = _uuid.UUID(project_id)
            proj = db.get(Project, pid)
        except ValueError:
            pass
    if not proj:
        proj = db.scalars(
            select(Project).where(
                Project.group_id == group.id
            )
        ).first()
    if not proj:
        return None
    return group.id, proj.id


def _resolve_user_db_id(
    db: Session, user: CurrentUser
) -> _uuid.UUID | None:
    return db.scalars(
        select(User.id).where(
            User.keycloak_sub == user.user_id
        )
    ).first()


def _ensure_temporary_context(
    db: Session,
    user: CurrentUser,
    x_team_id: str | None,
) -> tuple[_uuid.UUID, _uuid.UUID, _uuid.UUID] | None:
    """Provision the temporary shared planning context for the logged user.

    This is intentionally local to planning session creation. It lets the
    authenticated Keycloak user own the session while the shared academic
    records are still absent from the database.
    """
    requested_code = _normalize_team_code(x_team_id or "")
    if requested_code and requested_code != TEMPORARY_SHARED_GROUP_CODE:
        return None

    user_row = db.scalars(
        select(User).where(User.keycloak_sub == user.user_id)
    ).first()
    if not user_row:
        user_row = User(
            keycloak_sub=user.user_id,
            role=user.role,
            name=user.name or user.username or user.email or "SELVIA User",
            student_number=None,
        )
        db.add(user_row)
        db.flush()

    group = db.scalars(
        select(Group).where(Group.code == TEMPORARY_SHARED_GROUP_CODE)
    ).first()
    if not group:
        group = Group(
            code=TEMPORARY_SHARED_GROUP_CODE,
            name=TEMPORARY_SHARED_GROUP_NAME,
        )
        db.add(group)
        db.flush()

    membership = db.scalars(
        select(GroupMember).where(
            GroupMember.group_id == group.id,
            GroupMember.user_id == user_row.id,
        )
    ).first()
    if not membership:
        db.add(GroupMember(group_id=group.id, user_id=user_row.id))

    project = db.scalars(
        select(Project).where(Project.group_id == group.id)
    ).first()
    if not project:
        project = Project(
            group_id=group.id,
            created_by_id=user_row.id,
            title=TEMPORARY_SHARED_PROJECT_TITLE,
            description="Temporary shared project context for SELVIA planning.",
        )
        db.add(project)
        db.flush()

    return user_row.id, group.id, project.id


def _get_session(
    db: Session,
    x_team_id: str | None,
    project_id: str | None,
    user: CurrentUser,
    *,
    create: bool = True,
) -> PipelineSession | None:
    ids = _resolve_group_project(
        db, x_team_id, project_id
    )
    if ids:
        group_id, proj_id = ids
        user_db_id = _resolve_user_db_id(db, user)
        if not user_db_id:
            temporary_context = _ensure_temporary_context(
                db, user, x_team_id
            )
            if temporary_context:
                user_db_id, group_id, proj_id = temporary_context
    else:
        temporary_context = _ensure_temporary_context(
            db, user, x_team_id
        )
        if not temporary_context:
            return None
        user_db_id, group_id, proj_id = temporary_context

    if not create:
        return pipeline_session_service.get_active_session(
            db, proj_id, group_id
        )

    if not user_db_id:
        return None
    return pipeline_session_service.get_or_create_session(
        db, proj_id, group_id, user_db_id
    )


def _require_session(
    db: Session,
    x_team_id: str | None,
    project_id: str | None,
    user: CurrentUser,
    *,
    create: bool = True,
) -> PipelineSession:
    session = _get_session(
        db, x_team_id, project_id, user, create=create
    )
    if not session:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Could not resolve pipeline session. "
                "Ensure X-Team-Id header is set and the "
                "group/project exist."
            ),
        )
    return session


def _build_req_map(
    db: Session,
    session: PipelineSession,
    items: list[RequirementIn],
) -> dict[str, _uuid.UUID]:
    reqs = requirement_service.list_requirements(
        db, session.id
    )
    ref_map = {r.requirement_ref: r.id for r in reqs}
    for item in items:
        requirement_id = ref_map.get(item.id)
        if requirement_id:
            # Re-checks are edits to an existing requirement. Persist the
            # revised text so a page reload shows the evaluated version.
            requirement = next(
                r for r in reqs if r.id == requirement_id
            )
            requirement.requirement_text = item.text
        else:
            rows = requirement_service.create_requirements(
                db,
                session.id,
                None,
                session.project_id,
                session.group_id,
                [{"id": item.id, "text": item.text,
                  "type": item.type}],
            )
            if rows:
                ref_map[item.id] = rows[0].id
    db.flush()
    return ref_map


async def _orchestrate(
    request: OrchestrationRequest,
) -> dict[str, Any]:
    try:
        response = await get_ai_backend_client().orchestrate(
            request
        )
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
        message = (
            response.error.message
            if response.error
            else "Planning agent failed."
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=message,
        )
    return response.result


def _persist_quality(
    db: Session,
    session: PipelineSession,
    quality_results: list[dict[str, Any]],
    req_map: dict[str, _uuid.UUID],
    threshold: float = DEFAULT_THRESHOLD,
) -> None:
    for qr in quality_results:
        req_id = req_map.get(qr.get("id", ""))
        if req_id:
            requirement = db.get(Requirement, req_id)
            if not requirement:
                continue
            quality_service.save_assessment(
                db,
                req_id,
                session.id,
                qr,
                requirement.requirement_text,
            )
    assessments = quality_service.get_assessments(
        db, session.id
    )
    if assessments:
        quality_service.save_gate_decision(
            db, session.id, assessments, threshold
        )
    db.commit()


async def _auto_trigger_dart(
    user: CurrentUser,
    db: Session,
    session: PipelineSession,
    requirement: RequirementIn,
    source_stage: str,
    source_result: dict[str, Any],
    stories: list[dict] | None = None,
) -> dict[str, Any] | None:
    try:
        tripped = await run_in_threadpool(
            dart_service.session_circuit_breaker,
            db,
            session.id,
        )
        if tripped:
            logger.warning(
                "DART circuit breaker tripped for %s",
                session.id,
            )
            return None
    except Exception:
        logger.exception("Circuit breaker check failed")
        return None

    dart_request = OrchestrationRequest(
        requester=user.to_requester(),
        action="planning.arbitrate",
        project_id=str(session.project_id),
        input={
            "requirement": {
                "id": requirement.id,
                "text": requirement.text,
                "type": requirement.type,
            },
            "trigger_reason": "low_confidence",
            "source_stage": source_stage,
            "source_result": source_result,
            "stories": stories or [],
        },
    )
    try:
        dart_result = await _orchestrate(dart_request)
    except Exception:
        logger.exception(
            "DART auto-trigger failed for %s",
            requirement.id,
        )
        return None

    if dart_result:
        try:
            await run_in_threadpool(
                dart_service.create_session,
                db,
                session.id,
                dart_result,
                source_stage,
                "low_confidence",
            )
            await run_in_threadpool(
                pipeline_session_service.increment_dart_count,
                db,
                session.id,
            )
            db.commit()
        except Exception:
            logger.exception(
                "Failed to persist DART session for %s",
                requirement.id,
            )
    return dart_result


# ── Session management ───────────────────────────────────────


@router.post(
    "/sessions",
    summary="Create or get active pipeline session",
)
async def create_session(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    x_team_id: Annotated[str | None, Header()] = None,
    project_id: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    session = await run_in_threadpool(
        _require_session, db, x_team_id, project_id, user
    )
    return pipeline_session_service.session_to_dict(session)


@router.get(
    "/sessions/active",
    summary="Get the active pipeline session",
)
async def get_active_session(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    x_team_id: Annotated[str | None, Header()] = None,
    project_id: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    session = await run_in_threadpool(
        _get_session,
        db,
        x_team_id,
        project_id,
        user,
        create=False,
    )
    if not session:
        return {"session": None}
    return pipeline_session_service.session_to_dict(session)


@router.get(
    "/sessions/{session_id}",
    summary="Get pipeline session details",
)
async def get_session_detail(
    session_id: _uuid.UUID,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    session = pipeline_session_service.get_session(
        db, session_id
    )
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found.",
        )
    return pipeline_session_service.session_to_dict(session)


# ── SRS & quality ────────────────────────────────────────────


@router.post(
    "/srs",
    summary="Upload SRS .docx, extract + score requirements",
)
async def upload_srs(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    file: Annotated[
        UploadFile,
        File(description="SRS document (.docx)"),
    ],
    threshold: Annotated[int, Query()] = DEFAULT_THRESHOLD,
    project_id: Annotated[str | None, Query()] = None,
    x_team_id: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    filename = (file.filename or "").lower()
    if not filename.endswith(".docx"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Only .docx files are supported. "
                "Download the SRS template and upload "
                "it filled in."
            ),
        )

    data = await file.read()
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is empty.",
        )
    if len(data) > MAX_SRS_BYTES:
        raise HTTPException(
            status_code=(
                status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
            ),
            detail="File too large (max 5 MB).",
        )

    session = await run_in_threadpool(
        _require_session, db, x_team_id, project_id, user
    )
    user_db_id = await run_in_threadpool(
        _resolve_user_db_id, db, user
    )

    srs_doc = SrsDocument(
        pipeline_session_id=session.id,
        group_id=session.group_id,
        uploaded_by=user_db_id or session.initiated_by,
        original_filename=file.filename or "srs.docx",
        file_size_bytes=len(data),
        mime_type=DOCX_MEDIA_TYPE,
        parse_status=ParseStatus.PENDING,
    )
    db.add(srs_doc)
    db.flush()

    request = OrchestrationRequest(
        requester=user.to_requester(),
        action="planning.extract_requirements",
        project_id=str(session.project_id),
        input={
            "file_base64": base64.b64encode(data).decode(),
            "filename": file.filename,
            "options": {
                "analyze_quality": True,
                "threshold": threshold,
            },
        },
    )
    result = await _orchestrate(request)

    try:
        extracted = result.get("requirements", [])
        srs_doc.parse_status = ParseStatus.PARSED
        srs_doc.total_requirements_extracted = len(extracted)
        srs_doc.parsed_at = datetime.now(UTC)

        reqs = requirement_service.create_requirements(
            db,
            session.id,
            srs_doc.id,
            session.project_id,
            session.group_id,
            extracted,
        )
        req_map = {r.requirement_ref: r.id for r in reqs}

        quality_data = (
            (result.get("quality") or {})
            .get("requirements", [])
        )
        if quality_data:
            _persist_quality(
                db, session, quality_data, req_map, threshold
            )

        pipeline_session_service.advance_stage(
            db, session.id, PipelineStage.QUALITY
        )
        db.commit()
    except Exception:
        logger.exception(
            "Failed to persist SRS/quality results"
        )
        # Never return an apparently successful upload when the database
        # transaction failed. Roll back the partial document/requirement rows
        # and let the UI tell the student to retry instead of showing results
        # that disappear on refresh.
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The SRS was analyzed but could not be saved. Please try again.",
        ) from None

    return result


@router.get(
    "/srs/template",
    summary="Download the SRS template (.docx)",
)
async def srs_template() -> Response:
    request = OrchestrationRequest(
        requester=RequesterContext(
            user_id="public", role=UserRole.STUDENT
        ),
        action="planning.get_srs_template",
        input={},
    )
    result = await _orchestrate(request)
    data = base64.b64decode(result["file_base64"])
    return Response(
        content=data,
        media_type=DOCX_MEDIA_TYPE,
        headers={
            "Content-Disposition": (
                'attachment; filename="SRS_Template.docx"'
            )
        },
    )


@router.post(
    "/quality",
    summary="Analyze requirement quality",
)
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
            "requirements": [
                r.model_dump() for r in body.requirements
            ],
            "options": {"threshold": body.threshold},
        },
    )
    result = await _orchestrate(request)

    session = await run_in_threadpool(
        _get_session,
        db,
        x_team_id,
        body.project_id,
        user,
    )
    if session:
        try:
            req_map = await run_in_threadpool(
                _build_req_map,
                db,
                session,
                body.requirements,
            )
            quality_data = (result or {}).get(
                "requirements", []
            )
            await run_in_threadpool(
                _persist_quality,
                db,
                session,
                quality_data,
                req_map,
                float(body.threshold),
            )
        except Exception:
            logger.exception(
                "Failed to persist quality results"
            )
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Quality result could not be saved. Please try again.",
            ) from None

        dart_cases: list[dict[str, Any]] = []
        for req_result in (result or {}).get(
            "requirements", []
        ):
            if req_result.get("dart_triggered"):
                req_in = next(
                    (
                        r
                        for r in body.requirements
                        if r.id == req_result["id"]
                    ),
                    None,
                )
                if req_in:
                    dart_result = await _auto_trigger_dart(
                        user,
                        db,
                        session,
                        req_in,
                        "quality",
                        req_result,
                    )
                    if dart_result:
                        dart_cases.append(
                            dart_result.get("case", {})
                        )
        if dart_cases:
            result["dart_cases"] = dart_cases

    return result


@router.get(
    "/quality",
    summary="Latest quality results for session",
)
async def get_quality(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    x_team_id: Annotated[str | None, Header()] = None,
    project_id: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    session = await run_in_threadpool(
        _get_session,
        db,
        x_team_id,
        project_id,
        user,
        create=False,
    )
    if not session:
        return {"project_id": None, "requirements": []}

    assessments = await run_in_threadpool(
        quality_service.get_assessments, db, session.id
    )
    reqs = await run_in_threadpool(
        requirement_service.list_requirements, db, session.id
    )
    ref_lookup = {r.id: r for r in reqs}

    results = []
    for a in assessments:
        d = quality_service.assessment_to_dict(a)
        req = ref_lookup.get(a.requirement_id)
        if req:
            d["id"] = req.requirement_ref
            d["text"] = req.requirement_text
            d["type"] = req.requirement_category.value
            d["decomposition_authorized"] = req.quality_approved_for_decomposition
            d["effort_authorized"] = req.decomposition_approved_for_effort
        results.append(d)

    return {
        "project_id": str(session.project_id),
        "requirements": results,
    }


@router.post(
    "/quality/{requirement_ref}/proceed-to-decomposition",
    summary="Authorize a passing requirement for decomposition",
)
async def proceed_to_decomposition(
    requirement_ref: str,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    x_team_id: Annotated[str | None, Header()] = None,
    project_id: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    session = await run_in_threadpool(_get_session, db, x_team_id, project_id, user, create=False)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active planning session was found.")
    req = await run_in_threadpool(requirement_service.get_by_ref, db, session.id, requirement_ref)
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requirement was not found.")
    rows = await run_in_threadpool(quality_service.get_assessments, db, session.id)
    assessment = next((row for row in rows if row.requirement_id == req.id), None)
    if not assessment or assessment.assessment_status != AssessmentStatus.COMPLETED or float(assessment.composite_score) < DEFAULT_THRESHOLD:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This requirement must complete and pass SRS Quality (minimum 75%) first.")
    req.quality_approved_for_decomposition = True
    db.commit()
    return {"requirement_ref": requirement_ref, "decomposition_authorized": True}


@router.get(
    "/quality/gate",
    summary="Quality gate decision for session",
)
async def get_quality_gate(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    x_team_id: Annotated[str | None, Header()] = None,
    project_id: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    session = await run_in_threadpool(
        _get_session,
        db,
        x_team_id,
        project_id,
        user,
        create=False,
    )
    if not session:
        return {"gate": None}
    gate = await run_in_threadpool(
        quality_service.get_gate_decision, db, session.id
    )
    if not gate:
        return {"gate": None}
    return {"gate": quality_service.gate_to_dict(gate)}


@router.get(
    "/quality/{requirement_ref}/history",
    summary="Stored quality versions for one requirement",
)
async def get_quality_history(
    requirement_ref: str,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    x_team_id: Annotated[str | None, Header()] = None,
    project_id: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    session = await run_in_threadpool(
        _get_session,
        db,
        x_team_id,
        project_id,
        user,
        create=False,
    )
    if not session:
        return {
            "requirement_ref": requirement_ref,
            "versions": [],
        }
    assessments = await run_in_threadpool(
        quality_service.get_assessments,
        db,
        session.id,
        latest_only=False,
    )
    req = await run_in_threadpool(
        requirement_service.get_by_ref,
        db,
        session.id,
        requirement_ref,
    )
    versions = []
    if req:
        versions = sorted(
            (
                quality_service.assessment_to_dict(a)
                for a in assessments
                if a.requirement_id == req.id
            ),
            key=lambda item: item["revision_number"],
        )
    return {
        "requirement_ref": requirement_ref,
        "versions": versions,
    }


# ── Story CRUD ───────────────────────────────────────────────


@router.get(
    "/stories", summary="List all user stories"
)
async def list_stories(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    x_team_id: Annotated[str | None, Header()] = None,
    project_id: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    session = await run_in_threadpool(
        _get_session,
        db,
        x_team_id,
        project_id,
        user,
        create=False,
    )
    if not session:
        return {"project_id": None, "stories": []}
    rows = await run_in_threadpool(
        decomposition_service.list_stories, db, session.id
    )
    requirements = await run_in_threadpool(
        requirement_service.list_requirements, db, session.id
    )
    requirement_refs = {requirement.id: requirement.requirement_ref for requirement in requirements}
    task_validations = await run_in_threadpool(
        decomposition_service.get_latest_task_validations, db, [row.id for row in rows]
    )
    from app.models.sprint import Sprint

    sprint_rows = await run_in_threadpool(
        lambda: list(db.scalars(select(Sprint).where(Sprint.project_id == session.project_id)).all())
    )
    sprint_states = {sprint.jira_sprint_id: sprint.jira_state for sprint in sprint_rows if sprint.jira_sprint_id}
    stories = []
    for row in rows:
        story = decomposition_service.story_to_dict(row, task_validations.get(row.id))
        story["requirement_ref"] = requirement_refs.get(row.requirement_id, str(row.requirement_id))
        story["jira_sprint_state"] = sprint_states.get(row.jira_sprint_id)
        stories.append(story)
    return {
        "project_id": str(session.project_id),
        "stories": stories,
    }


@router.post("/stories", status_code=status.HTTP_201_CREATED, summary="Create a user story")
async def create_story(
    body: StoryIn,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    x_team_id: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    session = await run_in_threadpool(
        _require_session, db, x_team_id, None, user
    )
    req = await run_in_threadpool(
        requirement_service.get_by_ref,
        db,
        session.id,
        body.requirement_ref,
    )
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Requirement '{body.requirement_ref}' "
                "not found in this session."
            ),
        )
    user_db_id = await run_in_threadpool(
        _resolve_user_db_id, db, user
    )
    story_data = body.model_dump(exclude={"requirement_ref", "id"})
    # Never use a client-supplied key. The persistence service allocates an
    # atomic, immutable SCRUM-<number> key suitable for issue-tracker mapping.
    try:
        row = await run_in_threadpool(
            decomposition_service.create_story,
            db,
            req.id,
            session.id,
            story_data,
            user_db_id,
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user story with this reference already exists in this project.",
        )
    return {
        "ok": True,
        "story": decomposition_service.story_to_dict(row),
    }


@router.patch(
    "/stories/{story_ref}",
    summary="Patch a user story",
)
async def patch_story(
    story_ref: str,
    body: StoryPatch,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    x_team_id: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    session = await run_in_threadpool(
        _require_session, db, x_team_id, None, user
    )
    row = await run_in_threadpool(
        decomposition_service.get_story_by_ref,
        db,
        session.id,
        story_ref,
    )
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Story not found.",
        )
    patch = body.model_dump(exclude_none=True)
    requested_status = patch.get("status")
    if requested_status and requested_status != StoryStatus.ACCEPTED.value:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Story status is managed by the decomposition and estimation workflow.",
        )
    if requested_status == StoryStatus.ACCEPTED.value and row.status != StoryStatus.INVEST_PASSED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only a story that passes the latest INVEST analysis can be accepted.",
        )
    if row.status == StoryStatus.IN_BACKLOG and any(
        field in patch
        for field in ("title", "as_a", "i_want", "so_that", "description", "acceptance_criteria")
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A story already sent to the sprint backlog cannot be edited.",
        )
    changed = False
    for field, val in patch.items():
        if field == "status":
            try:
                val = StoryStatus(val)
            except ValueError:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid story status.")
        if hasattr(row, field) and getattr(row, field) != val:
            setattr(row, field, val)
            changed = True
    if changed and any(
        field in patch
        for field in ("title", "as_a", "i_want", "so_that", "description", "acceptance_criteria")
    ) and row.status not in (StoryStatus.IN_BACKLOG, StoryStatus.ESTIMATED):
        row.status = StoryStatus.DRAFT
    if changed:
        row.edited_at = datetime.now(UTC)
    db.flush()
    db.commit()
    validation = await run_in_threadpool(decomposition_service.get_latest_task_validation, db, row.id)
    return {
        "ok": True,
        "story": decomposition_service.story_to_dict(row, validation),
    }


@router.post("/stories/{story_ref}/tasks", status_code=status.HTTP_201_CREATED, summary="Create a story task or subtask")
async def create_story_task(
    story_ref: str,
    body: StoryTaskIn,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    x_team_id: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    session = await run_in_threadpool(_require_session, db, x_team_id, None, user)
    story = await run_in_threadpool(decomposition_service.get_story_by_ref, db, session.id, story_ref)
    if not story:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Story not found.")
    try:
        await run_in_threadpool(
            decomposition_service.create_task,
            db, story, body.title, body.parent_task_id, body.description, body.priority,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    db.commit()
    story = await run_in_threadpool(decomposition_service.get_story_by_ref, db, session.id, story_ref)
    validation = await run_in_threadpool(decomposition_service.get_latest_task_validation, db, story.id)
    return {"ok": True, "story": decomposition_service.story_to_dict(story, validation)}


@router.patch(
    "/stories/{story_ref}/tasks/{task_id}",
    summary="Edit a story task or subtask",
)
async def update_story_task(
    story_ref: str,
    task_id: _uuid.UUID,
    body: StoryTaskUpdate,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    x_team_id: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    session = await run_in_threadpool(_require_session, db, x_team_id, None, user)
    story = await run_in_threadpool(decomposition_service.get_story_by_ref, db, session.id, story_ref)
    if not story:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Story not found.")
    task = await run_in_threadpool(decomposition_service.get_task, db, story, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
    status_val = None
    if body.status is not None:
        try:
            status_val = TaskStatus(body.status)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid task status.")
    await run_in_threadpool(
        decomposition_service.update_task,
        db, task, title=body.title, description=body.description, priority=body.priority, status=status_val,
    )
    db.commit()
    story = await run_in_threadpool(decomposition_service.get_story_by_ref, db, session.id, story_ref)
    validation = await run_in_threadpool(decomposition_service.get_latest_task_validation, db, story.id)
    return {"ok": True, "story": decomposition_service.story_to_dict(story, validation)}


@router.delete(
    "/stories/{story_ref}/tasks/{task_id}",
    summary="Delete a story task or subtask",
)
async def delete_story_task(
    story_ref: str,
    task_id: _uuid.UUID,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    x_team_id: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    session = await run_in_threadpool(_require_session, db, x_team_id, None, user)
    story = await run_in_threadpool(decomposition_service.get_story_by_ref, db, session.id, story_ref)
    if not story:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Story not found.")
    task = await run_in_threadpool(decomposition_service.get_task, db, story, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
    await run_in_threadpool(decomposition_service.delete_task, db, task)
    db.commit()
    story = await run_in_threadpool(decomposition_service.get_story_by_ref, db, session.id, story_ref)
    validation = await run_in_threadpool(decomposition_service.get_latest_task_validation, db, story.id)
    return {"ok": True, "story": decomposition_service.story_to_dict(story, validation)}


@router.post(
    "/stories/{story_ref}/tasks/validate",
    summary="Run AI task validation for a story's tasks",
)
async def validate_story_tasks(
    story_ref: str,
    body: TaskValidationRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    x_team_id: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    session = await run_in_threadpool(_require_session, db, x_team_id, body.project_id, user)
    story = await run_in_threadpool(decomposition_service.get_story_by_ref, db, session.id, story_ref)
    if not story:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Story not found.")

    response: dict[str, Any] = {"persisted": False, "persist_error": None, "assessment": None}

    # Reuse the prior validation when the submitted tasks are byte-for-byte
    # identical to what produced it — mirrors analyze_decomposition's
    # input_hash short-circuit against repeated LLM calls.
    input_hash = decomposition_service.compute_tasks_hash(body.tasks)
    cached = await run_in_threadpool(decomposition_service.get_latest_task_validation, db, story.id)
    if cached and cached.input_hash == input_hash and not cached.analysis_failed:
        assessment_dict = decomposition_service.task_validation_to_dict(cached)
        assessment_dict["reused"] = True
        response["persisted"] = True
        response["assessment"] = assessment_dict
        return response

    requirement = await run_in_threadpool(db.get, Requirement, story.requirement_id)

    request = OrchestrationRequest(
        requester=user.to_requester(),
        action="planning.validate_tasks",
        project_id=body.project_id,
        input={
            "story": {
                "id": story.story_ref,
                "title": story.title,
                "description": story.description or "",
            },
            "requirement_text": requirement.requirement_text if requirement else "",
            "tasks": body.tasks,
        },
    )
    result = await _orchestrate(request)
    task_result = result.get("result")

    if task_result:
        try:
            assessment = await run_in_threadpool(
                decomposition_service.save_task_validation,
                db, story, session.id, task_result, story.tasks, session.initiated_by, input_hash,
            )
            db.commit()
            assessment_dict = decomposition_service.task_validation_to_dict(assessment)
            response["persisted"] = True
            response["assessment"] = assessment_dict
        except Exception:
            logger.exception("Failed to persist task validation result")
            db.rollback()
            response["persist_error"] = (
                "Validation completed but could not be saved — please re-run validation."
            )

    return response


@router.get(
    "/stories/{story_ref}/tasks/validation",
    summary="Latest stored task-validation result for a story",
)
async def get_story_task_validation(
    story_ref: str,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    x_team_id: Annotated[str | None, Header()] = None,
    project_id: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    session = await run_in_threadpool(_get_session, db, x_team_id, project_id, user, create=False)
    if not session:
        return {"assessment": None}
    story = await run_in_threadpool(decomposition_service.get_story_by_ref, db, session.id, story_ref)
    if not story:
        return {"assessment": None}
    row = await run_in_threadpool(decomposition_service.get_latest_task_validation, db, story.id)
    if not row:
        return {"assessment": None}
    return {"assessment": decomposition_service.task_validation_to_dict(row)}


@router.delete(
    "/stories/{story_ref}",
    summary="Soft-delete a user story",
)
async def delete_story(
    story_ref: str,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    x_team_id: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    session = await run_in_threadpool(
        _require_session, db, x_team_id, None, user
    )
    deleted = await run_in_threadpool(
        decomposition_service.delete_story,
        db,
        session.id,
        story_ref,
    )
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Story not found.",
        )
    db.commit()
    return {"ok": True}


# ── Decomposition ────────────────────────────────────────────


def _attach_requirement_refs(
    db: Session,
    session: PipelineSession,
    dicts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Replace each dict's UUID requirement_id with the human-readable ref
    (e.g. "REQ-1") the frontend actually keys its requirements by - mirrors
    the GET /planning/quality req_map/ref_lookup pattern."""
    reqs = requirement_service.list_requirements(db, session.id)
    ref_lookup = {r.id: r.requirement_ref for r in reqs}
    for d in dicts:
        ref = ref_lookup.get(_uuid.UUID(d["requirement_id"]))
        if ref:
            d["requirement_id"] = ref
    return dicts


@router.post(
    "/decomposition",
    summary="Run decomposition analysis",
)
async def analyze_decomposition(
    body: DecompositionRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    x_team_id: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    session = await run_in_threadpool(
        _get_session,
        db,
        x_team_id,
        body.project_id,
        user,
    )
    response: dict[str, Any] = {
        "persisted": False,
        "persist_error": None,
        "assessment": None,
        "dart_cases": [],
        "stories_analyzed": 0,
        "stories_reused": 0,
    }

    # Decomposition is available only after THIS requirement has a completed,
    # passing SRS-quality assessment in the database. This guard is enforced
    # server-side so an old browser state or direct API call cannot bypass the
    # stage order.
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active planning session was found.",
        )
    req = await run_in_threadpool(
        requirement_service.get_by_ref, db, session.id, body.requirement.id,
    )
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Requirement '{body.requirement.id}' was not found in this session.",
        )
    quality_rows = await run_in_threadpool(
        quality_service.get_assessments, db, session.id,
    )
    quality = next((row for row in quality_rows if row.requirement_id == req.id), None)
    if (
        not quality
        or quality.assessment_status != AssessmentStatus.COMPLETED
        or float(quality.composite_score) < DEFAULT_THRESHOLD
        or not req.quality_approved_for_decomposition
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Complete and pass SRS Quality (minimum 75%), then click Proceed to "
                "Decomposition for this requirement."
            ),
        )

    # Reuse the prior analysis when the submitted stories are byte-for-byte
    # identical to what produced it — this is the main lever against hitting
    # the LLM provider's rate limit on repeated clicks / accidental
    # re-submits. A run that itself failed is never reused, so the student
    # can always retry after a transient error.
    input_hash = decomposition_service.compute_stories_hash(body.stories)
    story_input_hashes = {
        str(story.get("id") or story.get("story_ref") or ""): (
            decomposition_service.compute_story_hash(story)
        )
        for story in body.stories
    }
    cached = await run_in_threadpool(
        decomposition_service.get_latest_assessment_for_requirement,
        db, session.id, req.id,
    )
    unchanged = cached and cached.input_hash == input_hash
    if unchanged and not cached.analysis_failed:
        assessment_dict = decomposition_service.assessment_to_dict(cached)
        assessment_dict["requirement_id"] = body.requirement.id
        assessment_dict["reused"] = True
        response["persisted"] = True
        response["assessment"] = assessment_dict
        response["stories_reused"] = len(body.stories)
        return response

    prior_story_hashes = (cached.assessment_evidence or {}).get(
        "story_input_hashes", {}
    ) if cached and not cached.analysis_failed else {}
    story_ids_to_analyze = [
        story_id
        for story_id, story_hash in story_input_hashes.items()
        if prior_story_hashes.get(story_id) != story_hash
    ]
    cached_story_results: list[dict[str, Any]] = []
    cached_task_summaries: list[dict[str, Any]] = []
    if cached and prior_story_hashes:
        prior_results, prior_tasks = await run_in_threadpool(
            decomposition_service.get_cached_story_analysis, cached
        )
        unchanged_story_ids = set(story_input_hashes) - set(story_ids_to_analyze)
        cached_story_results = [
            result for result in prior_results
            if result.get("story_id") in unchanged_story_ids
        ]
        cached_task_summaries = [
            result for result in prior_tasks
            if result.get("story_id") in unchanged_story_ids
        ]
    response["stories_analyzed"] = len(story_ids_to_analyze)
    response["stories_reused"] = len(cached_story_results)

    request = OrchestrationRequest(
        requester=user.to_requester(),
        action="planning.analyze_decomposition",
        project_id=body.project_id,
        input={
            "requirement": {
                "id": body.requirement.id,
                "text": body.requirement.text,
                "type": body.requirement.type,
            },
            "stories": body.stories,
            "options": {
                "threshold": body.threshold,
                "story_ids_to_analyze": story_ids_to_analyze,
                "cached_story_results": cached_story_results,
                "cached_task_summaries": cached_task_summaries,
            },
        },
    )
    result = await _orchestrate(request)
    decomp_result = result.get("result")

    if session and decomp_result:
        if decomp_result.get("dart_triggered"):
            dart_result = await _auto_trigger_dart(
                user,
                db,
                session,
                body.requirement,
                "decomposition",
                decomp_result,
                body.stories,
            )
            if dart_result:
                response["dart_cases"] = [
                    dart_result.get("case", {})
                ]

        try:
            if not req:
                raise ValueError(
                    f"Requirement '{body.requirement.id}' not found in session."
                )
            stories = await run_in_threadpool(
                decomposition_service.list_stories,
                db,
                session.id,
            )
            assessment = await run_in_threadpool(
                decomposition_service.save_assessment,
                db,
                req.id,
                session.id,
                decomp_result,
                stories,
                session.initiated_by,
                input_hash,
                story_input_hashes,
            )
            pipeline_session_service.advance_stage(
                db,
                session.id,
                PipelineStage.DECOMPOSITION,
            )
            db.commit()
            assessment_dict = decomposition_service.assessment_to_dict(
                assessment
            )
            assessment_dict["requirement_id"] = body.requirement.id
            response["persisted"] = True
            response["assessment"] = assessment_dict
        except Exception:
            logger.exception("Failed to persist decomposition result")
            db.rollback()
            response["persist_error"] = (
                "Analysis completed but could not be saved — "
                "please re-run analysis."
            )

    return response


@router.get(
    "/decomposition",
    summary="Latest decomposition results",
)
async def get_decomposition(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    x_team_id: Annotated[str | None, Header()] = None,
    project_id: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    session = await run_in_threadpool(
        _get_session,
        db,
        x_team_id,
        project_id,
        user,
        create=False,
    )
    if not session:
        return {"project_id": None, "results": []}
    rows = await run_in_threadpool(
        decomposition_service.get_assessments,
        db,
        session.id,
    )
    results = [decomposition_service.assessment_to_dict(r) for r in rows]
    results = await run_in_threadpool(
        _attach_requirement_refs, db, session, results
    )
    return {
        "project_id": str(session.project_id),
        "results": results,
    }


@router.get(
    "/decomposition/gate",
    summary="Decomposition gate decision for a requirement",
)
async def get_decomposition_gate(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    x_team_id: Annotated[str | None, Header()] = None,
    project_id: Annotated[str | None, Query()] = None,
    requirement_ref: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    session = await run_in_threadpool(
        _get_session,
        db,
        x_team_id,
        project_id,
        user,
        create=False,
    )
    if not session:
        return {"gate": None}

    requirement_id: _uuid.UUID | None = None
    if requirement_ref:
        req = await run_in_threadpool(
            requirement_service.get_by_ref, db, session.id, requirement_ref
        )
        if not req:
            return {"gate": None}
        requirement_id = req.id

    row = await run_in_threadpool(
        decomposition_service.get_gate_status, db, session.id, requirement_id
    )
    if not row:
        return {"gate": None}
    gate = decomposition_service.gate_to_dict(row)
    gate["requirement_id"] = requirement_ref or str(row.requirement_id)
    return {"gate": gate}


@router.post(
    "/decomposition/{requirement_ref}/proceed-to-effort",
    summary="Authorize a decomposed requirement for effort estimation",
)
async def proceed_to_effort_estimation(
    requirement_ref: str,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    x_team_id: Annotated[str | None, Header()] = None,
    project_id: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    session = await run_in_threadpool(_get_session, db, x_team_id, project_id, user, create=False)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active planning session was found.")
    req = await run_in_threadpool(requirement_service.get_by_ref, db, session.id, requirement_ref)
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requirement was not found.")
    assessment = await run_in_threadpool(
        decomposition_service.get_latest_assessment_for_requirement, db, session.id, req.id,
    )
    if not assessment or assessment.analysis_failed:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Run a valid decomposition analysis before proceeding to effort estimation.")

    requirement_stories = await run_in_threadpool(
        decomposition_service.list_stories, db, session.id
    )
    stories_without_tasks = [
        story.story_ref
        for story in requirement_stories
        if story.requirement_id == req.id and not story.tasks
    ]
    if stories_without_tasks:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Add at least one implementation task to every user story before "
                "proceeding to effort estimation. Missing tasks: "
                f"{', '.join(stories_without_tasks)}."
            ),
        )

    # Decomposition Completeness Gate check: verify no critical missing elements
    critical_missing = [
        el for el in (assessment.coverage_elements or [])
        if getattr(el, "coverage_result", None) and str(getattr(el.coverage_result, "value", el.coverage_result)).lower() == "missing"
        and str(getattr(el.element_type, "value", el.element_type)).lower() in ("exception_behavior", "error_handling", "recovery_retry", "business_rule")
    ]
    if critical_missing:
        missing_names = ", ".join(el.description[:40] for el in critical_missing[:2])
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Decomposition Completeness Gate blocked: missing requirement elements ({missing_names}). Please cover these in your user stories or acceptance criteria.",
        )

    req.decomposition_approved_for_effort = True
    db.commit()
    return {"requirement_ref": requirement_ref, "effort_authorized": True}


# ── Estimation ───────────────────────────────────────────────


def _check_project_access(
    db: Session, user: CurrentUser, session: PipelineSession
) -> None:
    if user.role in (UserRole.ADMIN, UserRole.LECTURER):
        return
    user_db_id = _resolve_user_db_id(db, user)
    if not user_db_id:
        return
    if session.initiated_by == user_db_id:
        return
    membership = db.scalars(
        select(GroupMember).where(
            GroupMember.group_id == session.group_id,
            GroupMember.user_id == user_db_id,
        )
    ).first()
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to estimate stories for this project.",
        )


@router.post(
    "/estimates",
    summary="Save a student effort estimate",
)
async def save_estimate(
    body: EstimateIn,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    x_team_id: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    session = await run_in_threadpool(
        _require_session, db, x_team_id, None, user
    )
    await run_in_threadpool(
        _check_project_access, db, user, session
    )
    story = await run_in_threadpool(
        decomposition_service.get_story_by_ref,
        db,
        session.id,
        body.story_ref,
    )
    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Story not found.",
        )
    requirement = db.get(Requirement, story.requirement_id)
    if requirement and not requirement.decomposition_approved_for_effort:
        requirement.decomposition_approved_for_effort = True
    user_db_id = await run_in_threadpool(
        _resolve_user_db_id, db, user
    )
    row = await run_in_threadpool(
        estimation_service.save_student_estimate,
        db,
        story.id,
        session.id,
        user_db_id,
        body.story_points,
        body.hours,
        body.basis,
        body.technique,
    )
    db.commit()
    return {
        "ok": True,
        "estimate": estimation_service.estimate_to_dict(row),
    }


@router.get(
    "/estimates",
    summary="List estimates for session",
)
async def list_estimates(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    x_team_id: Annotated[str | None, Header()] = None,
    project_id: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    session = await run_in_threadpool(
        _get_session,
        db,
        x_team_id,
        project_id,
        user,
        create=False,
    )
    if not session:
        return {"estimates": []}
    await run_in_threadpool(
        _check_project_access, db, user, session
    )
    rows = await run_in_threadpool(
        estimation_service.list_estimates, db, session.id
    )
    return {
        "estimates": [
            estimation_service.estimate_to_dict(r)
            for r in rows
        ],
    }


@router.post(
    "/estimates/{story_ref}/confirm",
    summary="Confirm estimate and create backlog item",
)
async def confirm_estimate(
    story_ref: str,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    x_team_id: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    session = await run_in_threadpool(
        _require_session, db, x_team_id, None, user
    )
    await run_in_threadpool(
        _check_project_access, db, user, session
    )
    story = await run_in_threadpool(
        decomposition_service.get_story_by_ref,
        db,
        session.id,
        story_ref,
    )
    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Story not found.",
        )
    requirement = db.get(Requirement, story.requirement_id)
    if not requirement or not requirement.decomposition_approved_for_effort:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Review decomposition and click Proceed to Effort Estimation before confirming estimates.",
        )
    estimates = await run_in_threadpool(
        estimation_service.list_estimates, db, session.id
    )
    est = next(
        (e for e in estimates if e.user_story_id == story.id),
        None,
    )
    points = est.estimated_story_points if est else (story.student_story_points or 0)
    hours = (
        float(est.estimated_hours)
        if est and est.estimated_hours
        else None
    )
    item = await run_in_threadpool(
        sprint_backlog_service.create_item,
        db,
        session.id,
        story.id,
        story.requirement_id,
        points,
        story.title,
        hours,
    )
    story.status = StoryStatus.IN_BACKLOG
    pipeline_session_service.advance_stage(
        db,
        session.id,
        PipelineStage.EFFORT_ESTIMATION,
    )
    db.commit()
    return {
        "ok": True,
        "item": sprint_backlog_service.item_to_dict(item),
    }


# ── Backlog ──────────────────────────────────────────────────


@router.get(
    "/backlog", summary="List sprint backlog items"
)
async def list_backlog(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    x_team_id: Annotated[str | None, Header()] = None,
    project_id: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    session = await run_in_threadpool(
        _get_session,
        db,
        x_team_id,
        project_id,
        user,
        create=False,
    )
    if not session:
        return {"items": []}
    rows = await run_in_threadpool(
        sprint_backlog_service.list_items, db, session.id
    )
    return {
        "items": [
            sprint_backlog_service.item_to_dict(r)
            for r in rows
        ],
    }


@router.post(
    "/backlog", summary="Create a backlog item"
)
async def create_backlog_item(
    body: BacklogItemIn,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    x_team_id: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    session = await run_in_threadpool(
        _require_session, db, x_team_id, None, user
    )
    row = await run_in_threadpool(
        sprint_backlog_service.create_item,
        db,
        session.id,
        _uuid.UUID(body.user_story_id),
        _uuid.UUID(body.requirement_id),
        body.story_points,
        body.description,
        body.hours,
        body.estimation_source,
    )
    db.commit()
    return {
        "ok": True,
        "item": sprint_backlog_service.item_to_dict(row),
    }


@router.patch(
    "/backlog/{item_id}",
    summary="Update a backlog item",
)
async def patch_backlog_item(
    item_id: _uuid.UUID,
    body: BacklogItemPatch,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    patch = body.model_dump(exclude_none=True)
    row = await run_in_threadpool(
        sprint_backlog_service.patch_item, db, item_id, patch
    )
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backlog item not found.",
        )
    db.commit()
    return {
        "ok": True,
        "item": sprint_backlog_service.item_to_dict(row),
    }


@router.delete(
    "/backlog/{item_id}",
    summary="Delete a backlog item",
)
async def delete_backlog_item(
    item_id: _uuid.UUID,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    deleted = await run_in_threadpool(
        sprint_backlog_service.delete_item, db, item_id
    )
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backlog item not found.",
        )
    db.commit()
    return {"ok": True}


# ── Backlog Readiness Passport ────────────────────────────────


@router.get(
    "/passports", summary="List all Backlog Readiness Passports for the session"
)
async def list_passports(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    x_team_id: Annotated[str | None, Header()] = None,
    project_id: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    session = await run_in_threadpool(
        _get_session, db, x_team_id, project_id, user, create=False
    )
    if not session:
        return {"passports": []}
    rows = await run_in_threadpool(
        passport_service.list_passports_for_session, db, session.id
    )
    db.commit()
    return {
        "passports": [passport_service.passport_to_dict(r) for r in rows]
    }


@router.get(
    "/passports/{story_ref}", summary="Get Backlog Readiness Passport for a user story"
)
async def get_story_passport(
    story_ref: str,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    x_team_id: Annotated[str | None, Header()] = None,
    project_id: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    session = await run_in_threadpool(
        _get_session, db, x_team_id, project_id, user, create=False
    )
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active planning session was found.",
        )
    story = await run_in_threadpool(
        decomposition_service.get_story_by_ref, db, session.id, story_ref
    )
    if not story:
        from app.models.decomposition_assessment import UserStory
        from sqlalchemy import func, or_
        # Fallback to case-insensitive match or UUID lookup
        try:
            story_uuid = _uuid.UUID(story_ref)
            story = db.get(UserStory, story_uuid)
        except (ValueError, TypeError):
            story = db.scalars(
                select(UserStory)
                .where(
                    or_(
                        func.lower(UserStory.story_ref) == story_ref.lower(),
                        func.lower(UserStory.legacy_story_ref) == story_ref.lower(),
                    ),
                    UserStory.is_active.is_(True),
                )
            ).first()

        if not story:
            from app.models.requirement import Requirement
            req = db.scalars(
                select(Requirement).where(
                    or_(
                        func.lower(Requirement.requirement_ref) == story_ref.lower(),
                        func.lower(Requirement.legacy_id) == story_ref.lower(),
                    ),
                    Requirement.pipeline_session_id == session.id,
                )
            ).first()
            if not req:
                req = db.scalars(
                    select(Requirement).where(
                        or_(
                            func.lower(Requirement.requirement_ref) == story_ref.lower(),
                            func.lower(Requirement.legacy_id) == story_ref.lower(),
                        ),
                    )
                ).first()
            if req:
                story = db.scalars(
                    select(UserStory)
                    .where(
                        UserStory.requirement_id == req.id,
                        UserStory.is_active.is_(True),
                    )
                    .order_by(UserStory.created_at.asc())
                ).first()

    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User story or requirement '{story_ref}' was not found.",
        )
    row = await run_in_threadpool(
        passport_service.evaluate_story_passport, db, session.id, story.id
    )
    db.commit()
    return {"passport": passport_service.passport_to_dict(row)}


@router.post(
    "/passports/evaluate", summary="Force re-evaluate all Backlog Readiness Passports"
)
async def evaluate_passports(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    x_team_id: Annotated[str | None, Header()] = None,
    project_id: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    session = await run_in_threadpool(
        _require_session, db, x_team_id, project_id, user
    )
    rows = await run_in_threadpool(
        passport_service.list_passports_for_session, db, session.id
    )
    db.commit()
    return {
        "ok": True,
        "count": len(rows),
        "passports": [passport_service.passport_to_dict(r) for r in rows],
    }


# ── DART ─────────────────────────────────────────────────────


@router.post(
    "/dart/arbitrate",
    summary="Trigger DART arbitration",
)
async def dart_arbitrate(
    body: DartArbitrateRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    x_team_id: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    session = await run_in_threadpool(
        _require_session,
        db,
        x_team_id,
        body.project_id,
        user,
    )
    tripped = await run_in_threadpool(
        dart_service.session_circuit_breaker,
        db,
        session.id,
    )
    if tripped:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                "DART circuit breaker: too many open "
                "sessions. Resolve existing ones first."
            ),
        )

    request = OrchestrationRequest(
        requester=user.to_requester(),
        action="planning.arbitrate",
        project_id=str(session.project_id),
        input={
            "requirement": {
                "id": body.requirement.id,
                "text": body.requirement.text,
                "type": body.requirement.type,
            },
            "trigger_reason": body.trigger_reason,
            "source_stage": body.source_stage,
            "source_result": body.source_result,
            "stories": body.stories,
        },
    )
    result = await _orchestrate(request)

    if result:
        try:
            await run_in_threadpool(
                dart_service.create_session,
                db,
                session.id,
                result,
                body.source_stage,
                body.trigger_reason,
            )
            await run_in_threadpool(
                pipeline_session_service.increment_dart_count,
                db,
                session.id,
            )
            db.commit()
        except Exception:
            logger.exception(
                "Failed to persist DART session"
            )

    return result


@router.get(
    "/dart/cases",
    summary="List DART sessions",
)
async def list_dart_sessions(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    x_team_id: Annotated[str | None, Header()] = None,
    project_id: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    session = await run_in_threadpool(
        _get_session,
        db,
        x_team_id,
        project_id,
        user,
        create=False,
    )
    if not session:
        return {"project_id": None, "cases": []}
    rows = await run_in_threadpool(
        dart_service.list_sessions, db, session.id
    )
    return {
        "project_id": str(session.project_id),
        "cases": [
            dart_service.session_to_dict(r) for r in rows
        ],
    }


@router.get(
    "/dart/cases/{session_id}",
    summary="Single DART session with full chain",
)
async def get_dart_session(
    session_id: _uuid.UUID,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    rows = await run_in_threadpool(
        dart_service.list_sessions, db, session_id
    )
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="DART session not found.",
        )
    return dart_service.session_to_dict(rows[0])


@router.patch(
    "/dart/cases/{dart_session_id}/resolve",
    summary="Resolve a DART session",
)
async def resolve_dart_session(
    dart_session_id: _uuid.UUID,
    body: DartResolveRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    row = await run_in_threadpool(
        dart_service.resolve_session,
        db,
        dart_session_id,
        body.status,
        user.user_id,
    )
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="DART session not found.",
        )
    db.commit()
    return {
        "ok": True,
        "id": str(dart_session_id),
        "status": body.status,
    }


# ── Feedback & instructor alerts ─────────────────────────────


@router.get(
    "/feedback", summary="List feedback for session"
)
async def list_feedback(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    x_team_id: Annotated[str | None, Header()] = None,
    project_id: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    session = await run_in_threadpool(
        _get_session,
        db,
        x_team_id,
        project_id,
        user,
        create=False,
    )
    if not session:
        return {"feedback": []}
    user_db_id = await run_in_threadpool(
        _resolve_user_db_id, db, user
    )
    rows = await run_in_threadpool(
        feedback_service.list_feedback,
        db,
        session.id,
        user_db_id,
    )
    return {
        "feedback": [
            feedback_service.feedback_to_dict(r)
            for r in rows
        ],
    }


@router.patch(
    "/feedback/{feedback_id}/view",
    summary="Mark feedback as viewed",
)
async def mark_feedback_viewed(
    feedback_id: _uuid.UUID,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    row = await run_in_threadpool(
        feedback_service.mark_viewed, db, feedback_id
    )
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found.",
        )
    db.commit()
    return {"ok": True}


@router.get(
    "/instructor/alerts",
    summary="List instructor alerts",
)
async def list_instructor_alerts(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    resolved: Annotated[bool | None, Query()] = None,
) -> dict[str, Any]:
    user_db_id = await run_in_threadpool(
        _resolve_user_db_id, db, user
    )
    if not user_db_id:
        return {"alerts": []}
    rows = await run_in_threadpool(
        feedback_service.list_alerts,
        db,
        user_db_id,
        resolved,
    )
    return {
        "alerts": [
            feedback_service.alert_to_dict(r) for r in rows
        ],
    }


@router.patch(
    "/instructor/alerts/{alert_id}",
    summary="Resolve an instructor alert",
)
async def resolve_instructor_alert(
    alert_id: _uuid.UUID,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    notes: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    user_db_id = await run_in_threadpool(
        _resolve_user_db_id, db, user
    )
    if not user_db_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found.",
        )
    row = await run_in_threadpool(
        feedback_service.resolve_alert,
        db,
        alert_id,
        user_db_id,
        notes,
    )
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found.",
        )
    db.commit()
    return {"ok": True}


# ── Jira Integration ─────────────────────────────────────────


@router.get(
    "/jira/status",
    summary="Check Jira connection and configuration status",
)
async def get_jira_status(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    base_url: Annotated[str | None, Query()] = None,
    email: Annotated[str | None, Query()] = None,
    project_key: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    overrides: dict[str, Any] = {}
    if base_url:
        overrides["base_url"] = base_url
    if email:
        overrides["email"] = email
    if project_key:
        overrides["project_key"] = project_key
    return await jira_service.check_jira_status(overrides)


@router.post(
    "/jira/sync/backlog",
    summary="Push validated backlog (Epics, Stories, Story Points, Subtasks) to Jira",
)
async def sync_backlog_to_jira(
    body: JiraSyncIn,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    x_team_id: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    session = await run_in_threadpool(
        _require_session, db, x_team_id, body.project_id, user
    )
    overrides = body.model_dump(exclude_none=True)
    client = jira_service.get_jira_client(overrides)
    result = await jira_service.sync_backlog_to_jira(
        db,
        session.id,
        client,
        force_resync=body.force_resync,
        story_refs=body.story_refs,
        story_points=body.story_points,
    )
    return result


@router.post(
    "/jira/reset-links",
    summary="Clear all Jira issue/epic/sprint links from the database to allow a fresh push",
)
async def reset_jira_links(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    x_team_id: Annotated[str | None, Header()] = None,
    project_id: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    session = await run_in_threadpool(
        _require_session, db, x_team_id, project_id, user
    )
    result = await jira_service.clear_jira_keys(db, session.id)
    return result


@router.post(
    "/jira/sync/sprint",
    summary="Create active sprint on Jira Scrum board and assign estimated stories",
)
async def sync_sprint_to_jira(
    body: JiraSprintSyncIn,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    x_team_id: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    session = await run_in_threadpool(
        _require_session, db, x_team_id, body.project_id, user
    )
    overrides = body.model_dump(exclude_none=True)
    client = jira_service.get_jira_client(overrides)
    result = await jira_service.sync_sprint_to_jira(db, session.id, client, body.sprint_id)
    return result


@router.post(
    "/jira/fetch",
    summary="Fetch current execution data from linked Jira sprint, stories, and subtasks",
)
async def fetch_jira_execution(
    body: JiraFetchIn,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    x_team_id: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    session = await run_in_threadpool(
        _require_session, db, x_team_id, body.project_id, user
    )
    overrides = body.model_dump(exclude_none=True)
    client = jira_service.get_jira_client(overrides)
    return await jira_service.fetch_linked_jira_execution(db, session.id, client)


@router.post(
    "/jira/transition",
    summary="Transition Jira issue status and update local DB row",
)
async def transition_jira_issue(
    body: JiraTransitionIn,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    x_team_id: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    session = await run_in_threadpool(
        _require_session, db, x_team_id, body.project_id, user
    )
    overrides = body.model_dump(exclude_none=True)
    client = jira_service.get_jira_client(overrides)
    return await jira_service.transition_jira_issue(
        db, session.id, client, body.issue_key, body.target_status,
        body.acceptance_criteria_confirmed,
    )

