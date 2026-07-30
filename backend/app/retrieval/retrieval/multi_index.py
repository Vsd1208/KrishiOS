"""Multi-Index retrieval orchestrator across specialized domain collections."""

import asyncio
from typing import ClassVar

from app.retrieval.interfaces.providers import EmbeddingProvider, VectorStoreProvider
from app.retrieval.interfaces.types import RetrievalFilters, RetrievalHit


class MultiIndexRetriever:
    """Queries multiple specialized domain vector aliases concurrently and merges results."""

    # Default category aliases for multi-index architecture
    DEFAULT_ALIASES: ClassVar[dict[str, str]] = {
        "government": "krishios-gov-docs",
        "research": "krishios-research",
        "officer": "krishios-officer-reports",
        "weather": "krishios-weather-advisories",
        "knowledge_graph": "krishios-kg",
    }

    def __init__(
        self,
        vector_store: VectorStoreProvider,
        embedding_provider: EmbeddingProvider,
        domain_aliases: dict[str, str] | None = None,
    ) -> None:
        self._vector_store = vector_store
        self._embedding_provider = embedding_provider
        self._domain_aliases = domain_aliases or dict(self.DEFAULT_ALIASES)

    async def search_all_domains(
        self,
        query: str,
        filters: RetrievalFilters,
        top_k: int = 10,
        score_threshold: float = 0.3,
        target_domains: list[str] | None = None,
    ) -> list[RetrievalHit]:
        """Search across target domain indexes concurrently and return merged, deduplicated hits."""
        query_vector = await self._embedding_provider.embed_query(query)
        selected_aliases = self._select_aliases(target_domains)

        # Run vector searches across all target aliases concurrently
        tasks = [
            self._safe_search_alias(
                alias_name=alias,
                query_vector=query_vector,
                top_k=top_k,
                filters=filters,
                score_threshold=score_threshold,
            )
            for alias in selected_aliases
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_hits: list[RetrievalHit] = []
        for res in results:
            if isinstance(res, list):
                all_hits.extend(res)

        return self._deduplicate_and_sort(all_hits, top_k)

    async def _safe_search_alias(
        self,
        alias_name: str,
        query_vector: list[float],
        top_k: int,
        filters: RetrievalFilters,
        score_threshold: float,
    ) -> list[RetrievalHit]:
        """Execute search on an alias safely without failing the entire multi-index query."""
        try:
            state = await self._vector_store.get_alias_state(alias_name)
            if state.collection_name is None:
                return []
            return await self._vector_store.search_alias(
                alias_name,
                query_vector,
                top_k,
                filters,
                score_threshold,
            )
        except Exception:  # Resilience against missing domain collection
            return []

    def _select_aliases(self, target_domains: list[str] | None) -> list[str]:
        if not target_domains:
            return list(self._domain_aliases.values())
        return [
            self._domain_aliases[domain]
            for domain in target_domains
            if domain in self._domain_aliases
        ]

    @staticmethod
    def _deduplicate_and_sort(hits: list[RetrievalHit], top_k: int) -> list[RetrievalHit]:
        seen: set[str] = set()
        deduped: list[RetrievalHit] = []
        for hit in sorted(hits, key=lambda item: item.similarity, reverse=True):
            if hit.chunk_id in seen:
                continue
            seen.add(hit.chunk_id)
            deduped.append(hit)
        return deduped[:top_k]
