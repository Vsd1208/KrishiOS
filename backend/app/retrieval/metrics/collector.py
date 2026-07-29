"""Lightweight metrics collector for retrieval operations."""

from contextlib import contextmanager
from time import perf_counter
from typing import Iterator

from loguru import logger


class RetrievalMetricsCollector:
    """Collect and log operational timings for retrieval infrastructure."""

    @contextmanager
    def timer(self, metric_name: str, **context: object) -> Iterator[None]:
        """Measure elapsed time for an operation and log it."""
        started = perf_counter()
        try:
            yield
        finally:
            elapsed_ms = (perf_counter() - started) * 1000
            logger.info(
                "retrieval_metric name={} elapsed_ms={:.2f} context={}",
                metric_name,
                elapsed_ms,
                context,
            )

