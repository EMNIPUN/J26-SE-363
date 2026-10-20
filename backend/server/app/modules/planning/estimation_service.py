"""Persistence for student effort estimates and comparisons."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.decomposition_assessment import UserStory
from app.models.effort_estimation import (
    EstimateComparison,
    StudentEffortEstimate,
)
from app.models.enums import EstimationTechnique, StoryStatus

TECHNIQUE_MAP = {
    "planning_poker": EstimationTechnique.PLANNING_POKER,
    "t_shirt": EstimationTechnique.T_SHIRT,
    "fibonacci": EstimationTechnique.FIBONACCI,
    "expert_judgment": EstimationTechnique.EXPERT_JUDGMENT,
}


def save_student_estimate(
    db: Session,
    story_id: uuid.UUID,
    session_id: uuid.UUID,
    user_id: uuid.UUID | None,
    story_points: int,
    hours: float | None = None,
    basis: str | None = None,
    technique: str = "fibonacci",
) -> StudentEffortEstimate:
    story = db.get(UserStory, story_id)
    if story:
        story.student_story_points = story_points
        if story.status != StoryStatus.IN_BACKLOG:
            story.status = StoryStatus.ESTIMATED

    existing = db.scalars(
        select(StudentEffortEstimate)
        .where(
            StudentEffortEstimate.user_story_id == story_id,
            StudentEffortEstimate.pipeline_session_id == session_id,
        )
        .options(selectinload(StudentEffortEstimate.user_story))
    ).first()
    if existing:
        existing.estimated_story_points = story_points
        existing.estimated_hours = hours
        existing.estimation_basis = basis
        existing.estimation_technique = TECHNIQUE_MAP.get(
            technique, EstimationTechnique.FIBONACCI
        )
        if user_id:
            existing.estimated_by = user_id
        db.flush()
        try:
            from app.modules.planning.passport_service import evaluate_story_passport
            evaluate_story_passport(db, session_id, story_id)
        except Exception:
            pass
        return existing

    row = StudentEffortEstimate(
        user_story_id=story_id,
        pipeline_session_id=session_id,
        estimated_by=user_id,
        estimated_story_points=story_points,
        estimated_hours=hours,
        estimation_basis=basis,
        estimation_technique=TECHNIQUE_MAP.get(
            technique, EstimationTechnique.FIBONACCI
        ),
    )
    db.add(row)
    db.flush()
    if story:
        row.user_story = story
    try:
        from app.modules.planning.passport_service import evaluate_story_passport
        evaluate_story_passport(db, session_id, story_id)
    except Exception:
        pass
    return row


def save_comparison(
    db: Session,
    story_id: uuid.UUID,
    session_id: uuid.UUID,
    user_id: uuid.UUID | None,
    final_story_points: int,
    final_hours: float | None = None,
    basis: str | None = None,
    student_estimate_id: uuid.UUID | None = None,
) -> EstimateComparison:
    row = EstimateComparison(
        user_story_id=story_id,
        pipeline_session_id=session_id,
        student_estimate_id=student_estimate_id,
        decided_by=user_id,
        final_story_points=final_story_points,
        final_hours=final_hours,
        final_decision_basis=basis,
    )
    db.add(row)
    db.flush()
    return row


def list_estimates(
    db: Session, session_id: uuid.UUID
) -> list[StudentEffortEstimate]:
    return list(
        db.scalars(
            select(StudentEffortEstimate)
            .where(
                StudentEffortEstimate.pipeline_session_id == session_id,
            )
            .options(selectinload(StudentEffortEstimate.user_story))
            .order_by(StudentEffortEstimate.created_at.asc())
        ).all()
    )


def estimate_to_dict(
    row: StudentEffortEstimate,
) -> dict[str, Any]:
    story_ref = row.user_story.story_ref if row.user_story else None
    return {
        "id": str(row.id),
        "user_story_id": str(row.user_story_id),
        "story_ref": story_ref,
        "story_points": row.estimated_story_points,
        "estimated_story_points": row.estimated_story_points,
        "final_story_points": row.estimated_story_points,
        "estimated_hours": (
            float(row.estimated_hours)
            if row.estimated_hours is not None
            else None
        ),
        "estimation_basis": row.estimation_basis,
        "estimation_technique": (
            row.estimation_technique.value
            if hasattr(row.estimation_technique, "value")
            else str(row.estimation_technique)
        ),
        "status": (
            row.user_story.status.value
            if row.user_story and hasattr(row.user_story.status, "value")
            else "estimated"
        ),
        "confirmed": (
            row.user_story.status in (StoryStatus.ESTIMATED, StoryStatus.IN_BACKLOG)
            if row.user_story
            else True
        ),
        "created_at": (
            row.created_at.isoformat()
            if row.created_at
            else None
        ),
        "updated_at": (
            row.updated_at.isoformat()
            if row.updated_at
            else None
        ),
    }
