"""Monitoring collector for runtime execution metrics."""

from __future__ import annotations

from collections import defaultdict


class RuntimeMetricsCollector:
    """Collect execution time, usage, and failure telemetry for the agent runtime."""

    def __init__(self) -> None:
        self._values: dict[str, list[float]] = defaultdict(list)

    def record(self, metric_name: str, value: float) -> None:
        """Store a metric observation."""
        self._values[metric_name].append(float(value))

    def summarize(self) -> dict[str, float]:
        """Return summarized metrics for the runtime."""
        summary: dict[str, float] = {}
        for metric_name, values in sorted(self._values.items()):
            if not values:
                continue
            summary[f"{metric_name}.count"] = float(len(values))
            summary[f"{metric_name}.avg"] = sum(values) / len(values)
        return summary
