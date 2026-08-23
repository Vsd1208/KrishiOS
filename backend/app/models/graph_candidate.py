"""PostgreSQL model for graph knowledge candidates.

Tracks extracted relationships before they are promoted into Neo4j.
Officers review PENDING candidates via the /graph/candidates API.
APPROVED candidates are ingested into Neo4j; REJECTED are kept for audit.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import Float, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.base import TimestampMixin


class GraphKnowledgeCandidate(TimestampMixin, Base):
    """A candidate graph relationship extracted from a document chunk.

    Lifecycle:
      PENDING       → extracted, awaiting review or auto-accept
      APPROVED      → accepted, inserted (or queued for insertion) into Neo4j
      REJECTED      → rejected by officer or below confidence threshold
    """

    __tablename__ = "graph_knowledge_candidate"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # ── Source provenance ─────────────────────────────────────────────────────
    document_uuid: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="UUID of the parent KnowledgeDocument",
    )
    chunk_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="UUID of the DocumentChunk (= Qdrant point_id)",
    )
    page_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Page within the source document (1-based)",
    )
    authority: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        default="",
        comment="Publishing authority from document metadata",
    )

    # ── Graph triple ──────────────────────────────────────────────────────────
    subject_label: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="Ontology node type (e.g. Crop)"
    )
    subject_name: Mapped[str] = mapped_column(
        String(300), nullable=False, comment="Canonical entity name"
    )
    predicate: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="Relationship type (e.g. HAS_DISEASE)"
    )
    object_label: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="Ontology node type of the target"
    )
    object_name: Mapped[str] = mapped_column(
        String(300), nullable=False, comment="Canonical entity name of the target"
    )
    source_text: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Text evidence that produced this relationship"
    )

    # ── Extraction metadata ───────────────────────────────────────────────────
    confidence: Mapped[float] = mapped_column(
        Float, nullable=False, comment="Extraction confidence 0.0–1.0"
    )
    extraction_model: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="Extractor identifier"
    )

    # ── Review state ──────────────────────────────────────────────────────────
    review_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="PENDING",
        index=True,
        comment="PENDING | APPROVED | REJECTED",
    )
    reviewed_by: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        nullable=True,
        comment="UUID of the reviewing officer (from User.uuid)",
    )
    review_note: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )

    # ── Neo4j back-reference (populated on approval) ──────────────────────────
    neo4j_rel_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="The rel_id of the resulting Neo4j relationship",
    )

    # ── Indexes ───────────────────────────────────────────────────────────────
    __table_args__ = (
        Index("ix_gkc_document_status", "document_uuid", "review_status"),
        Index("ix_gkc_subject", "subject_label", "subject_name"),
        Index("ix_gkc_predicate", "predicate"),
    )

    def __repr__(self) -> str:
        return (
            f"<GraphKnowledgeCandidate id={self.id} "
            f"{self.subject_name}-[{self.predicate}]->{self.object_name} "
            f"status={self.review_status}>"
        )
