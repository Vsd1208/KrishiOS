"""KnowledgeDocument ORM model.

Represents a document ingested into the KrishiOS knowledge base.
Stores file metadata, agricultural context, and ingestion status.
Physical file bytes are stored separately on the filesystem/volume;
this table holds only the path and content-addressable hash.
"""

import enum
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import TimestampMixin

if False:  # TYPE_CHECKING guard avoids circular imports at runtime
    from app.models.document_chunk import DocumentChunk


class DocumentStatus(str, enum.Enum):
    """Lifecycle state of a document through the ingestion pipeline."""

    PENDING = "pending"
    PARSING = "parsing"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    COMPLETED = "completed"
    FAILED = "failed"


class KnowledgeDocument(TimestampMixin, Base):
    """A document ingested into the KrishiOS semantic knowledge base.

    Agricultural metadata (crop, district, season, authority) is stored
    here so it can be denormalized into chunk payloads for filtered search.
    """

    __tablename__ = "knowledge_document"

    # ── Identity ────────────────────────────────────────────────────────────
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    uuid: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        default=uuid4,
        unique=True,
        nullable=False,
        index=True,
    )

    # ── Content identity ────────────────────────────────────────────────────
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    document_type: Mapped[str] = mapped_column(String(100), nullable=False)
    language: Mapped[str] = mapped_column(String(50), nullable=False, default="en")

    # ── Provenance ──────────────────────────────────────────────────────────
    source: Mapped[str | None] = mapped_column(String(300), nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    authority: Mapped[str | None] = mapped_column(
        String(300),
        nullable=True,
        comment="Issuing body e.g. ICAR, NABARD, State Dept of Agriculture",
    )

    # ── Agricultural context ─────────────────────────────────────────────────
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    district: Mapped[str | None] = mapped_column(String(150), nullable=True)
    crop: Mapped[str | None] = mapped_column(String(150), nullable=True)
    season: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="kharif, rabi, zaid, or perennial",
    )

    # ── Upload metadata ──────────────────────────────────────────────────────
    uploaded_by: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
        comment="Officer / system identifier that triggered the upload",
    )

    # ── File metadata ────────────────────────────────────────────────────────
    file_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
        comment="SHA-256 hex digest used for deduplication",
    )
    file_size: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        comment="File size in bytes",
    )
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    storage_path: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Absolute path to the stored file on the volume",
    )

    # ── Processing status ────────────────────────────────────────────────────
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name="document_status_enum"),
        nullable=False,
        default=DocumentStatus.PENDING,
        index=True,
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Populated when status = FAILED",
    )

    # ── Relationships ────────────────────────────────────────────────────────
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        "DocumentChunk",
        back_populates="document",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # ── Indexes ──────────────────────────────────────────────────────────────
    __table_args__ = (
        Index("ix_kd_crop_district", "crop", "district"),
        Index("ix_kd_language_status", "language", "status"),
    )

    def __repr__(self) -> str:
        return f"<KnowledgeDocument id={self.id} title={self.title!r} status={self.status}>"


# Re-import guard — resolve the forward reference used above.
from app.models.document_chunk import DocumentChunk  # noqa: E402, F401
