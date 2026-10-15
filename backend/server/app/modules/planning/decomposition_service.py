"""Persistence for decomposition analysis results (versioned, like quality)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.decomposition import DecompositionRecord


def save_result(
    db: Session,
    project_id: str,
    requirement_ref: str,
    requirement_text: str,
    result: dict[str, Any],
) -> None:
    """Persist one new version row for a decomposition analysis."""
    if not project_id:
        return
    db.add(DecompositionRecord(
        project_id=project_id,
        requirement_ref=requirement_ref,
        requirement_text=requirement_text,
        result=result,
    ))
    db.commit()


def latest_results(db: Session, project_id: str) -> list[dict[str, Any]]:
    """Newest stored result per requirement (for page hydration)."""
    rows = db.scalars(
        select(DecompositionRecord)
        .where(DecompositionRecord.project_id == project_id)
        .order_by(DecompositionRecord.created_at.desc())
    ).all()

    seen: set[str] = set()
    latest: list[dict[str, Any]] = []
    for row in rows:
        if row.requirement_ref in seen:
            continue
        seen.add(row.requirement_ref)
        latest.append(_to_dict(row))
    return latest


def history(db: Session, project_id: str, requirement_ref: str) -> list[dict[str, Any]]:
    """All stored versions of one requirement's decomposition, oldest first."""
    rows = db.scalars(
        select(DecompositionRecord)
        .where(
            DecompositionRecord.project_id == project_id,
            DecompositionRecord.requirement_ref == requirement_ref,
        )
        .order_by(DecompositionRecord.created_at.asc())
    ).all()
    return [{**_to_dict(row), "version": i} for i, row in enumerate(rows, start=1)]


def _to_dict(row: DecompositionRecord) -> dict[str, Any]:
    return {
        "requirement_ref": row.requirement_ref,
        "requirement_text": row.requirement_text,
        "result": row.result,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }
