import uuid
from datetime import datetime, timezone

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
    DartDecision,
    DartHypothesis,
    DartStatus,
    DartTriggerReason,
    PipelineStage,
)


class DartSession(TimestampMixin, Base):
    __tablename__ = "rqa_dart_sessions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    pipeline_session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rqa_pipeline_sessions.id", ondelete="CASCADE"), index=True
    )
    triggering_stage: Mapped[PipelineStage] = mapped_column(
        string_enum(PipelineStage, "dart_triggering_stage")
    )
    triggering_assessment_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    triggering_assessment_type: Mapped[str | None] = mapped_column(String(16))
    trigger_reason: Mapped[DartTriggerReason] = mapped_column(
        string_enum(DartTriggerReason, "dart_trigger_reason")
    )
    trigger_description: Mapped[str | None] = mapped_column(Text)
    conflicting_tool_names: Mapped[dict | None] = mapped_column(JSONType)
    conflicting_outputs_summary: Mapped[dict | None] = mapped_column(JSONType)
    diagnostic_hypothesis: Mapped[DartHypothesis | None] = mapped_column(
        string_enum(DartHypothesis, "dart_hypothesis")
    )
    hypothesis_justification: Mapped[str | None] = mapped_column(Text)
    hypothesis_classified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    resolution_strategy: Mapped[str | None] = mapped_column(Text)
    selected_resolution_tool: Mapped[str | None] = mapped_column(String(100))
    final_decision: Mapped[DartDecision | None] = mapped_column(
        string_enum(DartDecision, "dart_decision")
    )
    final_decision_justification: Mapped[str | None] = mapped_column(Text)
    resolved_score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    iteration_count: Mapped[int] = mapped_column(Integer, default=0)
    sequence_number: Mapped[int] = mapped_column(Integer, default=1)
    timeout_ms: Mapped[int] = mapped_column(Integer, default=30000)
    status: Mapped[DartStatus] = mapped_column(
        string_enum(DartStatus, "dart_status"), default=DartStatus.ACTIVE
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    iterations: Mapped[list["DartIteration"]] = relationship(
        back_populates="dart_session",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="DartIteration.iteration_number",
    )
    escalation: Mapped["DartEscalation | None"] = relationship(
        back_populates="dart_session", uselist=False,
        cascade="all, delete-orphan", passive_deletes=True,
    )


class DartIteration(Base):
    __tablename__ = "rqa_dart_iterations"
    __table_args__ = (UniqueConstraint("dart_session_id", "iteration_number"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    dart_session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rqa_dart_sessions.id", ondelete="CASCADE"), index=True
    )
    iteration_number: Mapped[int] = mapped_column(Integer)
    resolution_tool_used: Mapped[str | None] = mapped_column(String(100))
    resolution_question: Mapped[str | None] = mapped_column(Text)
    resolution_input: Mapped[dict | None] = mapped_column(JSONType)
    resolution_output: Mapped[dict | None] = mapped_column(JSONType)
    confidence_before: Mapped[float | None] = mapped_column(Numeric(5, 2))
    confidence_after: Mapped[float | None] = mapped_column(Numeric(5, 2))
    score_before: Mapped[float | None] = mapped_column(Numeric(5, 2))
    score_after: Mapped[float | None] = mapped_column(Numeric(5, 2))
    convergence_achieved: Mapped[bool] = mapped_column(Boolean, default=False)
    iteration_outcome: Mapped[str | None] = mapped_column(String(32))
    execution_time_ms: Mapped[int | None] = mapped_column(Integer)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    dart_session: Mapped["DartSession"] = relationship(back_populates="iterations")
    evidence: Mapped[list["DartEvidence"]] = relationship(
        back_populates="dart_iteration",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class DartEvidence(Base):
    __tablename__ = "rqa_dart_evidence"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    dart_iteration_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rqa_dart_iterations.id", ondelete="CASCADE"), index=True
    )
    evidence_type: Mapped[str] = mapped_column(String(64))
    source_tool: Mapped[str | None] = mapped_column(String(100))
    source_collection: Mapped[str | None] = mapped_column(String(100))
    evidence_data: Mapped[dict | None] = mapped_column(JSONType)
    relevance_score: Mapped[float | None] = mapped_column(Numeric(5, 4))
    supports_hypothesis: Mapped[bool | None] = mapped_column(Boolean)
    evidence_summary: Mapped[str | None] = mapped_column(Text)

    dart_iteration: Mapped["DartIteration"] = relationship(back_populates="evidence")


class DartEscalation(TimestampMixin, Base):
    __tablename__ = "rqa_dart_escalations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    dart_session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rqa_dart_sessions.id", ondelete="CASCADE"), unique=True
    )
    escalated_to: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    escalation_reason: Mapped[str | None] = mapped_column(Text)
    diagnostic_context: Mapped[dict | None] = mapped_column(JSONType)
    original_conflicting_outputs: Mapped[dict | None] = mapped_column(JSONType)
    iteration_history: Mapped[dict | None] = mapped_column(JSONType)
    instructor_decision: Mapped[str | None] = mapped_column(Text)
    instructor_override_score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    instructor_notes: Mapped[str | None] = mapped_column(Text)
    resolution_action: Mapped[str | None] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32), default="pending")
    escalated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    dart_session: Mapped["DartSession"] = relationship(back_populates="escalation")
