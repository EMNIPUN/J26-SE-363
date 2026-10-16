import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, string_enum
from app.models.enums import ParseStatus

if TYPE_CHECKING:
    from app.models.pipeline_session import PipelineSession


class SrsDocument(TimestampMixin, Base):
    __tablename__ = "rqa_srs_documents"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    pipeline_session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rqa_pipeline_sessions.id", ondelete="CASCADE"), unique=True
    )
    group_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("groups.id", ondelete="CASCADE"), index=True
    )
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    original_filename: Mapped[str] = mapped_column(String(255))
    stored_file_path: Mapped[str | None] = mapped_column(String(500))
    file_size_bytes: Mapped[int] = mapped_column(BigInteger)
    mime_type: Mapped[str] = mapped_column(String(100))
    parse_status: Mapped[ParseStatus] = mapped_column(
        string_enum(ParseStatus, "parse_status"), default=ParseStatus.PENDING
    )
    total_requirements_extracted: Mapped[int] = mapped_column(Integer, default=0)
    parse_error_message: Mapped[str | None] = mapped_column(Text)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    parsed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    pipeline_session: Mapped["PipelineSession"] = relationship(
        back_populates="srs_document"
    )
