"""Pipeline session lifecycle management."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import PipelineStage, SessionStatus
from app.models.pipeline_session import PipelineSession


def get_or_create_session(
    db: Session,
    project_id: uuid.UUID,
    group_id: uuid.UUID,
    user_id: uuid.UUID,
) -> PipelineSession:
    row = db.scalars(
        select(PipelineSession).where(
            PipelineSession.project_id == project_id,
            PipelineSession.group_id == group_id,
            PipelineSession.status == SessionStatus.ACTIVE,
        )
    ).first()
    if row:
        return row

    max_ver = db.scalar(
        select(
            PipelineSession.version
        ).where(
            PipelineSession.group_id == group_id,
        ).order_by(PipelineSession.version.desc())
    ) or 0

    row = PipelineSession(
        project_id=project_id,
        group_id=group_id,
        initiated_by=user_id,
        version=max_ver + 1,
    )
    db.add(row)
    db.flush()
    return row


def get_session(
    db: Session, session_id: uuid.UUID
) -> PipelineSession | None:
    return db.get(PipelineSession, session_id)


def get_active_session(
    db: Session,
    project_id: uuid.UUID,
    group_id: uuid.UUID,
) -> PipelineSession | None:
    return db.scalars(
        select(PipelineSession).where(
            PipelineSession.project_id == project_id,
            PipelineSession.group_id == group_id,
            PipelineSession.status == SessionStatus.ACTIVE,
        )
    ).first()


def advance_stage(
    db: Session,
    session_id: uuid.UUID,
    stage: PipelineStage,
) -> None:
    row = db.get(PipelineSession, session_id)
    if row:
        row.current_stage = stage
        db.flush()


def increment_dart_count(
    db: Session, session_id: uuid.UUID
) -> None:
    row = db.get(PipelineSession, session_id)
    if row:
        row.dart_activation_count += 1
        db.flush()


def complete_session(
    db: Session,
    session_id: uuid.UUID,
    composite_score: float | None = None,
) -> None:
    row = db.get(PipelineSession, session_id)
    if row:
        row.status = SessionStatus.COMPLETED
        row.overall_composite_score = composite_score
        from datetime import datetime, timezone

        row.completed_at = datetime.now(timezone.utc)
        db.flush()


def session_to_dict(row: PipelineSession) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "group_id": str(row.group_id),
        "project_id": str(row.project_id),
        "current_stage": row.current_stage.value,
        "status": row.status.value,
        "version": row.version,
        "dart_activation_count": row.dart_activation_count,
        "overall_composite_score": (
            float(row.overall_composite_score)
            if row.overall_composite_score is not None
            else None
        ),
        "started_at": (
            row.started_at.isoformat() if row.started_at else None
        ),
        "completed_at": (
            row.completed_at.isoformat()
            if row.completed_at
            else None
        ),
    }
