"""SpeechTranscript ORM model storing STT results, raw transcript, and language understanding."""

from uuid import UUID, uuid4
from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import TimestampMixin


class SpeechTranscript(TimestampMixin, Base):
    """Stores STT output, raw transcript (never overwritten), and extracted intent/entities."""

    __tablename__ = "speech_transcripts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uuid: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        default=uuid4,
        unique=True,
        nullable=False,
        index=True,
    )
    audio_id: Mapped[int] = mapped_column(
        ForeignKey("audio_records.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Immutable raw transcript
    raw_transcript: Mapped[str] = mapped_column(Text, nullable=False)
    detected_language: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    language_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    transcription_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)

    # Language Understanding & Normalization
    normalized_query: Mapped[str | None] = mapped_column(Text, nullable=True)
    detected_intent: Mapped[str | None] = mapped_column(String(100), nullable=True)
    extracted_entities: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Relationships
    audio: Mapped["AudioRecord"] = relationship("AudioRecord", back_populates="transcripts")
