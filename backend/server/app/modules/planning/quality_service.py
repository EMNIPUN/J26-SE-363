"""Persistence for quality assessment results — unpacks agent JSONB into
normalized quality_assessments, dimension_scores, and tool_outputs."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.enums import (
    AssessmentStatus,
    ConfidenceLevel,
    GateDecision,
    QualityDimension,
    ToolStatus,
)
from app.models.quality_assessment import (
    QualityAssessment,
    QualityDimensionScore,
    QualityGateDecision,
    QualityToolOutput,
)

DIMENSION_NAMES = [d.value for d in QualityDimension]

CONFIDENCE_MAP = {
    "high": ConfidenceLevel.HIGH,
    "moderate": ConfidenceLevel.MODERATE,
    "low": ConfidenceLevel.LOW,
}


def save_assessment(
    db: Session,
    requirement_id: uuid.UUID,
    session_id: uuid.UUID,
    agent_result: dict[str, Any],
) -> QualityAssessment:
    assessment = QualityAssessment(
        requirement_id=requirement_id,
        pipeline_session_id=session_id,
        composite_score=agent_result.get("overall_score", 0),
        confidence_level=CONFIDENCE_MAP.get(
            str(agent_result.get("confidence", "moderate")).lower(),
            ConfidenceLevel.MODERATE,
        ),
        confidence_basis=agent_result.get("confidence_basis"),
        diagnosis=agent_result.get("diagnosis"),
        relevant_quality_criterion=agent_result.get(
            "relevant_quality_criterion"
        ),
        recommended_action=agent_result.get("recommended_action"),
        tools_invoked=agent_result.get("tools_invoked"),
        assessment_status=AssessmentStatus.COMPLETED,
        assessed_at=datetime.now(timezone.utc),
    )
    db.add(assessment)
    db.flush()

    dim_scores = agent_result.get("dimension_scores", {})
    if isinstance(dim_scores, list):
        dim_scores = {
            d.get("dimension", ""): d for d in dim_scores
        }

    for dim_name in DIMENSION_NAMES:
        dim_data = dim_scores.get(dim_name, {})
        score_val = (
            dim_data
            if isinstance(dim_data, (int, float))
            else dim_data.get("score", 0)
        )
        db.add(
            QualityDimensionScore(
                quality_assessment_id=assessment.id,
                dimension=QualityDimension(dim_name),
                score=float(score_val),
                weight=float(
                    dim_data.get("weight", 1.0)
                    if isinstance(dim_data, dict)
                    else 1.0
                ),
                justification=(
                    dim_data.get("justification")
                    if isinstance(dim_data, dict)
                    else None
                ),
                relevant_standard_reference=(
                    dim_data.get("standard_reference")
                    if isinstance(dim_data, dict)
                    else None
                ),
            )
        )

    tools = agent_result.get("tool_outputs", [])
    for idx, tool in enumerate(tools):
        db.add(
            QualityToolOutput(
                quality_assessment_id=assessment.id,
                tool_name=tool.get("tool_name", f"tool_{idx}"),
                execution_order=idx,
                input_summary=tool.get("input_summary"),
                output_data=tool.get("output_data"),
                confidence_score=tool.get("confidence_score"),
                execution_time_ms=tool.get("execution_time_ms"),
                status=ToolStatus(
                    tool.get("status", "success")
                ),
                error_message=tool.get("error_message"),
            )
        )

    db.flush()
    return assessment


def save_assessments(
    db: Session,
    session_id: uuid.UUID,
    items: list[dict[str, Any]],
    requirement_map: dict[str, uuid.UUID],
) -> None:
    for item in items:
        req_ref = item.get("requirement_ref") or item.get("id", "")
        req_id = requirement_map.get(req_ref)
        if not req_id:
            continue
        result = item.get("result", item)
        save_assessment(db, req_id, session_id, result)
    db.commit()


def save_gate_decision(
    db: Session,
    session_id: uuid.UUID,
    assessments: list[QualityAssessment],
    threshold: float = 75.0,
) -> QualityGateDecision:
    above = sum(
        1 for a in assessments
        if float(a.composite_score) >= threshold
    )
    below = len(assessments) - above
    avg = (
        sum(float(a.composite_score) for a in assessments)
        / len(assessments)
        if assessments
        else 0
    )
    decision = (
        GateDecision.PASS if avg >= threshold else GateDecision.BLOCK
    )
    row = QualityGateDecision(
        pipeline_session_id=session_id,
        composite_score=avg,
        threshold=threshold,
        decision=decision,
        total_requirements=len(assessments),
        requirements_above_threshold=above,
        requirements_below_threshold=below,
        decided_at=datetime.now(timezone.utc),
    )
    db.add(row)
    db.flush()
    return row


def get_assessments(
    db: Session, session_id: uuid.UUID
) -> list[QualityAssessment]:
    return list(
        db.scalars(
            select(QualityAssessment)
            .where(
                QualityAssessment.pipeline_session_id == session_id,
            )
            .options(
                selectinload(QualityAssessment.dimension_scores),
                selectinload(QualityAssessment.tool_outputs),
            )
        ).all()
    )


def get_gate_decision(
    db: Session, session_id: uuid.UUID
) -> QualityGateDecision | None:
    return db.scalars(
        select(QualityGateDecision).where(
            QualityGateDecision.pipeline_session_id == session_id,
        )
    ).first()


def assessment_to_dict(
    row: QualityAssessment,
) -> dict[str, Any]:
    dims = {}
    for ds in row.dimension_scores:
        dims[ds.dimension.value] = {
            "score": float(ds.score),
            "weight": float(ds.weight),
            "justification": ds.justification,
            "standard_reference": ds.relevant_standard_reference,
        }
    tools = [
        {
            "tool_name": t.tool_name,
            "output_data": t.output_data,
            "confidence_score": (
                float(t.confidence_score)
                if t.confidence_score is not None
                else None
            ),
            "execution_time_ms": t.execution_time_ms,
            "status": t.status.value,
            "error_message": t.error_message,
        }
        for t in sorted(row.tool_outputs, key=lambda x: x.execution_order)
    ]
    return {
        "id": str(row.requirement_id),
        "overall_score": float(row.composite_score),
        "confidence": row.confidence_level.value,
        "confidence_basis": row.confidence_basis,
        "diagnosis": row.diagnosis,
        "recommended_action": row.recommended_action,
        "dimension_scores": dims,
        "tool_outputs": tools,
        "status": row.assessment_status.value,
        "assessed_at": (
            row.assessed_at.isoformat() if row.assessed_at else None
        ),
        "created_at": (
            row.created_at.isoformat() if row.created_at else None
        ),
    }


def gate_to_dict(
    row: QualityGateDecision,
) -> dict[str, Any]:
    return {
        "decision": row.decision.value,
        "composite_score": float(row.composite_score),
        "threshold": float(row.threshold),
        "total_requirements": row.total_requirements,
        "above_threshold": row.requirements_above_threshold,
        "below_threshold": row.requirements_below_threshold,
        "gate_summary": row.gate_summary,
        "decided_at": (
            row.decided_at.isoformat() if row.decided_at else None
        ),
    }
