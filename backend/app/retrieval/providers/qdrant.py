"""Qdrant vector store provider for retrieval index management."""

from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qmodels

from app.retrieval.interfaces.providers import VectorStoreProvider
from app.retrieval.interfaces.types import AliasState, RetrievalFilters, RetrievalHit, VectorRecord


class QdrantRetrievalVectorStore(VectorStoreProvider):
    """Qdrant implementation hidden behind the VectorStoreProvider contract."""

    def __init__(self, host: str, port: int) -> None:
        self._client = AsyncQdrantClient(host=host, port=port)

    async def create_collection(self, collection_name: str, vector_size: int) -> None:
        """Create a collection with cosine distance if it does not already exist."""
        if await self.collection_exists(collection_name):
            return
        await self._client.create_collection(
            collection_name=collection_name,
            vectors_config=qmodels.VectorParams(size=vector_size, distance=qmodels.Distance.COSINE),
        )

    async def delete_collection(self, collection_name: str) -> None:
        """Delete a collection if it exists."""
        if await self.collection_exists(collection_name):
            await self._client.delete_collection(collection_name=collection_name)

    async def collection_exists(self, collection_name: str) -> bool:
        """Return whether a collection exists in Qdrant."""
        collections = await self._client.get_collections()
        return any(collection.name == collection_name for collection in collections.collections)

    async def upsert(self, collection_name: str, records: list[VectorRecord]) -> None:
        """Insert or update vector records into a concrete collection."""
        if not records:
            return
        await self._client.upsert(
            collection_name=collection_name,
            points=[
                qmodels.PointStruct(
                    id=str(record.point_id),
                    vector=record.vector,
                    payload=record.payload,
                )
                for record in records
            ],
        )

    async def search(
        self,
        collection_name: str,
        query_vector: list[float],
        top_k: int,
        filters: RetrievalFilters,
        score_threshold: float,
    ) -> list[RetrievalHit]:
        """Search a concrete collection."""
        return await self._search(collection_name, query_vector, top_k, filters, score_threshold)

    async def search_alias(
        self,
        alias_name: str,
        query_vector: list[float],
        top_k: int,
        filters: RetrievalFilters,
        score_threshold: float,
    ) -> list[RetrievalHit]:
        """Search through an alias, keeping callers independent of collection names."""
        return await self._search(alias_name, query_vector, top_k, filters, score_threshold)

    async def switch_alias(self, alias_name: str, collection_name: str) -> AliasState:
        """Atomically switch an alias to a new collection."""
        operations: list[qmodels.CreateAliasOperation | qmodels.DeleteAliasOperation] = []
        current = await self.get_alias_state(alias_name)
        if current.collection_name is not None:
            operations.append(
                qmodels.DeleteAliasOperation(
                    delete_alias=qmodels.DeleteAlias(alias_name=alias_name)
                )
            )
        operations.append(
            qmodels.CreateAliasOperation(
                create_alias=qmodels.CreateAlias(
                    collection_name=collection_name,
                    alias_name=alias_name,
                )
            )
        )
        await self._client.update_collection_aliases(change_aliases_operations=operations)
        return AliasState(alias_name=alias_name, collection_name=collection_name)

    async def get_alias_state(self, alias_name: str) -> AliasState:
        """Return current alias target, if present."""
        aliases = await self._client.get_aliases()
        for alias in aliases.aliases:
            if alias.alias_name == alias_name:
                return AliasState(alias_name=alias_name, collection_name=alias.collection_name)
        return AliasState(alias_name=alias_name, collection_name=None)

    async def count(self, collection_name: str) -> int:
        """Return vector count for a collection."""
        result = await self._client.count(collection_name=collection_name, exact=True)
        return int(result.count)

    async def _search(
        self,
        target: str,
        query_vector: list[float],
        top_k: int,
        filters: RetrievalFilters,
        score_threshold: float,
    ) -> list[RetrievalHit]:
        qdrant_filter = self._build_filter(filters)
        hits = await self._client.search(
            collection_name=target,
            query_vector=query_vector,
            query_filter=qdrant_filter,
            limit=top_k,
            score_threshold=score_threshold,
            with_payload=True,
        )
        return [
            RetrievalHit(
                chunk_id=str((hit.payload or {}).get("chunk_id", hit.id)),
                chunk_text=str((hit.payload or {}).get("chunk_text", "")),
                similarity=float(hit.score),
                collection=target,
                metadata=dict(hit.payload or {}),
            )
            for hit in hits
        ]

    @staticmethod
    def _build_filter(filters: RetrievalFilters) -> qmodels.Filter | None:
        conditions: list[qmodels.FieldCondition] = []
        for key in (
            "crop",
            "state",
            "district",
            "season",
            "language",
            "authority",
            "document_type",
        ):
            value = getattr(filters, key)
            if value is not None:
                conditions.append(
                    qmodels.FieldCondition(key=key, match=qmodels.MatchValue(value=value))
                )
        if not conditions:
            return None
        return qmodels.Filter(must=conditions)

