"""Typed data contracts shared across retrieval components."""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class RetrievalFilters:
    """Metadata filters applied during retrieval and ranking."""

    crop: str | None = None
    state: str | None = None
    district: str | None = None
    season: str | None = None
    language: str | None = None
    authority: str | None = None
    document_type: str | None = None
    effective_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class VectorRecord:
    """A vector point ready for insertion into a vector index."""

    point_id: UUID
    vector: list[float]
    payload: dict[str, str | int | float | bool | None]


@dataclass(frozen=True, slots=True)
class RetrievalHit:
    """Raw retrieval hit returned by a vector store provider."""

    chunk_id: str
    chunk_text: str
    similarity: float
    collection: str
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class EmbeddedDocument:
    """Embeddings for one document's chunks."""

    document_id: int
    document_hash: str
    content_checksum: str
    last_modified: datetime
    vectors: list[VectorRecord]


@dataclass(frozen=True, slots=True)
class IndexBuildRequest:
    """Request to build a new retrieval index version."""

    index_kind: str
    alias_name: str
    build_mode: str
    embedding_model: str
    embedding_version: str
    vector_size: int


@dataclass(frozen=True, slots=True)
class IndexValidationReport:
    """Validation metrics that decide whether an index can be promoted."""

    precision: float
    recall: float
    mrr: float
    ndcg: float
    latency_ms: float
    coverage: float
    chunk_integrity: bool
    embedding_integrity: bool

    @property
    def passed(self) -> bool:
        """Return whether validation metrics meet enterprise promotion gates."""
        return (
            self.precision >= 0.5
            and self.recall >= 0.5
            and self.mrr >= 0.3
            and self.ndcg >= 0.3
            and self.latency_ms <= 1500
            and self.coverage >= 0.8
            and self.chunk_integrity
            and self.embedding_integrity
        )

    def to_dict(self) -> dict[str, float | bool]:
        """Serialize the report for database persistence and API responses."""
        return {
            "precision": self.precision,
            "recall": self.recall,
            "mrr": self.mrr,
            "ndcg": self.ndcg,
            "latency_ms": self.latency_ms,
            "coverage": self.coverage,
            "chunk_integrity": self.chunk_integrity,
            "embedding_integrity": self.embedding_integrity,
            "passed": self.passed,
        }


@dataclass(frozen=True, slots=True)
class AliasState:
    """Current alias-to-collection mapping."""

    alias_name: str
    collection_name: str | None


@dataclass(frozen=True, slots=True)
class RankingSignals:
    """Signals used by the ranking engine to compute final score."""

    semantic_similarity: float
    authority_score: float
    freshness_score: float
    crop_match: float
    state_match: float
    district_match: float
    season_match: float
    language_match: float


@dataclass(frozen=True, slots=True)
class Citation:
    """Citation metadata for a retrieved chunk."""

    document_id: int | None
    title: str | None
    source: str | None
    source_url: str | None
    page_number: int | None
    chunk_id: str
