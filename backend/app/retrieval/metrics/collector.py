"""Lightweight metrics collector for retrieval operations."""

from collections import defaultdict
from contextlib import contextmanager
from time import perf_counter
from typing import Iterator

from loguru import logger


class MetricsCollector:
    """Collect and summarize operational metrics for retrieval infrastructure."""

    def __init__(self) -> None:
        self._values: dict[str, list[float]] = defaultdict(list)

    def record(self, metric_name: str, value: float) -> None:
        """Store a numeric observation for a metric."""
        self._values[metric_name].append(float(value))

    def summarize(self) -> dict[str, float]:
        """Return count, sum, average, min, and max values for each metric."""
        summary: dict[str, float] = {}
        for metric_name, values in sorted(self._values.items()):
            if not values:
                continue
            count = float(len(values))
            total = sum(values)
            average = total / count
            summary[f"{metric_name}.count"] = count
            summary[f"{metric_name}.sum"] = total
            summary[f"{metric_name}.avg"] = average
            summary[f"{metric_name}.min"] = min(values)
            summary[f"{metric_name}.max"] = max(values)
        return summary

    @contextmanager
    def timer(self, metric_name: str, **context: object) -> Iterator[None]:
        """Measure elapsed time for an operation and log it."""
        started = perf_counter()
        try:
            yield
        finally:
            elapsed_ms = (perf_counter() - started) * 1000
            self.record(metric_name, elapsed_ms)
            logger.info(
                "retrieval_metric name={} elapsed_ms={:.2f} context={}",
                metric_name,
                elapsed_ms,
                context,
            )


class RetrievalMetricsCollector(MetricsCollector):
    """Backward-compatible alias for the retrieval metrics collector."""


__all__ = ["MetricsCollector", "RetrievalMetricsCollector"]

