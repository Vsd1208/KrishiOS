"""Job registry. Feed jobs (weather_feed, bulletin_poll, market_feed, forecast_import) are
added in Phases 5 and 8; each is a ``JobSpec`` appended to ``JOBS``."""

from __future__ import annotations

from app.config.settings import get_settings
from app.worker.jobs.base import JobSkipped, JobSpec, run_job
from app.worker.jobs.feeds import mandi_history, sachet_poll, weather_feed
from app.worker.jobs.forecasting import forecast_import
from app.worker.jobs.govconnect import govconnect_maintenance
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
        JobSpec(
            name="govconnect_maintenance",
            func=govconnect_maintenance,
            interval_seconds=settings.GOVCONNECT_MAINTENANCE_INTERVAL_SECONDS,
            timeout_seconds=600,
            max_tries=3,
            description="Publish scheduled bulletins, expire old ones, retry RAG indexing.",
        ),
        JobSpec(
            name="sachet_poll",
            func=sachet_poll,
            interval_seconds=settings.SACHET_POLL_INTERVAL_SECONDS,
            timeout_seconds=900,
            max_tries=3,
            description="NDMA SACHET CAP warnings -> Govt Connect bulletins (officer review).",
        ),
        JobSpec(
            name="weather_feed",
            func=weather_feed,
            interval_seconds=settings.WEATHER_FEED_INTERVAL_SECONDS,
            timeout_seconds=1800,
            max_tries=2,
            description="District forecasts + NASA POWER cross-check -> snapshots + events.",
        ),
        JobSpec(
            name="mandi_history",
            func=mandi_history,
            interval_seconds=6 * 3600,
            timeout_seconds=1800,
            max_tries=2,
            description="Official AGMARKNET prices (last 3 days) -> history + sharp-move alerts.",
            enabled=bool(settings.DATA_GOV_IN_API_KEY),
        ),
        JobSpec(
            name="forecast_import",
            func=forecast_import,
            interval_seconds=settings.YIELD_FORECAST_IMPORT_INTERVAL_SECONDS,
            timeout_seconds=900,
            max_tries=2,
            description="Newest ml/ batch forecast -> yield_forecast; shortfalls -> events + "
                        "officer-review drafts.",
        ),
    ]


__all__ = ["JobSkipped", "JobSpec", "build_jobs", "run_job"]
