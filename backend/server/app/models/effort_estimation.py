import uuid
from datetime import datetime

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
    EstimationTechnique,
    ToolStatus,
)


class StudentEffortEstimate(TimestampMixin, Base):
    __tablename__ = "rqa_student_effort_estimates"
    __table_args__ = (UniqueConstraint("user_story_id", "pipeline_session_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_story_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rqa_user_stories.id", ondelete="CASCADE"), index=True
    )
    pipeline_session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rqa_pipeline_sessions.id", ondelete="CASCADE"), index=True
    )
    estimated_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    estimated_hours: Mapped[float | None] = mapped_column(Numeric(8, 2))
    estimated_story_points: Mapped[int] = mapped_column(Integer)
    estimation_basis: Mapped[str | None] = mapped_column(Text)
    estimation_technique: Mapped[EstimationTechnique] = mapped_column(
        string_enum(EstimationTechnique, "estimation_technique"),
        default=EstimationTechnique.FIBONACCI,
    )


class EstimateComparison(TimestampMixin, Base):
    __tablename__ = "rqa_estimate_comparisons"
    __table_args__ = (UniqueConstraint("user_story_id", "pipeline_session_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_story_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rqa_user_stories.id", ondelete="CASCADE"), index=True
    )
    pipeline_session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rqa_pipeline_sessions.id", ondelete="CASCADE"), index=True
    )
    student_estimate_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("rqa_student_effort_estimates.id", ondelete="SET NULL")
    )
    ai_assessment_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    decided_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    student_hours: Mapped[float | None] = mapped_column(Numeric(8, 2))
    ai_hours: Mapped[float | None] = mapped_column(Numeric(8, 2))
    deviation_percentage: Mapped[float | None] = mapped_column(Numeric(5, 2))
    deviation_category: Mapped[str | None] = mapped_column(String(32))
    ai_reasoning: Mapped[str | None] = mapped_column(Text)
    final_hours: Mapped[float | None] = mapped_column(Numeric(8, 2))
    final_story_points: Mapped[int] = mapped_column(Integer)
    final_decision_basis: Mapped[str | None] = mapped_column(Text)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


# --- Placeholder tables for class diagram compliance (AI agent not yet built) ---


class EffortEstimationAssessment(TimestampMixin, Base):
    __tablename__ = "rqa_effort_estimation_assessments"
    __table_args__ = (UniqueConstraint("user_story_id", "pipeline_session_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_story_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rqa_user_stories.id", ondelete="CASCADE"), index=True
    )
    pipeline_session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rqa_pipeline_sessions.id", ondelete="CASCADE"), index=True
    )
    composite_score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    confidence_level: Mapped[ConfidenceLevel | None] = mapped_column(
        string_enum(ConfidenceLevel, "eff_confidence_level")
    )
    diagnosis: Mapped[str | None] = mapped_column(Text)
    recommended_action: Mapped[str | None] = mapped_column(Text)
    tools_invoked: Mapped[dict | None] = mapped_column(JSONType)
    assessment_status: Mapped[AssessmentStatus] = mapped_column(
        string_enum(AssessmentStatus, "eff_assessment_status"),
        default=AssessmentStatus.PENDING,
    )
    assessed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    tool_outputs: Mapped[list["EffortToolOutput"]] = relationship(
        back_populates="assessment",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    shap_explanation: Mapped["ShapExplanation | None"] = relationship(
        back_populates="assessment", uselist=False,
        cascade="all, delete-orphan", passive_deletes=True,
    )


class EffortToolOutput(Base):
    __tablename__ = "rqa_effort_tool_outputs"
    __table_args__ = (UniqueConstraint("assessment_id", "tool_name"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    assessment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rqa_effort_estimation_assessments.id", ondelete="CASCADE"),
        index=True,
    )
    tool_name: Mapped[str] = mapped_column(String(64))
    execution_order: Mapped[int] = mapped_column(Integer)
    input_summary: Mapped[dict | None] = mapped_column(JSONType)
    output_data: Mapped[dict | None] = mapped_column(JSONType)
    confidence_score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    execution_time_ms: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[ToolStatus] = mapped_column(
        string_enum(ToolStatus, "eff_tool_status")
    )
    error_message: Mapped[str | None] = mapped_column(Text)

    assessment: Mapped["EffortEstimationAssessment"] = relationship(
        back_populates="tool_outputs"
    )


class ShapExplanation(Base):
    __tablename__ = "rqa_shap_explanations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    assessment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rqa_effort_estimation_assessments.id", ondelete="CASCADE"),
        unique=True,
    )
    feature_name: Mapped[str] = mapped_column(String(128))
    feature_value: Mapped[float | None] = mapped_column(Numeric(10, 4))
    shap_value: Mapped[float | None] = mapped_column(Numeric(10, 4))
    feature_importance_rank: Mapped[int | None] = mapped_column(Integer)
    direction: Mapped[str | None] = mapped_column(String(16))

    assessment: Mapped["EffortEstimationAssessment"] = relationship(
        back_populates="shap_explanation"
    )
