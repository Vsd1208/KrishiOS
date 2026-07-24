"""DocumentChunk ORM model.

Represents one text segment produced by the chunking pipeline from a
parent KnowledgeDocument. Each chunk has its own UUID that serves as
the Qdrant point_id, keeping PostgreSQL and vector store in sync.
"""

from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import TimestampMixin

if False:  # TYPE_CHECKING guard
    from app.models.knowledge_document import KnowledgeDocument


class DocumentChunk(TimestampMixin, Base):
    """A single semantic chunk derived from a KnowledgeDocument.

    The chunk_id field is the authoritative join key between PostgreSQL
    (for text retrieval) and Qdrant (for vector search).
    """

    __tablename__ = "document_chunk"

    # ── Identity ─────────────────────────────────────────────────────────────
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    chunk_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        default=uuid4,
        unique=True,
        nullable=False,
        index=True,
        comment="Shared key with Qdrant point_id",
    )
    document_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge_document.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Position ──────────────────────────────────────────────────────────────
    chunk_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="0-based position within the parent document",
    )
    page_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="1-based source page number",
    )

    # ── Content ───────────────────────────────────────────────────────────────
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Approximate whitespace-token count",
    )

    # ── Embedding metadata ────────────────────────────────────────────────────
    embedding_model: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Model name used to produce the embedding",
    )
    embedding_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Model version tag for cache invalidation",
    )

    # ── Agricultural payload (denormalised for fast Qdrant filtering) ─────────
    metadata_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Arbitrary metadata: crop, district, season, authority, etc.",
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    document: Mapped["KnowledgeDocument"] = relationship(
        "KnowledgeDocument",
        back_populates="chunks",
    )

    # ── Indexes ───────────────────────────────────────────────────────────────
    __table_args__ = (
        Index("ix_dc_document_index", "document_id", "chunk_index"),
        Index("ix_dc_document_page", "document_id", "page_number"),
    )

    def __repr__(self) -> str:
        return (
            f"<DocumentChunk id={self.id} doc={self.document_id}"
            f" index={self.chunk_index} page={self.page_number}>"
        )
