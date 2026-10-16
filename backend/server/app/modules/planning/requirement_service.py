"""Persistence for extracted requirements."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.requirement import Requirement


def create_requirements(
    db: Session,
    session_id: uuid.UUID,
    srs_document_id: uuid.UUID | None,
    project_id: uuid.UUID,
    group_id: uuid.UUID,
    items: list[dict[str, Any]],
) -> list[Requirement]:
    rows = []
    for item in items:
        row = Requirement(
            srs_document_id=srs_document_id,
            pipeline_session_id=session_id,
            project_id=project_id,
            group_id=group_id,
            requirement_ref=item["id"],
            requirement_text=item.get("text", ""),
            requirement_category=item.get("type", "functional"),
            section_reference=item.get("section"),
            extraction_confidence=item.get("confidence"),
        )
        db.add(row)
        rows.append(row)
    db.flush()
    return rows


def list_requirements(
    db: Session, session_id: uuid.UUID
) -> list[Requirement]:
    return list(
        db.scalars(
            select(Requirement)
            .where(
                Requirement.pipeline_session_id == session_id,
                Requirement.is_active.is_(True),
            )
            .order_by(Requirement.requirement_ref)
        ).all()
    )


def get_by_ref(
    db: Session,
    session_id: uuid.UUID,
    requirement_ref: str,
) -> Requirement | None:
    return db.scalars(
        select(Requirement).where(
            Requirement.pipeline_session_id == session_id,
            Requirement.requirement_ref == requirement_ref,
            Requirement.is_active.is_(True),
        )
    ).first()


def requirement_to_dict(row: Requirement) -> dict[str, Any]:
    return {
        "id": row.requirement_ref,
        "text": row.requirement_text,
        "type": row.requirement_category.value,
        "section": row.section_reference,
        "db_id": str(row.id),
    }
