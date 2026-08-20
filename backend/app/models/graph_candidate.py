"""PostgreSQL model for graph knowledge candidates.

Tracks extracted relationships before they enter Neo4j,
and records officer review decisions.
"""

from uuid import UUID

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TimestampMixin
from app.database.base import Base


class GraphKnowledgeCandidate(TimestampMixin, Base):
    """Tracks pending and reviewed graph knowledge candidates."""

    __tablename__ = "graph_knowledge_candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    document_uuid: Mapped[UUID] = mapped_column(ForeignKey("knowledge_documents.uuid", ondelete="CASCADE"), nullable=False, index=True)
    chunk_id: Mapped[UUID] = mapped_column(ForeignKey("document_chunks.chunk_id", ondelete="CASCADE"), nullable=False, index=True)
    
    subject_label: Mapped[str] = mapped_column(String, nullable=False)
    subject_name: Mapped[str] = mapped_column(String, nullable=False)
    predicate: Mapped[str] = mapped_column(String, nullable=False)
    object_label: Mapped[str] = mapped_column(String, nullable=False)
    object_name: Mapped[str] = mapped_column(String, nullable=False)
    
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    extraction_model: Mapped[str] = mapped_column(String, nullable=False)
    
    review_status: Mapped[str] = mapped_column(String, nullable=False, default="PENDING", index=True) # PENDING, APPROVED, REJECTED
    reviewed_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.uuid", ondelete="SET NULL"), nullable=True)
    review_note: Mapped[str | None] = mapped_column(String, nullable=True)
    
    neo4j_rel_id: Mapped[str | None] = mapped_column(String, nullable=True)
