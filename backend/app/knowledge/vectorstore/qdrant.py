"""Qdrant vector store implementation.

Wraps the official qdrant-client with the BaseVectorStore protocol.

Collection
----------
Name      : krishios_documents  (configurable via settings)
Distance  : Cosine
Vector dim: 384 (all-MiniLM-L6-v2 default, configurable)

Payload schema per point
------------------------
document_id   str   — KnowledgeDocument UUID
chunk_id      str   — DocumentChunk UUID (= point_id)
chunk_text    str   — Raw chunk text (stored for retrieval without SQL round-trip)
page_number   int
chunk_index   int
language      str
crop          str | null
district      str | null
state         str | null
season        str | null
authority     str | null

Design decisions
----------------
* Uses async QdrantClient (AsyncQdrantClient) to avoid blocking the event loop.
* Collection creation is idempotent — safe to call on every startup.
* Batch upserts use Qdrant's native PointStruct format.
* Search filters are built using the Qdrant models API (not raw dicts)
  so the filter schema is validated at construction time.
"""

from __future__ import annotations

from uuid import UUID

from loguru import logger
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qmodels

from app.knowledge.interfaces.vectorstore import (
    BaseVectorStore,
    SearchFilter,
    SearchResult,
    VectorPoint,
)


class QdrantVectorStore:
    """Qdrant-backed implementation of the BaseVectorStore protocol.

    Parameters
    ----------
    host:
        Qdrant server hostname.
    port:
        Qdrant gRPC/HTTP port (default 6333).
    collection_name:
        Name of the Qdrant collection to use.
    """

    def __init__(
        self,
        host: str,
        port: int,
        collection_name: str = "krishios_documents",
    ) -> None:
        self._client = AsyncQdrantClient(host=host, port=port)
        self._collection = collection_name

    # ── Collection management ─────────────────────────────────────────────

    async def ensure_collection(self, vector_size: int = 384) -> None:
        """Create the Qdrant collection if it does not already exist.

        This operation is idempotent and safe to call on every startup.
        Raises on unexpected errors (e.g. server unavailable).
        """
        existing = await self._client.get_collections()
        names = [c.name for c in existing.collections]

        if self._collection in names:
            logger.debug("QdrantVectorStore: collection '{}' already exists", self._collection)
            return

        await self._client.create_collection(
            collection_name=self._collection,
            vectors_config=qmodels.VectorParams(
                size=vector_size,
                distance=qmodels.Distance.COSINE,
            ),
        )
        logger.info(
            "QdrantVectorStore: created collection '{}' (dim={})",
            self._collection,
            vector_size,
        )

    # ── Upsert ────────────────────────────────────────────────────────────

    async def upsert(self, points: list[VectorPoint]) -> None:
        """Insert or update a batch of vector points.

        Converts VectorPoint dataclasses to Qdrant PointStruct objects.
        Empty batch is a no-op (not an error).
        """
        if not points:
            return

        qdrant_points = [
            qmodels.PointStruct(
                id=str(p.point_id),
                vector=p.vector,
                payload=p.payload,
            )
            for p in points
        ]

        await self._client.upsert(
            collection_name=self._collection,
            points=qdrant_points,
        )
        logger.info(
            "QdrantVectorStore: upserted {} points into '{}'",
            len(points),
            self._collection,
        )

    # ── Search ────────────────────────────────────────────────────────────

    async def search(
        self,
        query_vector: list[float],
        top_k: int = 5,
        score_threshold: float = 0.3,
        filters: SearchFilter | None = None,
    ) -> list[SearchResult]:
        """Run a nearest-neighbour search with optional payload filters.

        Parameters
        ----------
        query_vector:
            The embedded query vector (same model as index vectors).
        top_k:
            Maximum number of results to return.
        score_threshold:
            Minimum cosine similarity. Results below this are excluded.
        filters:
            Agricultural metadata filters applied server-side before scoring.

        Returns
        -------
        list[SearchResult]
            Ordered list of results, highest score first.
        """
        qdrant_filter = self._build_filter(filters) if filters else None

        response = await self._client.query_points(
            collection_name=self._collection,
            query=query_vector,
            limit=top_k,
            score_threshold=score_threshold,
            query_filter=qdrant_filter,
            with_payload=True,
        )

        search_results: list[SearchResult] = []
        
        for hit in response.points:
            payload = hit.payload or {}
            search_results.append(
                SearchResult(
                    point_id=UUID(str(hit.id)),
                    score=float(hit.score),
                    payload=payload,
                    chunk_text=str(payload.get("chunk_text", "")),
                )
            )

        logger.debug(
            "QdrantVectorStore: search returned {} hits (threshold={})",
            len(search_results),
            score_threshold,
        )
        return search_results

    # ── Deletion ──────────────────────────────────────────────────────────

    async def delete_by_document(self, document_id: str) -> None:
        """Remove all vector points belonging to a specific document.

        Uses a payload filter on the ``document_id`` field.
        """
        await self._client.delete(
            collection_name=self._collection,
            points_selector=qmodels.FilterSelector(
                filter=qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(
                            key="document_id",
                            match=qmodels.MatchValue(value=document_id),
                        )
                    ]
                )
            ),
        )
        logger.info(
            "QdrantVectorStore: deleted all points for document_id={}", document_id
        )

    # ── Internal helpers ───────────────────────────────────────────────────

    @staticmethod
    def _build_filter(f: SearchFilter) -> qmodels.Filter | None:
        """Convert a SearchFilter into a Qdrant Filter object."""
        conditions: list[qmodels.FieldCondition] = []

        field_map: dict[str, str | None] = {
            "language": f.language,
            "crop": f.crop,
            "district": f.district,
            "state": f.state,
            "season": f.season,
            "authority": f.authority,
            "document_id": f.document_id,
        }

        for key, value in field_map.items():
            if value is not None:
                conditions.append(
                    qmodels.FieldCondition(
                        key=key,
                        match=qmodels.MatchValue(value=value),
                    )
                )

        if not conditions:
            return None

        return qmodels.Filter(must=conditions)
