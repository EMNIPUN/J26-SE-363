"""Persistence for decomposition analysis — unpacks the agent's two-level-gate
JSON into decomposition_assessments, coverage_elements, coverage_gate_checks,
story_assessments, invest_validations, and student feedback rows.

Each analysis run creates a NEW DecompositionAssessment row (there is no
per-requirement uniqueness constraint — see the model docstring): re-running
analysis is always safe and preserves history instead of colliding."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.decomposition_assessment import (
    CoverageAnalysisResult,
    CoverageElementRow,
    CoverageGateCheckRow,
    DecompositionAssessment,
    DecompositionToolOutput,
    InvestValidation,
    StoryAssessment,
    UserStory,
    UserStoryTask,
)
from app.models.enums import (
    AssessmentStatus,
    CheckResult,
    ConfidenceLevel,
    CoverageElementType,
    CoverageResult,
    DecompositionGateStatus,
    DecompositionTaskType,
    FeedbackStage,
    FeedbackType,
    InvestCriterion,
    InvestResult,
    Priority,
    QualityBand,
    StoryStatus,
    ToolStatus,
)
from app.models.feedback import Feedback

logger = logging.getLogger(__name__)

INVEST_CRITERIA = [c.value for c in InvestCriterion]

CONFIDENCE_MAP = {
    "high": ConfidenceLevel.HIGH,
    "moderate": ConfidenceLevel.MODERATE,
    "low": ConfidenceLevel.LOW,
}

PRIORITY_MAP = {
    "critical": Priority.CRITICAL,
    "high": Priority.HIGH,
    "medium": Priority.MEDIUM,
    "low": Priority.LOW,
}

_RECOMMENDED_ACTION = {
    "COMPLETE": "Proceed to effort estimation",
    "NEEDS_REVIEW": "Send to supervisor for review",
    "INCOMPLETE": "Revise stories and re-run analysis",
}


def _confidence_level(value: Any) -> ConfidenceLevel:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return ConfidenceLevel.MODERATE
    if score >= 0.8:
        return ConfidenceLevel.HIGH
    if score >= 0.5:
        return ConfidenceLevel.MODERATE
    return ConfidenceLevel.LOW


# --- User Story CRUD ----------------------------------------------------------


def create_story(
    db: Session,
    requirement_id: uuid.UUID,
    session_id: uuid.UUID,
    story_data: dict[str, Any],
    authored_by: uuid.UUID | None = None,
) -> UserStory:
    story_ref = story_data["story_ref"]

    row = UserStory(
        requirement_id=requirement_id,
        pipeline_session_id=session_id,
        authored_by=authored_by,
        story_ref=story_ref,
        title=story_data.get("title", "Untitled"),
        as_a=story_data.get("as_a"),
        i_want=story_data.get("i_want"),
        so_that=story_data.get("so_that"),
        description=story_data.get("description"),
        acceptance_criteria=story_data.get("acceptance_criteria"),
        priority=PRIORITY_MAP.get(
            (story_data.get("priority") or "medium").lower(),
            Priority.MEDIUM,
        ),
    )
    db.add(row)
    db.flush()
    return row


def list_stories(db: Session, session_id: uuid.UUID) -> list[UserStory]:
    return list(
        db.scalars(
            select(UserStory)
            .where(
                UserStory.pipeline_session_id == session_id,
                UserStory.is_active.is_(True),
            )
            .options(
                selectinload(UserStory.invest_validations).selectinload(
                    InvestValidation.decomposition_assessment
                ),
                selectinload(UserStory.tasks),
            )
            .order_by(UserStory.story_ref)
        ).all()
    )


def get_story_by_ref(
    db: Session, session_id: uuid.UUID, story_ref: str
) -> UserStory | None:
    return db.scalars(
        select(UserStory)
        .where(
            UserStory.pipeline_session_id == session_id,
            UserStory.story_ref == story_ref,
            UserStory.is_active.is_(True),
        )
        .options(
            selectinload(UserStory.invest_validations).selectinload(
                InvestValidation.decomposition_assessment
            ),
            selectinload(UserStory.tasks),
        )
    ).first()


def delete_story(db: Session, session_id: uuid.UUID, story_ref: str) -> bool:
    row = get_story_by_ref(db, session_id, story_ref)
    if not row:
        return False
    row.is_active = False
    db.flush()
    return True


def create_task(
    db: Session,
    story: UserStory,
    title: str,
    parent_task_id: uuid.UUID | None = None,
) -> UserStoryTask:
    if parent_task_id:
        parent = db.get(UserStoryTask, parent_task_id)
        if not parent or parent.user_story_id != story.id or parent.task_type != DecompositionTaskType.TASK:
            raise ValueError("Parent task not found for this story.")
    row = UserStoryTask(
        user_story_id=story.id,
        parent_task_id=parent_task_id,
        title=title,
        task_type=(
            DecompositionTaskType.SUBTASK
            if parent_task_id
            else DecompositionTaskType.TASK
        ),
    )
    db.add(row)
    db.flush()
    return row


def set_story_status(story: UserStory, status: StoryStatus) -> None:
    story.status = status
    story.edited_at = datetime.now(UTC)


# --- Decomposition assessment --------------------------------------------------


def save_assessment(
    db: Session,
    requirement_id: uuid.UUID,
    session_id: uuid.UUID,
    agent_result: dict[str, Any],
    stories: list[UserStory] | None = None,
    target_user_id: uuid.UUID | None = None,
) -> DecompositionAssessment:
    """Unpack one ``DecompositionResult`` (agent.py schemas.py shape) into the
    normalized tables. ``agent_result`` field names must match
    DecompositionResult exactly — see schemas.py in the agentic framework."""
    cov = agent_result.get("coverage") or {}
    gate = cov.get("gate") or {}
    invest_gate = agent_result.get("invest_gate") or {}
    story_results = agent_result.get("stories") or []
    gate_status = agent_result.get("gate_status", "INCOMPLETE")

    assessment = DecompositionAssessment(
        requirement_id=requirement_id,
        pipeline_session_id=session_id,
        gate_status=DecompositionGateStatus(gate_status),
        decomposition_quality_score=agent_result.get(
            "decomposition_quality_score", 0.0
        ),
        quality_band=QualityBand(agent_result.get("quality_band", "Very poor")),
        needs_review_reason=agent_result.get("needs_review_reason"),
        analysis_failed=bool(agent_result.get("analysis_failed", False)),
        failure_reason=agent_result.get("failure_reason"),
        coverage_score=cov.get("coverage_percentage", 0.0),
        stories_evaluated=len(story_results),
        stories_needing_revision=len(invest_gate.get("failed_stories") or []),
        diagnosis=(agent_result.get("student_feedback") or [None])[0],
        recommended_action=_RECOMMENDED_ACTION.get(gate_status),
        confidence_level=_confidence_level(agent_result.get("confidence", 0.8)),
        assessment_status=AssessmentStatus.COMPLETED,
        assessed_at=datetime.now(UTC),
    )
    db.add(assessment)
    db.flush()

    db.add(
        CoverageAnalysisResult(
            decomposition_assessment_id=assessment.id,
            requirement_id=requirement_id,
            overall_coverage_percentage=cov.get("coverage_percentage", 0.0),
        )
    )

    for check_id, check in (gate.get("checks") or {}).items():
        try:
            result = CheckResult(check.get("result", "Fail"))
        except ValueError:
            result = CheckResult.FAIL
        db.add(
            CoverageGateCheckRow(
                decomposition_assessment_id=assessment.id,
                check_id=check_id,
                result=result,
                rationale=check.get("rationale"),
            )
        )

    duplicate_ids = set(gate.get("duplicate_elements") or [])
    for el in cov.get("elements") or []:
        try:
            element_type = CoverageElementType(el.get("element_type"))
        except ValueError:
            element_type = CoverageElementType.MAIN_ACTION
        try:
            coverage_result = CoverageResult(el.get("coverage_result", "Missing"))
        except ValueError:
            coverage_result = CoverageResult.MISSING
        db.add(
            CoverageElementRow(
                decomposition_assessment_id=assessment.id,
                element_type=element_type,
                description=el.get("description", ""),
                required=bool(el.get("required", True)),
                covered_by=el.get("covered_by") or [],
                coverage_result=coverage_result,
                is_duplicate=el.get("element_id") in duplicate_ids,
                evidence=el.get("evidence"),
            )
        )

    story_map = {s.story_ref: s for s in (stories or [])}
    unmatched: list[str] = []
    for si in story_results:
        sid = si.get("story_id", "")
        story_row = story_map.get(sid)
        if not story_row:
            unmatched.append(sid)
            continue

        db.add(
            StoryAssessment(
                decomposition_assessment_id=assessment.id,
                user_story_id=story_row.id,
                story_ready=bool(si.get("story_ready", False)),
                coverage_percentage=si.get("coverage_percentage"),
            )
        )
        if story_row.status in (StoryStatus.DRAFT, StoryStatus.INVEST_PASSED):
            story_row.status = (
                StoryStatus.INVEST_PASSED
                if bool(si.get("story_ready", False))
                else StoryStatus.DRAFT
            )
        for criterion_name in INVEST_CRITERIA:
            c = si.get(criterion_name) or {}
            try:
                result = InvestResult(c.get("result", "Cannot Assess"))
            except ValueError:
                result = InvestResult.CANNOT_ASSESS
            db.add(
                InvestValidation(
                    decomposition_assessment_id=assessment.id,
                    user_story_id=story_row.id,
                    pipeline_session_id=session_id,
                    criterion=InvestCriterion(criterion_name),
                    result=result,
                    is_satisfied=result
                    in (InvestResult.PASS, InvestResult.PASS_WITH_NOTE),
                    score={
                        "Pass": 1.0, "Pass with note": 0.75, "Fail": 0.0,
                    }.get(result.value),
                    justification=(
                        f"{c.get('note', '')} {c.get('evidence', '')}".strip()
                        or None
                    ),
                )
            )

    if unmatched:
        logger.warning(
            "save_assessment: %d story_id(s) from the agent had no matching "
            "UserStory (requirement=%s, session=%s): %s",
            len(unmatched), requirement_id, session_id, unmatched,
        )
        note = f" [{len(unmatched)} story result(s) unmatched to a saved story]"
        assessment.diagnosis = (assessment.diagnosis or "") + note

    tools = agent_result.get("tool_outputs") or []
    for idx, tool in enumerate(tools):
        db.add(
            DecompositionToolOutput(
                decomposition_assessment_id=assessment.id,
                tool_name=tool.get("tool_name", f"tool_{idx}"),
                execution_order=idx,
                input_summary=tool.get("input_summary"),
                output_data=tool.get("output_data"),
                confidence_score=tool.get("confidence_score"),
                execution_time_ms=tool.get("execution_time_ms"),
                status=ToolStatus(tool.get("status", "success")),
                error_message=tool.get("error_message"),
            )
        )

    if target_user_id:
        feedback_type = (
            FeedbackType.ACTIONABLE_IMPROVEMENT
            if gate_status == "COMPLETE"
            else FeedbackType.REVISION_REQUIRED
        )
        for bullet in agent_result.get("student_feedback") or []:
            db.add(
                Feedback(
                    pipeline_session_id=session_id,
                    requirement_id=requirement_id,
                    decomposition_assessment_id=assessment.id,
                    target_user_id=target_user_id,
                    feedback_stage=FeedbackStage.DECOMPOSITION,
                    feedback_type=feedback_type,
                    feedback_text=bullet,
                )
            )

    db.flush()
    return assessment


def get_assessments(
    db: Session,
    session_id: uuid.UUID,
    *,
    latest_only: bool = True,
) -> list[DecompositionAssessment]:
    assessments = list(
        db.scalars(
            select(DecompositionAssessment)
            .where(DecompositionAssessment.pipeline_session_id == session_id)
            .options(
                selectinload(DecompositionAssessment.coverage_analysis),
                selectinload(DecompositionAssessment.tool_outputs),
                selectinload(DecompositionAssessment.coverage_elements),
                selectinload(DecompositionAssessment.gate_checks),
                selectinload(DecompositionAssessment.story_assessments).selectinload(
                    StoryAssessment.user_story
                ),
                selectinload(DecompositionAssessment.invest_validations),
                selectinload(DecompositionAssessment.feedbacks),
            )
            .order_by(
                DecompositionAssessment.requirement_id,
                DecompositionAssessment.assessed_at.desc(),
            )
        ).all()
    )
    if not latest_only:
        return assessments

    latest: dict[uuid.UUID, DecompositionAssessment] = {}
    for assessment in assessments:
        latest.setdefault(assessment.requirement_id, assessment)
    return list(latest.values())


def get_latest_assessment_for_requirement(
    db: Session, session_id: uuid.UUID, requirement_id: uuid.UUID
) -> DecompositionAssessment | None:
    return db.scalars(
        select(DecompositionAssessment)
        .where(
            DecompositionAssessment.pipeline_session_id == session_id,
            DecompositionAssessment.requirement_id == requirement_id,
        )
        .options(
            selectinload(DecompositionAssessment.coverage_analysis),
            selectinload(DecompositionAssessment.tool_outputs),
            selectinload(DecompositionAssessment.coverage_elements),
            selectinload(DecompositionAssessment.gate_checks),
            selectinload(DecompositionAssessment.story_assessments).selectinload(
                StoryAssessment.user_story
            ),
            selectinload(DecompositionAssessment.invest_validations),
            selectinload(DecompositionAssessment.feedbacks),
        )
        .order_by(DecompositionAssessment.assessed_at.desc())
    ).first()


def get_gate_status(
    db: Session, session_id: uuid.UUID, requirement_id: uuid.UUID | None = None
) -> DecompositionAssessment | None:
    """Latest decomposition assessment for the session (optionally scoped to
    one requirement) — the decomposition analog of quality_service's
    get_gate_decision, mirrored by GET /planning/decomposition/gate."""
    if requirement_id is not None:
        return get_latest_assessment_for_requirement(db, session_id, requirement_id)
    rows = get_assessments(db, session_id, latest_only=True)
    if not rows:
        return None
    return max(rows, key=lambda r: r.assessed_at or r.created_at)


# --- Serialization -------------------------------------------------------------

_CRITERIA_FIELDS = (
    "independent", "negotiable", "valuable", "estimable", "small", "testable",
)


def story_to_dict(row: UserStory) -> dict[str, Any]:
    """Serialize the story with INVEST verdicts from its latest analysis run."""
    invest: dict[str, dict[str, Any]] = {}
    validations = row.invest_validations
    latest_assessment_id: uuid.UUID | None = None
    if validations:
        latest_validation = max(
            validations,
            key=lambda validation: (
                validation.decomposition_assessment.assessed_at
                or validation.decomposition_assessment.created_at
            ),
        )
        latest_assessment_id = latest_validation.decomposition_assessment_id
    for iv in sorted(validations, key=lambda v: v.criterion.value):
        if iv.decomposition_assessment_id != latest_assessment_id:
            continue
        invest[iv.criterion.value] = {
            "pass": iv.is_satisfied,
            "result": iv.result.value,
            "score": float(iv.score) if iv.score is not None else None,
            "note": iv.justification,
        }
    invest_result = None
    if invest:
        invest_result = {
            **{c: invest.get(c) for c in _CRITERIA_FIELDS},
            "overallPass": all(
                (invest.get(c) or {}).get("pass") for c in _CRITERIA_FIELDS
            ),
        }
    task_rows = sorted(row.tasks, key=lambda task: task.created_at)
    children: dict[uuid.UUID, list[UserStoryTask]] = {}
    for task in task_rows:
        if task.parent_task_id:
            children.setdefault(task.parent_task_id, []).append(task)

    def task_to_dict(task: UserStoryTask) -> dict[str, Any]:
        return {
            "id": str(task.id),
            "title": task.title,
            "task_type": task.task_type.value,
            "status": task.status.value,
            "subtasks": [task_to_dict(child) for child in children.get(task.id, [])],
        }

    return {
        "id": row.story_ref,
        "story_ref": row.story_ref,
        "requirement_ref": str(row.requirement_id),
        "title": row.title,
        "as_a": row.as_a,
        "i_want": row.i_want,
        "so_that": row.so_that,
        "description": row.description,
        "acceptance_criteria": row.acceptance_criteria,
        "student_story_points": row.student_story_points,
        "priority": row.priority.value,
        "status": row.status.value,
        "tasks": [task_to_dict(task) for task in task_rows if task.parent_task_id is None],
        "investResult": invest_result,
        "db_id": str(row.id),
        "edited_at": row.edited_at.isoformat() if row.edited_at else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def assessment_to_dict(row: DecompositionAssessment) -> dict[str, Any]:
    """The single, unified shape returned by both POST and GET
    /planning/decomposition — the frontend adapter only has one shape to
    handle regardless of which endpoint populated it."""
    checks = [
        {"check_id": c.check_id, "result": c.result.value, "rationale": c.rationale}
        for c in sorted(row.gate_checks, key=lambda c: c.check_id)
    ]
    elements = [
        {
            "element_type": e.element_type.value,
            "description": e.description,
            "required": e.required,
            "covered_by": e.covered_by or [],
            "coverage_result": e.coverage_result.value,
            "is_duplicate": e.is_duplicate,
            "evidence": e.evidence,
        }
        for e in row.coverage_elements
    ]

    invest_by_story: dict[uuid.UUID, dict[str, Any]] = {}
    for iv in row.invest_validations:
        invest_by_story.setdefault(iv.user_story_id, {})[iv.criterion.value] = {
            "result": iv.result.value,
            "note": iv.justification,
        }

    stories = []
    for sa in row.story_assessments:
        criteria = invest_by_story.get(sa.user_story_id, {})
        stories.append(
            {
                "story_ref": sa.user_story.story_ref if sa.user_story else None,
                "story_ready": sa.story_ready,
                "coverage_percentage": (
                    float(sa.coverage_percentage)
                    if sa.coverage_percentage is not None
                    else None
                ),
                **{c: criteria.get(c) for c in _CRITERIA_FIELDS},
            }
        )

    cov = row.coverage_analysis
    tools = [
        {
            "tool_name": t.tool_name,
            "output_data": t.output_data,
            "confidence_score": (
                float(t.confidence_score) if t.confidence_score is not None else None
            ),
            "status": t.status.value,
        }
        for t in sorted(row.tool_outputs, key=lambda x: x.execution_order)
    ]
    student_feedback = [
        f.feedback_text
        for f in sorted(row.feedbacks, key=lambda f: f.created_at)
    ]

    return {
        "requirement_id": str(row.requirement_id),
        "gate_status": row.gate_status.value,
        "decomposition_quality_score": float(row.decomposition_quality_score),
        "quality_band": row.quality_band.value,
        "needs_review_reason": row.needs_review_reason,
        "analysis_failed": row.analysis_failed,
        "failure_reason": row.failure_reason,
        "confidence": row.confidence_level.value,
        "diagnosis": row.diagnosis,
        "recommended_action": row.recommended_action,
        "coverage": {
            "coverage_percentage": (
                float(cov.overall_coverage_percentage) if cov else 0.0
            ),
            "elements": elements,
            "checks": checks,
        },
        "stories": stories,
        "student_feedback": student_feedback,
        "tool_outputs": tools,
        "stories_evaluated": row.stories_evaluated,
        "stories_needing_revision": row.stories_needing_revision,
        "assessed_at": row.assessed_at.isoformat() if row.assessed_at else None,
    }


def gate_to_dict(row: DecompositionAssessment) -> dict[str, Any]:
    return {
        "requirement_id": str(row.requirement_id),
        "gate_status": row.gate_status.value,
        "decomposition_quality_score": float(row.decomposition_quality_score),
        "quality_band": row.quality_band.value,
        "needs_review_reason": row.needs_review_reason,
        "analysis_failed": row.analysis_failed,
        "failure_reason": row.failure_reason,
        "assessed_at": row.assessed_at.isoformat() if row.assessed_at else None,
    }
