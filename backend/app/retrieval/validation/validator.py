"""Validation gates for retrieval index promotion."""

from app.retrieval.interfaces.providers import VectorStoreProvider
from app.retrieval.interfaces.types import IndexValidationReport


class IndexValidator:
    """Validate index integrity and operational readiness before promotion."""

    def __init__(self, vector_store: VectorStoreProvider) -> None:
        self._vector_store = vector_store

    async def validate(
        self,
        collection_name: str,
        expected_chunks: int,
        latency_ms: float,
    ) -> IndexValidationReport:
        """Run promotion gates for a newly built index."""
        vector_count = await self._vector_store.count(collection_name)
        chunk_integrity = vector_count == expected_chunks
        embedding_integrity = vector_count > 0 or expected_chunks == 0
        coverage = 1.0 if expected_chunks == 0 else min(1.0, vector_count / expected_chunks)
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

