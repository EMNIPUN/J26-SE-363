import uuid

from sqlalchemy import ForeignKey, LargeBinary, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin


class UserAvatar(TimestampMixin, Base):
    """The picture a person uploaded: a small JPEG, PNG or WebP kept in the database.

    It is a separate table so that reading a user never loads the image.
    """

    __tablename__ = "user_avatars"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    content_type: Mapped[str] = mapped_column(String(32))
    data: Mapped[bytes] = mapped_column(LargeBinary)
