"""Abstract vector store protocol.

The Qdrant implementation satisfies this protocol. Keeping the API
behind a protocol allows future swaps (e.g. pgvector, Weaviate) without
touching any upstream code.
"""

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable
from uuid import UUID


@dataclass(frozen=True, slots=True)
class VectorPoint:
    """A single embedding record ready to be upserted into the vector store.

    Attributes
    ----------
    point_id:
        Unique identifier for this vector point. Maps to `chunk_id` in the
        DocumentChunk table so SQL and Qdrant records stay in sync.
    vector:
        Dense embedding produced by the embedding pipeline.
    payload:
        Metadata persisted alongside the vector in Qdrant for filtered search.
        Must include at minimum: document_id, page_number, chunk_index.
    """

    point_id: UUID
    vector: list[float]
    payload: dict[str, str | int | float | bool] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SearchResult:
    """A single result returned by a vector similarity search.

    Attributes
    ----------
    point_id:
        Chunk UUID corresponding to a DocumentChunk row.
    score:
        Cosine similarity score in [0, 1]. Higher is more relevant.
    payload:
        Full Qdrant payload: document_id, page_number, crop, etc.
    chunk_text:
        The original chunk text stored in the payload.
    """

    point_id: UUID
    score: float
    payload: dict[str, str | int | float | bool]
    chunk_text: str


@dataclass(frozen=True, slots=True)
class SearchFilter:
    """Metadata filters applied server-side in Qdrant before scoring.

    All fields are optional. Only non-None fields are applied.
    Multiple fields are combined with AND logic.
    """

    language: str | None = None
    crop: str | None = None
    district: str | None = None
    state: str | None = None
    season: str | None = None
    authority: str | None = None
    document_id: str | None = None


@runtime_checkable
class BaseVectorStore(Protocol):
    """Contract that every vector store implementation must satisfy."""

    async def ensure_collection(self, vector_size: int) -> None:
        """Create the collection if it does not already exist."""
        ...

    async def upsert(self, points: list[VectorPoint]) -> None:
        """Insert or update a batch of vector points."""
        ...

    async def search(
        self,
        query_vector: list[float],
        top_k: int,
        score_threshold: float,
        filters: SearchFilter | None,
    ) -> list[SearchResult]:
        """Run a nearest-neighbour search and return ranked results."""
        ...

    async def delete_by_document(self, document_id: str) -> None:
        """Remove all vector points belonging to a given document."""
        ...
