import uuid

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, JSONType, TimestampMixin, string_enum
from app.models.enums import PipelineStage


class RetrievalLog(TimestampMixin, Base):
    __tablename__ = "rqa_retrieval_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    pipeline_session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rqa_pipeline_sessions.id", ondelete="CASCADE"), index=True
    )
    stage: Mapped[PipelineStage] = mapped_column(
        string_enum(PipelineStage, "retrieval_stage")
    )
    triggering_assessment_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    triggering_assessment_type: Mapped[str | None] = mapped_column(String(16))
    collection_name: Mapped[str] = mapped_column(String(64))
    retrieval_decision: Mapped[str] = mapped_column(String(16))
    decision_reason: Mapped[str | None] = mapped_column(Text)
    query_text: Mapped[str | None] = mapped_column(Text)
    results_count: Mapped[int] = mapped_column(Integer, default=0)
    top_similarity_score: Mapped[float | None] = mapped_column(Numeric(5, 4))
    retrieved_document_ids: Mapped[dict | None] = mapped_column(JSONType)
    execution_time_ms: Mapped[int | None] = mapped_column(Integer)
