"""AudioRecord ORM model storing metadata for voice audio uploads."""

from uuid import UUID, uuid4
from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import TimestampMixin


class AudioRecord(TimestampMixin, Base):
    """Metadata for an uploaded voice audio query. Audio binary resides in FileStore."""

    __tablename__ = "audio_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uuid: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        default=uuid4,
        unique=True,
        nullable=False,
        index=True,
    )
    owner_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("user.uuid", ondelete="CASCADE"), nullable=False, index=True
    )

    file_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    language_detected: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)
    language_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Relationships
    transcripts: Mapped[list["SpeechTranscript"]] = relationship(
        "SpeechTranscript", back_populates="audio", cascade="all, delete-orphan"
    )
