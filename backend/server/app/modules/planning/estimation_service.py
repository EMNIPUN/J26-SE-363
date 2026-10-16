"""Persistence for student effort estimates and comparisons."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.effort_estimation import (
    EstimateComparison,
    StudentEffortEstimate,
)
from app.models.enums import EstimationTechnique

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
    existing = db.scalars(
        select(StudentEffortEstimate).where(
            StudentEffortEstimate.user_story_id == story_id,
            StudentEffortEstimate.pipeline_session_id == session_id,
        )
    ).first()
    if existing:
        existing.estimated_story_points = story_points
        existing.estimated_hours = hours
        existing.estimation_basis = basis
        existing.estimation_technique = TECHNIQUE_MAP.get(
            technique, EstimationTechnique.FIBONACCI
        )
        db.flush()
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
            select(StudentEffortEstimate).where(
                StudentEffortEstimate.pipeline_session_id
                == session_id,
            )
        ).all()
    )


def estimate_to_dict(
    row: StudentEffortEstimate,
) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "user_story_id": str(row.user_story_id),
        "estimated_story_points": row.estimated_story_points,
        "estimated_hours": (
            float(row.estimated_hours)
            if row.estimated_hours is not None
            else None
        ),
        "estimation_basis": row.estimation_basis,
        "estimation_technique": row.estimation_technique.value,
        "created_at": (
            row.created_at.isoformat()
            if row.created_at
            else None
        ),
    }
