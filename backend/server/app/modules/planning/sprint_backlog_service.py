"""Persistence for sprint backlog items (replaces sprint_task_service)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.models.enums import (
    EstimationSource,
    Priority,
    TaskStatus,
)
from app.models.sprint_backlog import SprintBacklogItem

STATUS_MAP = {
    s.value: s for s in TaskStatus
}
PRIORITY_MAP = {
    p.value: p for p in Priority
}


def create_item(
    db: Session,
    session_id: uuid.UUID,
    user_story_id: uuid.UUID,
    requirement_id: uuid.UUID,
    story_points: int,
    description: str | None = None,
    hours: float | None = None,
    estimation_source: str = "student_only",
) -> SprintBacklogItem:
    existing = db.scalars(
        select(SprintBacklogItem).where(
            SprintBacklogItem.pipeline_session_id == session_id,
            SprintBacklogItem.user_story_id == user_story_id,
        )
    ).first()
    if existing:
        return existing
    row = SprintBacklogItem(
        pipeline_session_id=session_id,
        user_story_id=user_story_id,
        requirement_id=requirement_id,
        final_story_points=story_points,
        final_estimated_hours=hours,
        task_description=description,
        estimation_source=EstimationSource(estimation_source),
    )
    db.add(row)
    db.flush()
    return row


def list_items(
    db: Session, session_id: uuid.UUID
) -> list[SprintBacklogItem]:
    return list(
        db.scalars(
            select(SprintBacklogItem)
            .where(
                SprintBacklogItem.pipeline_session_id == session_id,
            )
            .options(
                selectinload(SprintBacklogItem.user_story),
                selectinload(SprintBacklogItem.requirement),
            )
            .order_by(SprintBacklogItem.created_at.asc())
        ).all()
    )


def patch_item(
    db: Session,
    item_id: uuid.UUID,
    patch: dict[str, Any],
) -> SprintBacklogItem | None:
    row = db.get(SprintBacklogItem, item_id)
    if not row:
        return None
    if "status" in patch:
        row.status = STATUS_MAP.get(
            patch["status"], row.status
        )
    if "priority" in patch:
        row.priority = PRIORITY_MAP.get(
            patch["priority"], row.priority
        )
    if "assigned_to" in patch:
        val = patch["assigned_to"]
        row.assigned_to = (
            uuid.UUID(val) if val else None
        )
    if "sprint_id" in patch:
        val = patch["sprint_id"]
        row.sprint_id = uuid.UUID(val) if val else None
    if "task_description" in patch:
        row.task_description = patch["task_description"]
    db.flush()
    return row


def delete_item(
    db: Session, item_id: uuid.UUID
) -> bool:
    result = db.execute(
        delete(SprintBacklogItem).where(
            SprintBacklogItem.id == item_id,
        )
    )
    db.flush()
    return result.rowcount > 0


def item_to_dict(
    row: SprintBacklogItem,
) -> dict[str, Any]:
    story_ref = row.user_story.story_ref if row.user_story else None
    requirement_ref = row.requirement.requirement_ref if row.requirement else None
    title = row.task_description or (row.user_story.title if row.user_story else "")
    return {
        "id": str(row.id),
        "pipeline_session_id": str(row.pipeline_session_id),
        "user_story_id": str(row.user_story_id),
        "story_ref": story_ref,
        "requirement_id": str(row.requirement_id),
        "requirement_ref": requirement_ref,
        "title": title,
        "sprint_id": (
            str(row.sprint_id) if row.sprint_id else None
        ),
        "assigned_to": (
            str(row.assigned_to) if row.assigned_to else None
        ),
        "task_type": row.task_type.value,
        "task_description": row.task_description,
        "final_story_points": row.final_story_points,
        "points": row.final_story_points,
        "story_points": row.final_story_points,
        "final_estimated_hours": (
            float(row.final_estimated_hours)
            if row.final_estimated_hours is not None
            else None
        ),
        "priority": row.priority.value,
        "status": row.status.value,
        "estimation_source": row.estimation_source.value,
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
