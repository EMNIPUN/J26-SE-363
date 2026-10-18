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
    CheckResult,
    ConfidenceLevel,
    CoverageElementType,
    CoverageResult,
    DecompositionGateStatus,
    DecompositionReadiness,
    DecompositionTaskType,
    InvestCriterion,
    InvestResult,
    Priority,
    QualityBand,
    StoryStatus,
    TaskCriterion,
    TaskCriterionOutcome,
    TaskReadinessStatus,
    TaskStatus,
    ToolStatus,
)

if TYPE_CHECKING:
    from app.models.effort_estimation import StudentEffortEstimate
    from app.models.feedback import Feedback


class UserStory(TimestampMixin, Base):
    __tablename__ = "rqa_user_stories"
    __table_args__ = (
        UniqueConstraint("story_ref"),
    )

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
    legacy_story_ref: Mapped[str | None] = mapped_column(String(20))
    title: Mapped[str] = mapped_column(String(255))
    as_a: Mapped[str | None] = mapped_column(String(255))
    i_want: Mapped[str | None] = mapped_column(String(500))
    so_that: Mapped[str | None] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)
    acceptance_criteria: Mapped[list[str] | None] = mapped_column(JSONType)
    student_story_points: Mapped[int | None] = mapped_column(Integer)
    priority: Mapped[Priority] = mapped_column(
        string_enum(Priority, "story_priority"), default=Priority.MEDIUM
    )
    status: Mapped[StoryStatus] = mapped_column(
        string_enum(StoryStatus, "story_lifecycle_status"),
        default=StoryStatus.DRAFT,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    jira_issue_key: Mapped[str | None] = mapped_column(String(32), nullable=True)

    invest_validations: Mapped[list["InvestValidation"]] = relationship(
        back_populates="user_story",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    tasks: Mapped[list["UserStoryTask"]] = relationship(
        back_populates="user_story",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    estimates: Mapped[list["StudentEffortEstimate"]] = relationship(
        "StudentEffortEstimate",
        back_populates="user_story",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class UserStoryTask(TimestampMixin, Base):
    """A task or subtask written while decomposing one user story."""

    __tablename__ = "rqa_user_story_tasks"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_story_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rqa_user_stories.id", ondelete="CASCADE"), index=True
    )
    parent_task_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("rqa_user_story_tasks.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str] = mapped_column(Text, default="")
    priority: Mapped[Priority] = mapped_column(
        string_enum(Priority, "task_priority"), default=Priority.MEDIUM
    )
    task_type: Mapped[DecompositionTaskType] = mapped_column(
        string_enum(DecompositionTaskType, "decomposition_task_type"), default=DecompositionTaskType.TASK
    )
    status: Mapped[TaskStatus] = mapped_column(
        string_enum(TaskStatus, "decomposition_task_status"), default=TaskStatus.TODO
    )
    jira_subtask_key: Mapped[str | None] = mapped_column(String(32), nullable=True)

    user_story: Mapped["UserStory"] = relationship(back_populates="tasks")


class InvestValidation(Base):
    __tablename__ = "rqa_invest_validations"
    __table_args__ = (
        UniqueConstraint(
            "decomposition_assessment_id", "user_story_id", "criterion"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    decomposition_assessment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rqa_decomposition_assessments.id", ondelete="CASCADE"),
        index=True,
    )
    user_story_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rqa_user_stories.id", ondelete="CASCADE"), index=True
    )
    pipeline_session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rqa_pipeline_sessions.id", ondelete="CASCADE"), index=True
    )
    criterion: Mapped[InvestCriterion] = mapped_column(
        string_enum(InvestCriterion, "invest_criterion")
    )
    result: Mapped[InvestResult] = mapped_column(
        string_enum(InvestResult, "invest_result")
    )
    is_satisfied: Mapped[bool] = mapped_column(Boolean)
    score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    justification: Mapped[str | None] = mapped_column(Text)
    validation_method: Mapped[str] = mapped_column(String(32), default="hybrid")

    user_story: Mapped["UserStory"] = relationship(back_populates="invest_validations")
    decomposition_assessment: Mapped["DecompositionAssessment"] = relationship(
        back_populates="invest_validations"
    )


class DecompositionAssessment(TimestampMixin, Base):
    """One row per decomposition analysis run. Deliberately NOT unique on
    (requirement_id, pipeline_session_id): re-running analysis creates a new
    row so history is preserved (mirrors the Quality assessment's revision
    tracking) instead of colliding or silently overwriting the prior run."""

    __tablename__ = "rqa_decomposition_assessments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    requirement_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rqa_requirements.id", ondelete="CASCADE"), index=True
    )
    pipeline_session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rqa_pipeline_sessions.id", ondelete="CASCADE"), index=True
    )
    readiness_status: Mapped[DecompositionReadiness] = mapped_column(
        string_enum(DecompositionReadiness, "decomposition_readiness")
    )
    readiness_reason: Mapped[str] = mapped_column(Text, default="")
    # Deprecated: superseded by readiness_status. Kept nullable, written as a
    # best-effort legacy projection only, for any lingering historical-data
    # consumer — nothing reads this to decide whether a student can proceed.
    gate_status: Mapped[DecompositionGateStatus | None] = mapped_column(
        string_enum(DecompositionGateStatus, "decomposition_gate_status")
    )
    decomposition_quality_score: Mapped[float] = mapped_column(Numeric(3, 2))
    quality_band: Mapped[QualityBand] = mapped_column(
        string_enum(QualityBand, "decomposition_quality_band")
    )
    needs_review_reason: Mapped[str | None] = mapped_column(Text)
    # True only when the coverage LLM call itself could not run (unavailable
    # or errored) - distinct from a real analysis that concluded incomplete.
    # When true, decomposition_quality_score/quality_band/readiness_status
    # are a mechanical placeholder, not a real assessment, and must be shown
    # to the student as a system error rather than as feedback.
    analysis_failed: Mapped[bool] = mapped_column(Boolean, default=False)
    failure_reason: Mapped[str | None] = mapped_column(Text)
    # SHA-256 of the submitted stories' (story_ref, title, description),
    # sorted by ref — lets POST /planning/decomposition detect "nothing
    # changed since the last run" and reuse that run instead of spending
    # another LLM call. NULL on rows persisted before this column existed.
    input_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    # Deprecated: superseded by decomposition_quality_score (0-4 scale). Kept
    # nullable, unwritten, for any lingering historical-data consumer.
    composite_score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    coverage_score: Mapped[float] = mapped_column(Numeric(5, 2))
    invest_composite_score: Mapped[float | None] = mapped_column(Numeric(5, 2))
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
    story_assessments: Mapped[list["StoryAssessment"]] = relationship(
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    coverage_elements: Mapped[list["CoverageElementRow"]] = relationship(
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    gate_checks: Mapped[list["CoverageGateCheckRow"]] = relationship(
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    invest_validations: Mapped[list["InvestValidation"]] = relationship(
        back_populates="decomposition_assessment",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    feedbacks: Mapped[list["Feedback"]] = relationship(
        back_populates="decomposition_assessment",
        passive_deletes=True,
    )


class StoryAssessment(Base):
    """One row per story per decomposition run - story_ready is run-scoped,
    not story-scoped, so it can't live on the per-criterion InvestValidation
    rows (which would need 6 copies to always agree)."""

    __tablename__ = "rqa_story_assessments"
    __table_args__ = (
        UniqueConstraint("decomposition_assessment_id", "user_story_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    decomposition_assessment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rqa_decomposition_assessments.id", ondelete="CASCADE"),
        index=True,
    )
    user_story_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rqa_user_stories.id", ondelete="CASCADE"), index=True
    )
    story_ready: Mapped[bool] = mapped_column(Boolean, default=False)
    coverage_percentage: Mapped[float | None] = mapped_column(Numeric(5, 2))

    user_story: Mapped["UserStory"] = relationship()


class CoverageElementRow(Base):
    """Replaces the opaque covered_aspects/uncovered_gaps JSON blobs with
    queryable per-element rows, matching the coverage matrix from the
    decomposition scoring methodology."""

    __tablename__ = "rqa_coverage_elements"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    decomposition_assessment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rqa_decomposition_assessments.id", ondelete="CASCADE"),
        index=True,
    )
    element_type: Mapped[CoverageElementType] = mapped_column(
        string_enum(CoverageElementType, "coverage_element_type")
    )
    description: Mapped[str] = mapped_column(Text)
    required: Mapped[bool] = mapped_column(Boolean, default=True)
    covered_by: Mapped[list | None] = mapped_column(JSONType)
    coverage_result: Mapped[CoverageResult] = mapped_column(
        string_enum(CoverageResult, "coverage_result")
    )
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False)
    evidence: Mapped[str | None] = mapped_column(Text)


class CoverageGateCheckRow(Base):
    """One row per C1-C10 coverage gate check per decomposition run."""

    __tablename__ = "rqa_coverage_gate_checks"
    __table_args__ = (
        UniqueConstraint("decomposition_assessment_id", "check_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    decomposition_assessment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rqa_decomposition_assessments.id", ondelete="CASCADE"),
        index=True,
    )
    check_id: Mapped[str] = mapped_column(String(4))
    result: Mapped[CheckResult] = mapped_column(
        string_enum(CheckResult, "coverage_check_result")
    )
    rationale: Mapped[str | None] = mapped_column(Text)


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


class TaskValidationAssessment(TimestampMixin, Base):
    """One row per AI task-validation run, scoped to a single user story.
    Mirrors DecompositionAssessment: deliberately NOT unique on
    user_story_id, so re-running validation creates a new row and history is
    preserved rather than overwritten."""

    __tablename__ = "rqa_task_validation_assessments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_story_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rqa_user_stories.id", ondelete="CASCADE"), index=True
    )
    pipeline_session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rqa_pipeline_sessions.id", ondelete="CASCADE"), index=True
    )
    readiness_status: Mapped[TaskReadinessStatus] = mapped_column(
        string_enum(TaskReadinessStatus, "task_validation_readiness")
    )
    readiness_reason: Mapped[str] = mapped_column(Text, default="")
    quality_score: Mapped[float] = mapped_column(Numeric(3, 2))
    quality_band: Mapped[QualityBand] = mapped_column(
        string_enum(QualityBand, "task_validation_quality_band")
    )
    coverage_percentage: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    confidence: Mapped[float] = mapped_column(Numeric(3, 2), default=0.8)
    # True only when the validation LLM call itself could not run (unavailable
    # or errored) - distinct from a real run that concluded Needs Improvement
    # / Coverage Warning. A mechanical placeholder, not a real assessment.
    analysis_failed: Mapped[bool] = mapped_column(Boolean, default=False)
    failure_reason: Mapped[str | None] = mapped_column(Text)
    # SHA-256 of the submitted tasks' (id, title, description), sorted - lets
    # the validate endpoint detect "nothing changed since the last run" and
    # reuse that run instead of spending another LLM call.
    input_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    assessed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user_story: Mapped["UserStory"] = relationship()
    task_assessments: Mapped[list["TaskAssessment"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True,
    )
    criterion_results: Mapped[list["TaskCriterionResultRow"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True,
    )
    feedbacks: Mapped[list["Feedback"]] = relationship(
        back_populates="task_validation_assessment", passive_deletes=True,
    )


class TaskAssessment(Base):
    """One row per task per task-validation run - task_ready is run-scoped,
    not task-scoped, so it can't live on the per-criterion
    TaskCriterionResultRow rows (which would need 4 copies to always agree)."""

    __tablename__ = "rqa_task_assessments"
    __table_args__ = (
        UniqueConstraint("task_validation_assessment_id", "user_story_task_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    task_validation_assessment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rqa_task_validation_assessments.id", ondelete="CASCADE"),
        index=True,
    )
    user_story_task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rqa_user_story_tasks.id", ondelete="CASCADE"), index=True
    )
    task_ready: Mapped[bool] = mapped_column(Boolean, default=False)

    user_story_task: Mapped["UserStoryTask"] = relationship()


class TaskCriterionResultRow(Base):
    """One row per task per criterion (relevance/scope/actionability/
    duplication) per task-validation run."""

    __tablename__ = "rqa_task_criterion_results"
    __table_args__ = (
        UniqueConstraint(
            "task_validation_assessment_id", "user_story_task_id", "criterion"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    task_validation_assessment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rqa_task_validation_assessments.id", ondelete="CASCADE"),
        index=True,
    )
    user_story_task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rqa_user_story_tasks.id", ondelete="CASCADE"), index=True
    )
    criterion: Mapped[TaskCriterion] = mapped_column(
        string_enum(TaskCriterion, "task_validation_criterion")
    )
    result: Mapped[TaskCriterionOutcome] = mapped_column(
        string_enum(TaskCriterionOutcome, "task_validation_criterion_outcome")
    )
    note: Mapped[str | None] = mapped_column(Text)
    evidence: Mapped[str | None] = mapped_column(Text)
