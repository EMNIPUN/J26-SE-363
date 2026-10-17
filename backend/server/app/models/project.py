import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.group import Group
    from app.models.user import User


class Project(TimestampMixin, Base):
    """A group's project, created by a lecturer.

    Titles are not unique: several groups may build the same project.
    """

    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    group_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("groups.id", ondelete="RESTRICT"), index=True
    )
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)

    group: Mapped["Group"] = relationship(back_populates="projects")
    created_by: Mapped["User"] = relationship()
    documents: Mapped[list["ProjectDocument"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", passive_deletes=True
    )


class ProjectDocument(TimestampMixin, Base):
    """A file attached to a project, such as the lecturer's guidance PDF.

    The file itself lives in object storage; this row only points to it.
    """

    __tablename__ = "project_documents"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    original_filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(255))
    # Object key or path in file storage (e.g. a Supabase Storage bucket path).
    storage_key: Mapped[str] = mapped_column(String(1024), unique=True)

    project: Mapped["Project"] = relationship(back_populates="documents")
