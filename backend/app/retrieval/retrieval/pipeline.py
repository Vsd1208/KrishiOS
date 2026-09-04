"""Enterprise retrieval pipeline consumed by future AI agents."""

from dataclasses import dataclass
from datetime import UTC, datetime
from time import perf_counter

from app.retrieval.citations.builder import CitationBuilder
from app.retrieval.interfaces.providers import (
    EmbeddingProvider,
    RerankerProvider,
    VectorStoreProvider,
)
from app.retrieval.interfaces.types import Citation, RetrievalFilters, RetrievalHit
from app.retrieval.ranking.engine import RankingEngine
from app.retrieval.retrieval.context import ContextBuilder
from app.retrieval.retrieval.metadata import QueryMetadataExtractor
from app.retrieval.retrieval.multi_index import MultiIndexRetriever


@dataclass(frozen=True, slots=True)
class RankedRetrievalResult:
    """Final ranked retrieval result with citations and scoring signals."""

    answer_context: str
    hit: RetrievalHit
    ranking_score: float
    freshness_score: float
    authority_score: float
    citation: Citation


@dataclass(frozen=True, slots=True)
class RetrievalPipelineResult:
    """Complete retrieval pipeline output."""

    query: str
    latency_ms: float
    results: list[RankedRetrievalResult]


class EnterpriseRetrievalPipeline:
    """Run metadata-aware dense retrieval, reranking, ranking, and citation building."""

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStoreProvider,
        reranker: RerankerProvider,
        ranking_engine: RankingEngine,
        context_builder: ContextBuilder,
        citation_builder: CitationBuilder,
        metadata_extractor: QueryMetadataExtractor,
        live_alias: str,
        delta_alias: str,
        multi_index_retriever: MultiIndexRetriever | None = None,
    ) -> None:
        self._embedding_provider = embedding_provider
        self._vector_store = vector_store
        self._reranker = reranker
        self._ranking_engine = ranking_engine
        self._context_builder = context_builder
        self._citation_builder = citation_builder
        self._metadata_extractor = metadata_extractor
        self._live_alias = live_alias
        self._delta_alias = delta_alias
        self._multi_index_retriever = multi_index_retriever

    async def search(
        self,
        query: str,
        filters: RetrievalFilters,
        top_k: int,
        score_threshold: float,
        include_delta: bool,
    ) -> RetrievalPipelineResult:
        """Execute the enterprise retrieval pipeline."""
        started = perf_counter()

        merged_filters = self._metadata_extractor.merge(query, filters)

        query_vector = await self._embedding_provider.embed_query(query)

        raw_hits = await self._retrieve(
            query_vector,
            merged_filters,
            top_k,
            score_threshold,
            include_delta,
        )

        fresh_hits = [
            hit
            for hit in raw_hits
            if self._is_fresh(hit, merged_filters.effective_at)
        ]

        deduped_hits = self._deduplicate(fresh_hits)

        reranked_hits = await self._reranker.rerank(
            query,
            deduped_hits,
        )

        ranked = self._rank(
            reranked_hits,
            merged_filters,
            top_k,
        )

        latency_ms = (perf_counter() - started) * 1000

        return RetrievalPipelineResult(
            query=query,
            latency_ms=latency_ms,
            results=ranked,
        )

    async def _retrieve(
        self,
        query_vector: list[float],
        filters: RetrievalFilters,
        top_k: int,
        score_threshold: float,
        include_delta: bool,
    ) -> list[RetrievalHit]:
        """Retrieve with progressively relaxed contextual filters."""

        async def search_with_filters(
            current_filters: RetrievalFilters,
        ) -> list[RetrievalHit]:
            live_hits = await self._vector_store.search_alias(
                self._live_alias,
                query_vector,
                top_k,
                current_filters,
                score_threshold,
            )

            if not include_delta:
                return live_hits

            delta_state = await self._vector_store.get_alias_state(
                self._delta_alias
            )

            if delta_state.collection_name is None:
                return live_hits

            delta_hits = await self._vector_store.search_alias(
                self._delta_alias,
                query_vector,
                top_k,
                current_filters,
                score_threshold,
            )

            return [*live_hits, *delta_hits]

        # ---------------------------------------------------------
        # 1. Strict contextual retrieval
        # ---------------------------------------------------------
        hits = await search_with_filters(filters)

        if hits:
            return hits

        # ---------------------------------------------------------
        # 2. Relax district
        # ---------------------------------------------------------
        if filters.district is not None:
            relaxed_filters = RetrievalFilters(
                crop=filters.crop,
                state=filters.state,
                district=None,
                season=filters.season,
                language=filters.language,
                authority=filters.authority,
                document_type=filters.document_type,
                effective_at=filters.effective_at,
            )

            hits = await search_with_filters(relaxed_filters)

            if hits:
                return hits

        # ---------------------------------------------------------
        # 3. Relax state
        # ---------------------------------------------------------
        if filters.state is not None:
            relaxed_filters = RetrievalFilters(
                crop=filters.crop,
                state=None,
                district=None,
                season=filters.season,
                language=filters.language,
                authority=filters.authority,
                document_type=filters.document_type,
                effective_at=filters.effective_at,
            )

            hits = await search_with_filters(relaxed_filters)

            if hits:
                return hits

        # ---------------------------------------------------------
        # 4. Relax season
        # ---------------------------------------------------------
        if filters.season is not None:
            relaxed_filters = RetrievalFilters(
                crop=filters.crop,
                state=None,
                district=None,
                season=None,
                language=filters.language,
                authority=filters.authority,
                document_type=filters.document_type,
                effective_at=filters.effective_at,
            )

            hits = await search_with_filters(relaxed_filters)

            if hits:
                return hits

        # ---------------------------------------------------------
        # 5. Crop-only retrieval
        # ---------------------------------------------------------
        if filters.crop is not None:
            relaxed_filters = RetrievalFilters(
                crop=filters.crop,
                state=None,
                district=None,
                season=None,
                language=filters.language,
                authority=filters.authority,
                document_type=filters.document_type,
                effective_at=filters.effective_at,
            )

            hits = await search_with_filters(relaxed_filters)

            if hits:
                return hits

        return []

    def _rank(
        self,
        hits: list[RetrievalHit],
        filters: RetrievalFilters,
        top_k: int,
    ) -> list[RankedRetrievalResult]:
        """Rank retrieved results and attach context and citations."""
        scored: list[RankedRetrievalResult] = []

        for hit in hits:
            score, signals = self._ranking_engine.score(
                hit,
                filters,
            )

            scored.append(
                RankedRetrievalResult(
                    answer_context=self._context_builder.build(hit),
                    hit=hit,
                    ranking_score=score,
                    freshness_score=signals.freshness_score,
                    authority_score=signals.authority_score,
                    citation=self._citation_builder.build(hit),
                )
            )

        return sorted(
            scored,
            key=lambda result: result.ranking_score,
            reverse=True,
        )[:top_k]

    @staticmethod
    def _deduplicate(
        hits: list[RetrievalHit],
    ) -> list[RetrievalHit]:
        """Remove duplicate chunks while keeping the strongest match."""
        seen: set[str] = set()
        unique: list[RetrievalHit] = []

        for hit in sorted(
            hits,
            key=lambda item: item.similarity,
            reverse=True,
        ):
            if hit.chunk_id in seen:
                continue

            seen.add(hit.chunk_id)
            unique.append(hit)

        return unique

    @staticmethod
    def _is_fresh(
        hit: RetrievalHit,
        effective_at: datetime | None,
    ) -> bool:
        """Check whether a retrieval result is still effective."""
        reference = effective_at or datetime.now(UTC)

        effective_until = hit.metadata.get("effective_until")

        if effective_until is None:
            return True

        try:
            expires = datetime.fromisoformat(str(effective_until))
        except ValueError:
            return True

        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)

        return expires >= reference