"""Protocols that decouple retrieval services from concrete providers."""

from typing import Protocol

from app.retrieval.interfaces.types import (
    AliasState,
    RetrievalFilters,
    RetrievalHit,
    VectorRecord,
)


class EmbeddingProvider(Protocol):
    """Contract for dense embedding providers."""

    @property
    def model_name(self) -> str:
        """Return the model identifier used to create embeddings."""

    @property
    def model_version(self) -> str:
        """Return the version tag used for cache invalidation."""

    @property
    def vector_size(self) -> int:
        """Return the embedding dimension."""

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts for indexing."""

    async def embed_query(self, query: str) -> list[float]:
        """Embed a search query."""


class VectorStoreProvider(Protocol):
    """Contract for vector stores supporting blue-green retrieval indexes."""

    async def create_collection(self, collection_name: str, vector_size: int) -> None:
        """Create a vector collection if it does not exist."""

    async def delete_collection(self, collection_name: str) -> None:
        """Delete a vector collection."""

    async def collection_exists(self, collection_name: str) -> bool:
        """Return whether the collection exists."""

    async def upsert(self, collection_name: str, records: list[VectorRecord]) -> None:
        """Insert or update vector records into a collection."""

    async def search(
        self,
        collection_name: str,
        query_vector: list[float],
        top_k: int,
        filters: RetrievalFilters,
        score_threshold: float,
    ) -> list[RetrievalHit]:
        """Search a concrete collection."""

    async def search_alias(
        self,
        alias_name: str,
        query_vector: list[float],
        top_k: int,
        filters: RetrievalFilters,
        score_threshold: float,
    ) -> list[RetrievalHit]:
        """Search through an alias instead of a concrete collection."""

    async def switch_alias(self, alias_name: str, collection_name: str) -> AliasState:
        """Atomically repoint an alias to a collection."""

    async def get_alias_state(self, alias_name: str) -> AliasState:
        """Return the collection currently targeted by an alias."""

    async def count(self, collection_name: str) -> int:
        """Return vector count for a collection."""


class RerankerProvider(Protocol):
    """Contract for cross-encoder or future reranking providers."""

    async def rerank(self, query: str, hits: list[RetrievalHit]) -> list[RetrievalHit]:
        """Return hits reordered or rescored by a reranker."""


class OCRProvider(Protocol):
    """Contract for OCR providers used by upstream ingestion."""

    async def extract_text(self, file_path: str) -> str:
        """Extract text from an image or scanned document."""


class ChunkerProvider(Protocol):
    """Contract for chunkers used by upstream ingestion."""

    async def chunk(self, text: str, metadata: dict[str, object]) -> list[dict[str, object]]:
        """Split text into retrieval chunks with metadata."""


class LLMProvider(Protocol):
    """Reserved contract for future answer generation without coupling Sprint 3 to an LLM."""

    async def count_tokens(self, text: str) -> int:
        """Count tokens for context budgeting without generating text."""
