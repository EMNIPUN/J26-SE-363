"""Persistence for sprint tasks (CRUD source of truth)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.sprint_task import SprintTaskRecord


def list_tasks(db: Session, project_id: str) -> list[dict[str, Any]]:
    rows = db.scalars(
        select(SprintTaskRecord)
        .where(SprintTaskRecord.project_id == project_id)
        .order_by(SprintTaskRecord.created_at.asc())
    ).all()
    return [_to_dict(row) for row in rows]


def upsert_task(
    db: Session,
    project_id: str,
    task_ref: str,
    story_ref: str,
    requirement_ref: str,
    task_status: str,
    data: dict[str, Any],
) -> dict[str, Any]:
    existing = db.scalars(
        select(SprintTaskRecord).where(
            SprintTaskRecord.project_id == project_id,
            SprintTaskRecord.task_ref == task_ref,
        )
    ).first()

    if existing:
        existing.story_ref = story_ref
        existing.requirement_ref = requirement_ref
        existing.status = task_status
        existing.data = data
        db.commit()
        db.refresh(existing)
        return _to_dict(existing)

    row = SprintTaskRecord(
        project_id=project_id,
        task_ref=task_ref,
        story_ref=story_ref,
        requirement_ref=requirement_ref,
        status=task_status,
        data=data,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_dict(row)


def patch_task(
    db: Session,
    project_id: str,
    task_ref: str,
    patch: dict[str, Any],
) -> dict[str, Any] | None:
    row = db.scalars(
        select(SprintTaskRecord).where(
            SprintTaskRecord.project_id == project_id,
            SprintTaskRecord.task_ref == task_ref,
        )
    ).first()
    if not row:
        return None

    if "status" in patch:
        row.status = patch["status"]
    if "data" in patch:
        merged = {**(row.data or {}), **patch["data"]}
        row.data = merged

    db.commit()
    db.refresh(row)
    return _to_dict(row)


def delete_task(db: Session, project_id: str, task_ref: str) -> bool:
    result = db.execute(
        delete(SprintTaskRecord).where(
            SprintTaskRecord.project_id == project_id,
            SprintTaskRecord.task_ref == task_ref,
        )
    )
    db.commit()
    return result.rowcount > 0


def _to_dict(row: SprintTaskRecord) -> dict[str, Any]:
    return {
        "task_ref": row.task_ref,
        "story_ref": row.story_ref,
        "requirement_ref": row.requirement_ref,
        "status": row.status,
        "data": row.data,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }
