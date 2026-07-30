"""Monitoring collector for runtime execution metrics."""

from __future__ import annotations

from collections import defaultdict


class RuntimeMetricsCollector:
    """Collect execution time, planning time, tool latency, retry, and failure telemetry."""

    def __init__(self) -> None:
        self._values: dict[str, list[float]] = defaultdict(list)
        self._failures: dict[str, int] = defaultdict(int)
        self._agent_runs: dict[str, int] = defaultdict(int)
        self._retry_counts: dict[str, int] = defaultdict(int)

    def record(self, metric_name: str, value: float) -> None:
        """Store a metric observation."""
        self._values[metric_name].append(float(value))

    def record_failure(self, agent_name: str) -> None:
        """Increment failure count for an agent."""
        self._failures[agent_name] += 1
        self.record("failure_count", 1.0)

    def record_retry(self, operation_name: str) -> None:
        """Increment retry count for an operation."""
        self._retry_counts[operation_name] += 1
        self.record("retry_count", 1.0)

    def record_agent_utilization(self, agent_names: list[str]) -> None:
        """Track agent utilization counts."""
        for name in agent_names:
            self._agent_runs[name] += 1

    def summarize(self) -> dict[str, float]:
        """Return summarized metrics for the runtime."""
        summary: dict[str, float] = {}
        for metric_name, values in sorted(self._values.items()):
            if not values:
                continue
            summary[f"{metric_name}.count"] = float(len(values))
            summary[f"{metric_name}.avg"] = sum(values) / len(values)
            summary[f"{metric_name}.max"] = max(values)
            summary[f"{metric_name}.min"] = min(values)

        for agent, count in self._agent_runs.items():
            summary[f"agent_utilization.{agent}"] = float(count)

        for agent, count in self._failures.items():
            summary[f"agent_failures.{agent}"] = float(count)

        return summary

    def reset(self) -> None:
        """Clear all collected metrics."""
        self._values.clear()
        self._failures.clear()
        self._agent_runs.clear()
        self._retry_counts.clear()
