import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, JSONType, TimestampMixin, string_enum
from app.models.enums import (
    AssessmentStatus,
    ConfidenceLevel,
    GateDecision,
    QualityDimension,
    ToolStatus,
)

if TYPE_CHECKING:
    from app.models.pipeline_session import PipelineSession


class QualityAssessment(TimestampMixin, Base):
    __tablename__ = "rqa_quality_assessments"
    __table_args__ = (
        UniqueConstraint(
            "requirement_id",
            "pipeline_session_id",
            "revision_number",
            name="uq_rqa_quality_assessments_req_session_revision",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    requirement_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rqa_requirements.id", ondelete="CASCADE"), index=True
    )
    pipeline_session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rqa_pipeline_sessions.id", ondelete="CASCADE"), index=True
    )
    # Immutable snapshot of the requirement at the time it was assessed.
    revision_number: Mapped[int] = mapped_column(Integer)
    requirement_text_snapshot: Mapped[str] = mapped_column(Text)
    composite_score: Mapped[float] = mapped_column(Numeric(5, 2))
    confidence_level: Mapped[ConfidenceLevel] = mapped_column(
        string_enum(ConfidenceLevel, "qa_confidence_level")
    )
    confidence_basis: Mapped[str | None] = mapped_column(Text)
    diagnosis: Mapped[str | None] = mapped_column(Text)
    relevant_quality_criterion: Mapped[str | None] = mapped_column(Text)
    recommended_action: Mapped[str | None] = mapped_column(Text)
    tools_invoked: Mapped[dict | None] = mapped_column(JSONType)
    assessment_status: Mapped[AssessmentStatus] = mapped_column(
        string_enum(AssessmentStatus, "qa_assessment_status"),
        default=AssessmentStatus.PENDING,
    )
    assessed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    dimension_scores: Mapped[list["QualityDimensionScore"]] = relationship(
        back_populates="quality_assessment",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    tool_outputs: Mapped[list["QualityToolOutput"]] = relationship(
        back_populates="quality_assessment",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class QualityDimensionScore(Base):
    __tablename__ = "rqa_quality_dimension_scores"
    __table_args__ = (UniqueConstraint("quality_assessment_id", "dimension"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    quality_assessment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rqa_quality_assessments.id", ondelete="CASCADE"), index=True
    )
    dimension: Mapped[QualityDimension] = mapped_column(
        string_enum(QualityDimension, "quality_dimension")
    )
    score: Mapped[float] = mapped_column(Numeric(5, 2))
    weight: Mapped[float] = mapped_column(Numeric(5, 2), default=1.0)
    justification: Mapped[str | None] = mapped_column(Text)
    issues: Mapped[list | None] = mapped_column(JSONType)
    recommended_action: Mapped[str | None] = mapped_column(Text)
    relevant_standard_reference: Mapped[str | None] = mapped_column(String(255))

    quality_assessment: Mapped["QualityAssessment"] = relationship(
        back_populates="dimension_scores"
    )


class QualityToolOutput(Base):
    __tablename__ = "rqa_quality_tool_outputs"
    __table_args__ = (UniqueConstraint("quality_assessment_id", "tool_name"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    quality_assessment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rqa_quality_assessments.id", ondelete="CASCADE"), index=True
    )
    tool_name: Mapped[str] = mapped_column(String(64))
    execution_order: Mapped[int] = mapped_column(Integer)
    input_summary: Mapped[dict | None] = mapped_column(JSONType)
    output_data: Mapped[dict | None] = mapped_column(JSONType)
    confidence_score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    execution_time_ms: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[ToolStatus] = mapped_column(
        string_enum(ToolStatus, "qa_tool_status")
    )
    error_message: Mapped[str | None] = mapped_column(Text)

    quality_assessment: Mapped["QualityAssessment"] = relationship(
        back_populates="tool_outputs"
    )


class QualityGateDecision(TimestampMixin, Base):
    __tablename__ = "rqa_quality_gate_decisions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    pipeline_session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rqa_pipeline_sessions.id", ondelete="CASCADE"), unique=True
    )
    composite_score: Mapped[float] = mapped_column(Numeric(5, 2))
    threshold: Mapped[float] = mapped_column(Numeric(5, 2), default=75.0)
    decision: Mapped[GateDecision] = mapped_column(
        string_enum(GateDecision, "gate_decision")
    )
    total_requirements: Mapped[int] = mapped_column(Integer)
    requirements_above_threshold: Mapped[int] = mapped_column(Integer)
    requirements_below_threshold: Mapped[int] = mapped_column(Integer)
    blocking_dimensions: Mapped[dict | None] = mapped_column(JSONType)
    gate_summary: Mapped[str | None] = mapped_column(Text)
    decided_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    pipeline_session: Mapped["PipelineSession"] = relationship(
        back_populates="quality_gate_decision"
    )


class StudentQualitySelfAssessment(TimestampMixin, Base):
    __tablename__ = "rqa_student_quality_self_assessments"
    __table_args__ = (
        UniqueConstraint("requirement_id", "pipeline_session_id", "dimension"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    requirement_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rqa_requirements.id", ondelete="CASCADE"), index=True
    )
    pipeline_session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rqa_pipeline_sessions.id", ondelete="CASCADE"), index=True
    )
    assessed_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    dimension: Mapped[QualityDimension] = mapped_column(
        string_enum(QualityDimension, "self_assess_quality_dimension")
    )
    student_score: Mapped[float] = mapped_column(Numeric(5, 2))
    student_justification: Mapped[str | None] = mapped_column(Text)
