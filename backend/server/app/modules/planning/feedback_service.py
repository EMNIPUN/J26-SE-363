"""Persistence for feedback and instructor alerts."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.feedback import Feedback
from app.models.instructor_alert import InstructorAlert


def list_feedback(
    db: Session,
    session_id: uuid.UUID,
    user_id: uuid.UUID | None = None,
) -> list[Feedback]:
    q = select(Feedback).where(
        Feedback.pipeline_session_id == session_id,
    )
    if user_id:
        q = q.where(Feedback.target_user_id == user_id)
    return list(
        db.scalars(q.order_by(Feedback.created_at.desc())).all()
    )


def mark_viewed(
    db: Session, feedback_id: uuid.UUID
) -> Feedback | None:
    row = db.get(Feedback, feedback_id)
    if not row:
        return None
    row.is_viewed = True
    row.viewed_at = datetime.now(timezone.utc)
    db.flush()
    return row


def list_alerts(
    db: Session,
    instructor_id: uuid.UUID,
    resolved: bool | None = None,
) -> list[InstructorAlert]:
    q = select(InstructorAlert).where(
        InstructorAlert.target_instructor_id == instructor_id,
    )
    if resolved is not None:
        q = q.where(InstructorAlert.is_resolved == resolved)
    return list(
        db.scalars(
            q.order_by(InstructorAlert.created_at.desc())
        ).all()
    )


def resolve_alert(
    db: Session,
    alert_id: uuid.UUID,
    resolved_by: uuid.UUID,
    notes: str | None = None,
) -> InstructorAlert | None:
    row = db.get(InstructorAlert, alert_id)
    if not row:
        return None
    row.is_resolved = True
    row.resolved_by = resolved_by
    row.resolved_at = datetime.now(timezone.utc)
    row.resolution_notes = notes
    db.flush()
    return row


def feedback_to_dict(row: Feedback) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "feedback_stage": row.feedback_stage.value,
        "feedback_type": row.feedback_type.value,
        "feedback_text": row.feedback_text,
        "severity": row.severity.value,
        "is_dart_generated": row.is_dart_generated,
        "is_viewed": row.is_viewed,
        "is_acted_upon": row.is_acted_upon,
        "created_at": (
            row.created_at.isoformat()
            if row.created_at
            else None
        ),
    }


def alert_to_dict(row: InstructorAlert) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "alert_type": row.alert_type,
        "severity": row.severity.value,
        "title": row.title,
        "description": row.description,
        "is_read": row.is_read,
        "is_resolved": row.is_resolved,
        "resolution_notes": row.resolution_notes,
        "created_at": (
            row.created_at.isoformat()
            if row.created_at
            else None
        ),
        "resolved_at": (
            row.resolved_at.isoformat()
            if row.resolved_at
            else None
        ),
    }
