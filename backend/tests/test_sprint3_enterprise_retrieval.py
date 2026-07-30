"""Unit tests for Sprint 3 Enterprise Knowledge Retrieval Platform extensions."""

import pytest
from app.retrieval.ingestion.incremental import IncrementalIngestionService
from app.retrieval.retrieval.multi_index import MultiIndexRetriever
from app.retrieval.monitoring.observability import RetrievalObservabilityService
from app.retrieval.metrics.collector import MetricsCollector


def test_incremental_checksum() -> None:
    texts = ["Chunk 1 about wheat", "Chunk 2 about soil"]
    checksum1 = IncrementalIngestionService.compute_checksum(texts)
    checksum2 = IncrementalIngestionService.compute_checksum(texts)

    assert len(checksum1) == 64  # SHA-256
    assert checksum1 == checksum2


def test_multi_index_alias_selection() -> None:
    retriever = MultiIndexRetriever(vector_store=None, embedding_provider=None)
    aliases = retriever._select_aliases(["government", "research"])

    assert len(aliases) == 2
    assert "krishios-gov-docs" in aliases
    assert "krishios-research" in aliases


def test_metrics_collector() -> None:
    metrics = MetricsCollector()
    metrics.record("latency.retrieval", 12.5)
    metrics.record("latency.retrieval", 27.5)

    summary = metrics.summarize()
    assert summary.get("latency.retrieval.avg") == 20.0
