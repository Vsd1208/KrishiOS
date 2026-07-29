"""Persistence models for enterprise retrieval index management."""

from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import TimestampMixin


class RetrievalIndexKind(StrEnum):
    """Logical index families supported by the retrieval platform."""

    GOVERNMENT_DOCUMENTS = "government_documents"
    RESEARCH_PAPERS = "research_papers"
    OFFICER_REPORTS = "officer_reports"
    WEATHER_ADVISORIES = "weather_advisories"
    KNOWLEDGE_GRAPH = "knowledge_graph"
    BASE = "base"
    DELTA = "delta"


class RetrievalIndexStatus(StrEnum):
    """Lifecycle status for a versioned vector index."""

    BUILDING = "building"
    VALIDATING = "validating"
    READY = "ready"
    ACTIVE = "active"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    DELETED = "deleted"


class RetrievalBuildMode(StrEnum):
    """Supported index build strategies."""

    FULL = "full"
    INCREMENTAL = "incremental"
    DELTA = "delta"
    BLUE_GREEN = "blue_green"


class RetrievalIndexVersion(TimestampMixin, Base):
    """Versioned retrieval index with deployment and validation metadata."""

    __tablename__ = "retrieval_index_version"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    collection_name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    alias_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    index_kind: Mapped[RetrievalIndexKind] = mapped_column(
        Enum(RetrievalIndexKind, name="retrieval_index_kind"),
        nullable=False,
        default=RetrievalIndexKind.BASE,
    )
    status: Mapped[RetrievalIndexStatus] = mapped_column(
        Enum(RetrievalIndexStatus, name="retrieval_index_status"),
        nullable=False,
        default=RetrievalIndexStatus.BUILDING,
        index=True,
    )
    build_mode: Mapped[RetrievalBuildMode] = mapped_column(
        Enum(RetrievalBuildMode, name="retrieval_build_mode"),
        nullable=False,
        default=RetrievalBuildMode.BLUE_GREEN,
    )
    embedding_model: Mapped[str] = mapped_column(String(200), nullable=False)
    embedding_version: Mapped[str] = mapped_column(String(50), nullable=False)
    vector_size: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    document_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    validation_report: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    promoted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rolled_back_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    document_states: Mapped[list["IndexedDocumentState"]] = relationship(
        "IndexedDocumentState",
        back_populates="index_version",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("alias_name", "version_number", name="uq_retrieval_alias_version"),
        Index("ix_retrieval_index_kind_status", "index_kind", "status"),
    )


class IndexedDocumentState(TimestampMixin, Base):
    """Incremental indexing state for one document inside one index version."""

    __tablename__ = "indexed_document_state"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    index_version_id: Mapped[int] = mapped_column(
        ForeignKey("retrieval_index_version.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge_document.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    content_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    embedding_version: Mapped[str] = mapped_column(String(50), nullable=False)
    last_modified: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_indexed: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    index_version: Mapped["RetrievalIndexVersion"] = relationship(back_populates="document_states")

    __table_args__ = (
        UniqueConstraint("index_version_id", "document_id", name="uq_indexed_document_state"),
        Index("ix_indexed_document_hash_version", "document_hash", "embedding_version"),
    )
