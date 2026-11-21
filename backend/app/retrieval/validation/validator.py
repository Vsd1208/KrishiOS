"""Validation gates for retrieval index promotion."""

import math
from collections.abc import Awaitable, Callable
from time import perf_counter

from app.retrieval.interfaces.providers import VectorStoreProvider
from app.retrieval.interfaces.types import IndexValidationReport, RetrievalFilters

PROBE_TOP_K = 5
PROBE_WORDS = 25  # the query is the opening words of the probe passage


class IndexValidator:
    """Validate index integrity and operational readiness before promotion."""

    def __init__(self, vector_store: VectorStoreProvider) -> None:
        self._vector_store = vector_store

    async def validate(
        self,
        collection_name: str,
        expected_chunks: int,
        latency_ms: float,
        probes: list[tuple[str, str]] | None = None,
        embed_query: Callable[[str], Awaitable[list[float]]] | None = None,
    ) -> IndexValidationReport:
        """Run promotion gates for a newly built index.

        With ``probes`` ((chunk_id, chunk_text) pairs) and ``embed_query``, retrieval quality is
        measured: each probe's opening words are searched and the rank of its own passage gives
        precision@1, recall@5, MRR and nDCG@5; latency is the mean query time (embed + search).
        ``latency_ms`` (the build time) is then only reported. Without probes the quality numbers
        follow from the counts alone (method "count_only"), as before.
        """
        vector_count = await self._vector_store.count(collection_name)
        chunk_integrity = vector_count == expected_chunks
        embedding_integrity = vector_count > 0 or expected_chunks == 0
        coverage = 1.0 if expected_chunks == 0 else min(1.0, vector_count / expected_chunks)
        if probes and embed_query is not None:
            ranks, times = [], []
            for chunk_id, text in probes:
                query = " ".join(text.split()[:PROBE_WORDS])
                started = perf_counter()
                hits = await self._vector_store.search(
                    collection_name, await embed_query(query), PROBE_TOP_K, RetrievalFilters(), 0.0)
                times.append((perf_counter() - started) * 1000)
                ids = [h.chunk_id for h in hits]
                ranks.append(ids.index(chunk_id) + 1 if chunk_id in ids else None)
            n = len(ranks)
            return IndexValidationReport(
                precision=sum(r == 1 for r in ranks) / n,
                recall=sum(r is not None for r in ranks) / n,
                mrr=sum(1 / r for r in ranks if r) / n,
                ndcg=sum(1 / math.log2(r + 1) for r in ranks if r) / n,
                latency_ms=sum(times) / n,
                coverage=coverage,
                chunk_integrity=chunk_integrity,
                embedding_integrity=embedding_integrity,
                method="self_retrieval",
                probes=n,
                build_ms=latency_ms,
            )
        precision = 1.0 if chunk_integrity else coverage
        recall = coverage
        mrr = 1.0 if embedding_integrity else 0.0
        ndcg = 1.0 if embedding_integrity else 0.0
        return IndexValidationReport(
            precision=precision,
            recall=recall,
            mrr=mrr,
            ndcg=ndcg,
            latency_ms=latency_ms,
            coverage=coverage,
            chunk_integrity=chunk_integrity,
            embedding_integrity=embedding_integrity,
        )
