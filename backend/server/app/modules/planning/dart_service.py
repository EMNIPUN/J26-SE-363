"""Persistence for DART arbitration cases."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.dart_case import DartCaseRecord

CIRCUIT_BREAKER_THRESHOLD = 5


def save_case(
    db: Session,
    project_id: str,
    case_ref: str,
    requirement_ref: str,
    source_stage: str,
    category: str,
    status: str,
    result: dict[str, Any],
) -> None:
    if not project_id:
        return
    db.add(DartCaseRecord(
        project_id=project_id,
        case_ref=case_ref,
        requirement_ref=requirement_ref,
        source_stage=source_stage,
        category=category,
        status=status,
        result=result,
    ))
    db.commit()


def update_case_status(
    db: Session,
    project_id: str,
    case_ref: str,
    status: str,
    resolved_by: str | None = None,
) -> DartCaseRecord | None:
    row = db.scalars(
        select(DartCaseRecord)
        .where(DartCaseRecord.project_id == project_id, DartCaseRecord.case_ref == case_ref)
    ).first()
    if not row:
        return None
    row.status = status
    if resolved_by:
        row.resolved_by = resolved_by
        row.resolved_at = datetime.now(UTC)
    db.commit()
    return row


def latest_cases(db: Session, project_id: str) -> list[dict[str, Any]]:
    rows = db.scalars(
        select(DartCaseRecord)
        .where(DartCaseRecord.project_id == project_id)
        .order_by(DartCaseRecord.created_at.desc())
    ).all()
    return [_to_dict(r) for r in rows]


def cases_for_requirement(db: Session, project_id: str, requirement_ref: str) -> list[dict[str, Any]]:
    rows = db.scalars(
        select(DartCaseRecord)
        .where(
            DartCaseRecord.project_id == project_id,
            DartCaseRecord.requirement_ref == requirement_ref,
        )
        .order_by(DartCaseRecord.created_at.desc())
    ).all()
    return [_to_dict(r) for r in rows]


def open_cases(db: Session, project_id: str) -> list[dict[str, Any]]:
    rows = db.scalars(
        select(DartCaseRecord)
        .where(DartCaseRecord.project_id == project_id, DartCaseRecord.status == "open")
        .order_by(DartCaseRecord.created_at.desc())
    ).all()
    return [_to_dict(r) for r in rows]


def get_case(db: Session, project_id: str, case_ref: str) -> dict[str, Any] | None:
    row = db.scalars(
        select(DartCaseRecord)
        .where(DartCaseRecord.project_id == project_id, DartCaseRecord.case_ref == case_ref)
    ).first()
    return _to_dict(row) if row else None


def session_circuit_breaker(db: Session, project_id: str) -> bool:
    count = len(open_cases(db, project_id))
    return count >= CIRCUIT_BREAKER_THRESHOLD


def _to_dict(row: DartCaseRecord) -> dict[str, Any]:
    return {
        "case_ref": row.case_ref,
        "requirement_ref": row.requirement_ref,
        "source_stage": row.source_stage,
        "category": row.category,
        "status": row.status,
        "result": row.result,
        "resolved_by": row.resolved_by,
        "resolved_at": row.resolved_at.isoformat() if row.resolved_at else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }
