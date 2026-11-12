"""Job registry. Feed jobs (weather_feed, bulletin_poll, market_feed, forecast_import) are
added in Phases 5 and 8; each is a ``JobSpec`` appended to ``JOBS``."""

from __future__ import annotations

from app.config.settings import get_settings
from app.worker.jobs.base import JobSkipped, JobSpec, run_job
from app.worker.jobs.heartbeat import heartbeat


def build_jobs() -> list[JobSpec]:
    settings = get_settings()
    return [
        JobSpec(
            name="heartbeat",
            func=heartbeat,
            interval_seconds=settings.WORKER_HEARTBEAT_INTERVAL_SECONDS,
            timeout_seconds=30,
            max_tries=1,
            description="Scheduler liveness signal.",
        ),
    ]


__all__ = ["JobSkipped", "JobSpec", "build_jobs", "run_job"]
