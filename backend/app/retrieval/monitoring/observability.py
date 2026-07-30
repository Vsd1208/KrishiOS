"""Enterprise observability, health checking, and telemetry metrics collector."""

import os
import psutil
from dataclasses import dataclass, field
from time import perf_counter

from app.retrieval.metrics.collector import MetricsCollector
from app.retrieval.interfaces.providers import VectorStoreProvider


@dataclass(slots=True)
class IndexHealthReport:
    """System health status for retrieval infrastructure."""

    status: str
    live_alias_target: str | None
    live_vector_count: int
    memory_usage_mb: float
    cache_hit_rate: float
    metrics_summary: dict[str, float] = field(default_factory=dict)


class RetrievalObservabilityService:
    """Collects system telemetry, index health, and execution metrics."""

    def __init__(
        self,
        vector_store: VectorStoreProvider,
        metrics_collector: MetricsCollector,
        live_alias: str = "krishios-live",
    ) -> None:
        self._vector_store = vector_store
        self._metrics = metrics_collector
        self._live_alias = live_alias

    async def get_health_report(self) -> IndexHealthReport:
        """Return system health report including memory, cache stats, and index vector count."""
        process = psutil.Process(os.getpid())
        memory_mb = process.memory_info().rss / (1024 * 1024)

        state = await self._vector_store.get_alias_state(self._live_alias)
        vector_count = 0
        status = "healthy"

        if state.collection_name is not None:
            try:
                vector_count = await self._vector_store.count(state.collection_name)
            except Exception:
                status = "degraded"
        else:
            status = "unconfigured"

        metrics_summary = self._metrics.summarize()
        cache_hits = metrics_summary.get("cache.hit.count", 0.0)
        cache_misses = metrics_summary.get("cache.miss.count", 0.0)
        total_cache = cache_hits + cache_misses
        hit_rate = (cache_hits / total_cache) if total_cache > 0 else 0.0

        return IndexHealthReport(
            status=status,
            live_alias_target=state.collection_name,
            live_vector_count=vector_count,
            memory_usage_mb=round(memory_mb, 2),
            cache_hit_rate=round(hit_rate, 4),
            metrics_summary=metrics_summary,
        )

    def record_stage_latency(self, stage_name: str, duration_ms: float) -> None:
        """Record latency metric for a specific retrieval stage."""
        self._metrics.record(f"latency.{stage_name}", duration_ms)

    def record_token_usage(self, token_count: int) -> None:
        """Record token consumption for budgeting and tracking."""
        self._metrics.record("tokens.consumed", float(token_count))
