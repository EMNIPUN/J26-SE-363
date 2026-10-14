"""Persistence for requirement-quality results (Core API owns this table).

Each scored version of a requirement is a row; history is the rows sharing
(project_id, requirement_ref) ordered by created_at. The full mapped result is
stored in ``result`` (JSON); only scope + ref are columns.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.requirement_quality import RequirementQualityRecord


def save_results(
    db: Session,
    project_id: str,
    items: list[dict[str, Any]],
) -> None:
    """Persist one new version row per scored requirement.

    ``items`` is a list of {"requirement_ref", "requirement_text", "result"}.
    """
    if not project_id or not items:
        return
    db.add_all(
        RequirementQualityRecord(
            project_id=project_id,
            requirement_ref=item["requirement_ref"],
            requirement_text=item.get("requirement_text") or "",
            result=item["result"],
        )
        for item in items
    )
    db.commit()


def latest_results(db: Session, project_id: str) -> list[dict[str, Any]]:
    """The newest stored result per requirement for a project (for page hydration)."""
    rows = db.scalars(
        select(RequirementQualityRecord)
        .where(RequirementQualityRecord.project_id == project_id)
        .order_by(RequirementQualityRecord.created_at.desc())
    ).all()

    seen: set[str] = set()
    latest: list[dict[str, Any]] = []
    for row in rows:  # already newest-first
        if row.requirement_ref in seen:
            continue
        seen.add(row.requirement_ref)
        latest.append(_to_dict(row))
    return latest


def history(db: Session, project_id: str, requirement_ref: str) -> list[dict[str, Any]]:
    """All stored versions of one requirement, oldest first, with a version index."""
    rows = db.scalars(
        select(RequirementQualityRecord)
        .where(
            RequirementQualityRecord.project_id == project_id,
            RequirementQualityRecord.requirement_ref == requirement_ref,
        )
        .order_by(RequirementQualityRecord.created_at.asc())
    ).all()
    return [{**_to_dict(row), "version": i} for i, row in enumerate(rows, start=1)]


def _to_dict(row: RequirementQualityRecord) -> dict[str, Any]:
    return {
        "requirement_ref": row.requirement_ref,
        "requirement_text": row.requirement_text,
        "result": row.result,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }
