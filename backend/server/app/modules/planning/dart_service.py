"""Persistence for DART arbitration protocol — unpacks agent JSONB into
dart_sessions, dart_iterations, dart_evidence, dart_escalations."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.dart import (
    DartEvidence,
    DartIteration,
    DartSession,
)
from app.models.enums import (
    DartDecision,
    DartHypothesis,
    DartStatus,
    DartTriggerReason,
    PipelineStage,
)

CIRCUIT_BREAKER_THRESHOLD = 5

TRIGGER_MAP = {t.value: t for t in DartTriggerReason}
HYPOTHESIS_MAP = {h.value: h for h in DartHypothesis}
DECISION_MAP = {d.value: d for d in DartDecision}
STATUS_MAP = {s.value: s for s in DartStatus}
STAGE_MAP = {s.value: s for s in PipelineStage}


def create_session(
    db: Session,
    pipeline_session_id: uuid.UUID,
    agent_result: dict[str, Any],
    source_stage: str = "quality",
    trigger_reason: str = "low_confidence",
) -> DartSession:
    case = agent_result.get("case", agent_result)

    seq = (
        db.scalar(
            select(func.count(DartSession.id)).where(
                DartSession.pipeline_session_id
                == pipeline_session_id,
            )
        )
        or 0
    ) + 1

    row = DartSession(
        pipeline_session_id=pipeline_session_id,
        triggering_stage=STAGE_MAP.get(
            source_stage, PipelineStage.QUALITY
        ),
        triggering_assessment_type=case.get(
            "triggering_assessment_type", "QA"
        ),
        trigger_reason=TRIGGER_MAP.get(
            trigger_reason, DartTriggerReason.LOW_CONFIDENCE
        ),
        trigger_description=case.get("trigger_description"),
        conflicting_tool_names=case.get("conflicting_tool_names"),
        conflicting_outputs_summary=case.get(
            "conflicting_outputs_summary"
        ),
        diagnostic_hypothesis=HYPOTHESIS_MAP.get(
            str(case.get("category", "")).lower()
        ),
        hypothesis_justification=case.get(
            "hypothesis_justification"
        ),
        resolution_strategy=case.get("resolution_strategy"),
        final_decision=DECISION_MAP.get(
            str(case.get("final_decision", "")).lower()
        ),
        final_decision_justification=case.get(
            "final_decision_justification"
        ),
        resolved_score=case.get("resolved_score"),
        sequence_number=seq,
        status=STATUS_MAP.get(
            case.get("status", "active"), DartStatus.ACTIVE
        ),
    )
    db.add(row)
    db.flush()

    iterations = case.get("iterations", [])
    for it_data in iterations:
        _add_iteration(db, row.id, it_data)

    if case.get("status") in ("resolved", "escalated"):
        row.resolved_at = datetime.now(timezone.utc)
    if case.get("status") == "escalated":
        row.status = DartStatus.ESCALATED

    db.flush()
    return row


def _add_iteration(
    db: Session,
    dart_session_id: uuid.UUID,
    it_data: dict[str, Any],
) -> DartIteration:
    it = DartIteration(
        dart_session_id=dart_session_id,
        iteration_number=it_data.get("iteration_number", 1),
        resolution_tool_used=it_data.get("resolution_tool_used"),
        resolution_question=it_data.get("resolution_question"),
        resolution_input=it_data.get("resolution_input"),
        resolution_output=it_data.get("resolution_output"),
        confidence_before=it_data.get("confidence_before"),
        confidence_after=it_data.get("confidence_after"),
        score_before=it_data.get("score_before"),
        score_after=it_data.get("score_after"),
        convergence_achieved=bool(
            it_data.get("convergence_achieved", False)
        ),
        iteration_outcome=it_data.get("iteration_outcome"),
        execution_time_ms=it_data.get("execution_time_ms"),
    )
    db.add(it)
    db.flush()

    for ev in it_data.get("evidence", []):
        db.add(
            DartEvidence(
                dart_iteration_id=it.id,
                evidence_type=ev.get("evidence_type", "unknown"),
                source_tool=ev.get("source_tool"),
                source_collection=ev.get("source_collection"),
                evidence_data=ev.get("evidence_data"),
                relevance_score=ev.get("relevance_score"),
                supports_hypothesis=ev.get(
                    "supports_hypothesis"
                ),
                evidence_summary=ev.get("evidence_summary"),
            )
        )
    db.flush()
    return it


def resolve_session(
    db: Session,
    dart_session_id: uuid.UUID,
    status: str = "resolved",
    resolved_by: str | None = None,
) -> DartSession | None:
    row = db.get(DartSession, dart_session_id)
    if not row:
        return None
    row.status = STATUS_MAP.get(status, DartStatus.RESOLVED)
    row.resolved_at = datetime.now(timezone.utc)
    db.flush()
    return row


def list_sessions(
    db: Session, pipeline_session_id: uuid.UUID
) -> list[DartSession]:
    return list(
        db.scalars(
            select(DartSession)
            .where(
                DartSession.pipeline_session_id
                == pipeline_session_id,
            )
            .options(
                selectinload(DartSession.iterations).selectinload(
                    DartIteration.evidence
                ),
                selectinload(DartSession.escalation),
            )
            .order_by(DartSession.created_at.desc())
        ).all()
    )


def active_sessions(
    db: Session, pipeline_session_id: uuid.UUID
) -> list[DartSession]:
    return list(
        db.scalars(
            select(DartSession).where(
                DartSession.pipeline_session_id
                == pipeline_session_id,
                DartSession.status == DartStatus.ACTIVE,
            )
        ).all()
    )


def session_circuit_breaker(
    db: Session, pipeline_session_id: uuid.UUID
) -> bool:
    count = len(active_sessions(db, pipeline_session_id))
    return count >= CIRCUIT_BREAKER_THRESHOLD


def session_to_dict(row: DartSession) -> dict[str, Any]:
    iterations = []
    for it in sorted(
        row.iterations, key=lambda x: x.iteration_number
    ):
        evidence = [
            {
                "evidence_type": e.evidence_type,
                "source_tool": e.source_tool,
                "evidence_data": e.evidence_data,
                "relevance_score": (
                    float(e.relevance_score)
                    if e.relevance_score is not None
                    else None
                ),
                "supports_hypothesis": e.supports_hypothesis,
                "evidence_summary": e.evidence_summary,
            }
            for e in it.evidence
        ]
        iterations.append(
            {
                "iteration_number": it.iteration_number,
                "resolution_tool_used": it.resolution_tool_used,
                "resolution_output": it.resolution_output,
                "confidence_before": (
                    float(it.confidence_before)
                    if it.confidence_before is not None
                    else None
                ),
                "confidence_after": (
                    float(it.confidence_after)
                    if it.confidence_after is not None
                    else None
                ),
                "convergence_achieved": it.convergence_achieved,
                "evidence": evidence,
            }
        )

    esc = None
    if row.escalation:
        e = row.escalation
        esc = {
            "escalation_reason": e.escalation_reason,
            "status": e.status,
            "instructor_decision": e.instructor_decision,
            "instructor_notes": e.instructor_notes,
        }

    return {
        "id": str(row.id),
        "pipeline_session_id": str(row.pipeline_session_id),
        "triggering_stage": row.triggering_stage.value,
        "trigger_reason": row.trigger_reason.value,
        "diagnostic_hypothesis": (
            row.diagnostic_hypothesis.value
            if row.diagnostic_hypothesis
            else None
        ),
        "final_decision": (
            row.final_decision.value
            if row.final_decision
            else None
        ),
        "resolved_score": (
            float(row.resolved_score)
            if row.resolved_score is not None
            else None
        ),
        "status": row.status.value,
        "iteration_count": row.iteration_count,
        "iterations": iterations,
        "escalation": esc,
        "started_at": (
            row.started_at.isoformat()
            if row.started_at
            else None
        ),
        "resolved_at": (
            row.resolved_at.isoformat()
            if row.resolved_at
            else None
        ),
        "created_at": (
            row.created_at.isoformat()
            if row.created_at
            else None
        ),
    }
