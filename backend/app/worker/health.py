"""Job health evaluation for ``GET /api/v1/health/jobs``."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from app.worker.jobs.base import JobSpec
from app.worker.store import JobRunState, JobStore


@dataclass(frozen=True, slots=True)
class JobHealth:
    job: str
    status: str  # ok | stale | failing | never_run | disabled
    interval_seconds: int
    freshness_lag_seconds: float | None
    state: JobRunState


def evaluate(spec: JobSpec, state: JobRunState, stale_factor: float,
             now: datetime | None = None) -> JobHealth:
    """Classify one job. ``freshness_lag`` = seconds since the last successful run."""
    now = now or datetime.now(UTC)
    lag = None
    if state.last_success_at:
        lag = (now - datetime.fromisoformat(state.last_success_at)).total_seconds()
    if not spec.enabled:
        status = "disabled"
    elif state.last_status == "never_run" and lag is None:
        status = "never_run"
    elif state.consecutive_failures > 0 and state.last_status == "failed":
        status = "failing"
    elif lag is None or lag > spec.interval_seconds * stale_factor:
        status = "stale"
    else:
        status = "ok"
    return JobHealth(spec.name, status, spec.interval_seconds, lag, state)


async def collect(specs: list[JobSpec], store: JobStore, stale_factor: float) -> list[JobHealth]:
    return [
        evaluate(spec, await store.load(spec.name, spec.interval_seconds), stale_factor)
        for spec in specs
    ]
