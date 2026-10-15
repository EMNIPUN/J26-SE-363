"""Persistence for student user stories (CRUD source of truth)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.user_story import UserStoryRecord


def list_stories(db: Session, project_id: str) -> list[dict[str, Any]]:
    """All stories for a project, grouped by requirement_ref."""
    rows = db.scalars(
        select(UserStoryRecord)
        .where(UserStoryRecord.project_id == project_id)
        .order_by(UserStoryRecord.created_at.asc())
    ).all()
    return [_to_dict(row) for row in rows]


def upsert_story(
    db: Session,
    project_id: str,
    requirement_ref: str,
    story_ref: str,
    data: dict[str, Any],
) -> dict[str, Any]:
    """Create or replace a user story."""
    existing = db.scalars(
        select(UserStoryRecord).where(
            UserStoryRecord.project_id == project_id,
            UserStoryRecord.story_ref == story_ref,
        )
    ).first()

    if existing:
        existing.requirement_ref = requirement_ref
        existing.data = data
        db.commit()
        db.refresh(existing)
        return _to_dict(existing)

    row = UserStoryRecord(
        project_id=project_id,
        requirement_ref=requirement_ref,
        story_ref=story_ref,
        data=data,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_dict(row)


def delete_story(db: Session, project_id: str, story_ref: str) -> bool:
    """Delete a story by ref. Returns True if something was deleted."""
    result = db.execute(
        delete(UserStoryRecord).where(
            UserStoryRecord.project_id == project_id,
            UserStoryRecord.story_ref == story_ref,
        )
    )
    db.commit()
    return result.rowcount > 0


def _to_dict(row: UserStoryRecord) -> dict[str, Any]:
    return {
        "requirement_ref": row.requirement_ref,
        "story_ref": row.story_ref,
        "data": row.data,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }
