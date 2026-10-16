"""Persistence for decomposition analysis — unpacks agent JSONB into
decomposition_assessments, invest_validations, coverage_analysis, tool_outputs."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.decomposition_assessment import (
    CoverageAnalysisResult,
    DecompositionAssessment,
    DecompositionToolOutput,
    InvestValidation,
    UserStory,
)
from app.models.enums import (
    AssessmentStatus,
    ConfidenceLevel,
    InvestCriterion,
    Priority,
    ToolStatus,
)

INVEST_CRITERIA = [c.value for c in InvestCriterion]

CONFIDENCE_MAP = {
    "high": ConfidenceLevel.HIGH,
    "moderate": ConfidenceLevel.MODERATE,
    "low": ConfidenceLevel.LOW,
}

PRIORITY_MAP = {
    "critical": Priority.CRITICAL,
    "high": Priority.HIGH,
    "medium": Priority.MEDIUM,
    "low": Priority.LOW,
}


# --- User Story CRUD --------------------------------------------------------


def upsert_story(
    db: Session,
    requirement_id: uuid.UUID,
    session_id: uuid.UUID,
    story_data: dict[str, Any],
    authored_by: uuid.UUID | None = None,
) -> UserStory:
    story_ref = story_data.get("id", story_data.get("story_ref", ""))
    existing = db.scalars(
        select(UserStory).where(
            UserStory.pipeline_session_id == session_id,
            UserStory.story_ref == story_ref,
        )
    ).first()

    if existing:
        existing.title = story_data.get("title", existing.title)
        existing.as_a = story_data.get("as_a", existing.as_a)
        existing.i_want = story_data.get("i_want", existing.i_want)
        existing.so_that = story_data.get("so_that", existing.so_that)
        existing.description = story_data.get(
            "description", existing.description
        )
        existing.acceptance_criteria = story_data.get(
            "acceptance_criteria", existing.acceptance_criteria
        )
        p = story_data.get("priority", "").lower()
        if p in PRIORITY_MAP:
            existing.priority = PRIORITY_MAP[p]
        db.flush()
        return existing

    row = UserStory(
        requirement_id=requirement_id,
        pipeline_session_id=session_id,
        authored_by=authored_by,
        story_ref=story_ref,
        title=story_data.get("title", "Untitled"),
        as_a=story_data.get("as_a"),
        i_want=story_data.get("i_want"),
        so_that=story_data.get("so_that"),
        description=story_data.get("description"),
        acceptance_criteria=story_data.get("acceptance_criteria"),
        priority=PRIORITY_MAP.get(
            story_data.get("priority", "medium").lower(),
            Priority.MEDIUM,
        ),
    )
    db.add(row)
    db.flush()
    return row


def list_stories(
    db: Session, session_id: uuid.UUID
) -> list[UserStory]:
    return list(
        db.scalars(
            select(UserStory)
            .where(
                UserStory.pipeline_session_id == session_id,
                UserStory.is_active.is_(True),
            )
            .options(selectinload(UserStory.invest_validations))
            .order_by(UserStory.story_ref)
        ).all()
    )


def get_story_by_ref(
    db: Session, session_id: uuid.UUID, story_ref: str
) -> UserStory | None:
    return db.scalars(
        select(UserStory).where(
            UserStory.pipeline_session_id == session_id,
            UserStory.story_ref == story_ref,
            UserStory.is_active.is_(True),
        )
    ).first()


def delete_story(
    db: Session, session_id: uuid.UUID, story_ref: str
) -> bool:
    row = get_story_by_ref(db, session_id, story_ref)
    if not row:
        return False
    row.is_active = False
    db.flush()
    return True


# --- Decomposition assessment ------------------------------------------------


def save_assessment(
    db: Session,
    requirement_id: uuid.UUID,
    session_id: uuid.UUID,
    agent_result: dict[str, Any],
    stories: list[UserStory] | None = None,
) -> DecompositionAssessment:
    assessment = DecompositionAssessment(
        requirement_id=requirement_id,
        pipeline_session_id=session_id,
        composite_score=agent_result.get("composite_score", 0),
        coverage_score=agent_result.get("coverage_score", 0),
        invest_composite_score=agent_result.get(
            "invest_composite_score", 0
        ),
        confidence_level=CONFIDENCE_MAP.get(
            str(agent_result.get("confidence", "moderate")).lower(),
            ConfidenceLevel.MODERATE,
        ),
        confidence_basis=agent_result.get("confidence_basis"),
        diagnosis=agent_result.get("diagnosis"),
        recommended_action=agent_result.get("recommended_action"),
        tools_invoked=agent_result.get("tools_invoked"),
        stories_evaluated=agent_result.get("stories_evaluated", 0),
        stories_needing_revision=agent_result.get(
            "stories_needing_revision", 0
        ),
        assessment_status=AssessmentStatus.COMPLETED,
        assessed_at=datetime.now(timezone.utc),
    )
    db.add(assessment)
    db.flush()

    coverage = agent_result.get("coverage", {})
    if coverage:
        db.add(
            CoverageAnalysisResult(
                decomposition_assessment_id=assessment.id,
                requirement_id=requirement_id,
                overall_coverage_percentage=coverage.get(
                    "overall_coverage_percentage", 0
                ),
                covered_aspects=coverage.get("covered_aspects"),
                uncovered_gaps=coverage.get("uncovered_gaps"),
                story_coverage_map=coverage.get("story_coverage_map"),
                semantic_similarity_scores=coverage.get(
                    "semantic_similarity_scores"
                ),
                highest_similarity=coverage.get("highest_similarity"),
                lowest_similarity=coverage.get("lowest_similarity"),
            )
        )

    story_invest = agent_result.get("stories", [])
    story_map = {s.story_ref: s for s in (stories or [])}
    for si in story_invest:
        sid = si.get("story_id", "")
        story_row = story_map.get(sid)
        if not story_row:
            continue
        for criterion_name in INVEST_CRITERIA:
            crit_data = si.get(criterion_name, {})
            if isinstance(crit_data, bool):
                crit_data = {
                    "is_satisfied": crit_data,
                    "score": 1.0 if crit_data else 0.0,
                }
            db.add(
                InvestValidation(
                    user_story_id=story_row.id,
                    pipeline_session_id=session_id,
                    criterion=InvestCriterion(criterion_name),
                    is_satisfied=bool(
                        crit_data.get("is_satisfied", False)
                    ),
                    score=float(crit_data.get("score", 0)),
                    justification=crit_data.get("justification"),
                )
            )

    tools = agent_result.get("tool_outputs", [])
    for idx, tool in enumerate(tools):
        db.add(
            DecompositionToolOutput(
                decomposition_assessment_id=assessment.id,
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


def get_assessments(
    db: Session, session_id: uuid.UUID
) -> list[DecompositionAssessment]:
    return list(
        db.scalars(
            select(DecompositionAssessment)
            .where(
                DecompositionAssessment.pipeline_session_id
                == session_id,
            )
            .options(
                selectinload(
                    DecompositionAssessment.coverage_analysis
                ),
                selectinload(DecompositionAssessment.tool_outputs),
            )
        ).all()
    )


# --- Serialization -----------------------------------------------------------


def story_to_dict(row: UserStory) -> dict[str, Any]:
    invest = {}
    for iv in row.invest_validations:
        invest[iv.criterion.value] = {
            "is_satisfied": iv.is_satisfied,
            "score": float(iv.score),
            "justification": iv.justification,
        }
    return {
        "id": row.story_ref,
        "story_ref": row.story_ref,
        "requirement_ref": str(row.requirement_id),
        "title": row.title,
        "as_a": row.as_a,
        "i_want": row.i_want,
        "so_that": row.so_that,
        "description": row.description,
        "acceptance_criteria": row.acceptance_criteria,
        "student_story_points": row.student_story_points,
        "priority": row.priority.value,
        "invest_result": invest or None,
        "db_id": str(row.id),
        "created_at": (
            row.created_at.isoformat() if row.created_at else None
        ),
        "updated_at": (
            row.updated_at.isoformat() if row.updated_at else None
        ),
    }


def assessment_to_dict(
    row: DecompositionAssessment,
) -> dict[str, Any]:
    cov = None
    if row.coverage_analysis:
        c = row.coverage_analysis
        cov = {
            "overall_coverage_percentage": float(
                c.overall_coverage_percentage
            ),
            "covered_aspects": c.covered_aspects,
            "uncovered_gaps": c.uncovered_gaps,
            "story_coverage_map": c.story_coverage_map,
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
            "status": t.status.value,
        }
        for t in sorted(
            row.tool_outputs, key=lambda x: x.execution_order
        )
    ]
    return {
        "requirement_id": str(row.requirement_id),
        "composite_score": float(row.composite_score),
        "coverage_score": float(row.coverage_score),
        "invest_composite_score": float(
            row.invest_composite_score
        ),
        "confidence": row.confidence_level.value,
        "diagnosis": row.diagnosis,
        "recommended_action": row.recommended_action,
        "coverage": cov,
        "tool_outputs": tools,
        "stories_evaluated": row.stories_evaluated,
        "stories_needing_revision": row.stories_needing_revision,
        "status": row.assessment_status.value,
        "assessed_at": (
            row.assessed_at.isoformat()
            if row.assessed_at
            else None
        ),
    }
