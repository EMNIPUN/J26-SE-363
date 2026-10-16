import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
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
    InvestCriterion,
    Priority,
    ToolStatus,
)

if TYPE_CHECKING:
    pass


class UserStory(TimestampMixin, Base):
    __tablename__ = "rqa_user_stories"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    requirement_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rqa_requirements.id", ondelete="CASCADE"), index=True
    )
    pipeline_session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rqa_pipeline_sessions.id", ondelete="CASCADE"), index=True
    )
    authored_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    story_ref: Mapped[str] = mapped_column(String(20))
    title: Mapped[str] = mapped_column(String(255))
    as_a: Mapped[str | None] = mapped_column(String(255))
    i_want: Mapped[str | None] = mapped_column(String(500))
    so_that: Mapped[str | None] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)
    acceptance_criteria: Mapped[dict | None] = mapped_column(JSONType)
    student_story_points: Mapped[int | None] = mapped_column(Integer)
    priority: Mapped[Priority] = mapped_column(
        string_enum(Priority, "story_priority"), default=Priority.MEDIUM
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[int] = mapped_column(Integer, default=1)

    invest_validations: Mapped[list["InvestValidation"]] = relationship(
        back_populates="user_story",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class InvestValidation(Base):
    __tablename__ = "rqa_invest_validations"
    __table_args__ = (UniqueConstraint("user_story_id", "criterion"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_story_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rqa_user_stories.id", ondelete="CASCADE"), index=True
    )
    pipeline_session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rqa_pipeline_sessions.id", ondelete="CASCADE"), index=True
    )
    criterion: Mapped[InvestCriterion] = mapped_column(
        string_enum(InvestCriterion, "invest_criterion")
    )
    is_satisfied: Mapped[bool] = mapped_column(Boolean)
    score: Mapped[float] = mapped_column(Numeric(5, 2))
    justification: Mapped[str | None] = mapped_column(Text)
    validation_method: Mapped[str] = mapped_column(String(32), default="hybrid")

    user_story: Mapped["UserStory"] = relationship(back_populates="invest_validations")


class DecompositionAssessment(TimestampMixin, Base):
    __tablename__ = "rqa_decomposition_assessments"
    __table_args__ = (UniqueConstraint("requirement_id", "pipeline_session_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    requirement_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rqa_requirements.id", ondelete="CASCADE"), index=True
    )
    pipeline_session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rqa_pipeline_sessions.id", ondelete="CASCADE"), index=True
    )
    composite_score: Mapped[float] = mapped_column(Numeric(5, 2))
    coverage_score: Mapped[float] = mapped_column(Numeric(5, 2))
    invest_composite_score: Mapped[float] = mapped_column(Numeric(5, 2))
    confidence_level: Mapped[ConfidenceLevel] = mapped_column(
        string_enum(ConfidenceLevel, "dec_confidence_level")
    )
    confidence_basis: Mapped[str | None] = mapped_column(Text)
    diagnosis: Mapped[str | None] = mapped_column(Text)
    recommended_action: Mapped[str | None] = mapped_column(Text)
    tools_invoked: Mapped[dict | None] = mapped_column(JSONType)
    stories_evaluated: Mapped[int] = mapped_column(Integer, default=0)
    stories_needing_revision: Mapped[int] = mapped_column(Integer, default=0)
    assessment_status: Mapped[AssessmentStatus] = mapped_column(
        string_enum(AssessmentStatus, "dec_assessment_status"),
        default=AssessmentStatus.PENDING,
    )
    assessed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    coverage_analysis: Mapped["CoverageAnalysisResult | None"] = relationship(
        back_populates="decomposition_assessment", uselist=False,
        cascade="all, delete-orphan", passive_deletes=True,
    )
    tool_outputs: Mapped[list["DecompositionToolOutput"]] = relationship(
        back_populates="decomposition_assessment",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class CoverageAnalysisResult(Base):
    __tablename__ = "rqa_coverage_analysis_results"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    decomposition_assessment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rqa_decomposition_assessments.id", ondelete="CASCADE"), unique=True
    )
    requirement_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rqa_requirements.id", ondelete="CASCADE"), index=True
    )
    overall_coverage_percentage: Mapped[float] = mapped_column(Numeric(5, 2))
    covered_aspects: Mapped[dict | None] = mapped_column(JSONType)
    uncovered_gaps: Mapped[dict | None] = mapped_column(JSONType)
    story_coverage_map: Mapped[dict | None] = mapped_column(JSONType)
    semantic_similarity_scores: Mapped[dict | None] = mapped_column(JSONType)
    highest_similarity: Mapped[float | None] = mapped_column(Numeric(5, 4))
    lowest_similarity: Mapped[float | None] = mapped_column(Numeric(5, 4))

    decomposition_assessment: Mapped["DecompositionAssessment"] = relationship(
        back_populates="coverage_analysis"
    )


class DecompositionToolOutput(Base):
    __tablename__ = "rqa_decomposition_tool_outputs"
    __table_args__ = (
        UniqueConstraint("decomposition_assessment_id", "tool_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    decomposition_assessment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rqa_decomposition_assessments.id", ondelete="CASCADE"), index=True
    )
    tool_name: Mapped[str] = mapped_column(String(64))
    execution_order: Mapped[int] = mapped_column(Integer)
    input_summary: Mapped[dict | None] = mapped_column(JSONType)
    output_data: Mapped[dict | None] = mapped_column(JSONType)
    confidence_score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    execution_time_ms: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[ToolStatus] = mapped_column(
        string_enum(ToolStatus, "dec_tool_status")
    )
    error_message: Mapped[str | None] = mapped_column(Text)

    decomposition_assessment: Mapped["DecompositionAssessment"] = relationship(
        back_populates="tool_outputs"
    )
