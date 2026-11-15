"""arq worker entrypoint: ``uv run arq app.worker.main.WorkerSettings``."""

from __future__ import annotations

from typing import Any, ClassVar

from arq import cron
from arq.connections import RedisSettings
from loguru import logger

from app.config.settings import get_settings
from app.logging.config import configure_logging
from app.worker.jobs import JobSpec, build_jobs, run_job
from app.worker.store import JobStore

MINUTE = 60
HOUR = 3600


def _cron_seconds(interval: int) -> dict[str, Any]:
    """Translate an interval into arq cron fields (minute- or hour-aligned)."""
    if interval < MINUTE:
        return {"second": set(range(0, 60, interval))}
    if interval < HOUR:
        return {"minute": set(range(0, 60, max(1, interval // 60))), "second": 0}
    return {"hour": set(range(0, 24, max(1, interval // 3600))), "minute": 0, "second": 0}


def _make_task(spec: JobSpec):
    async def task(ctx: dict[str, Any]) -> str:
        return await run_job(spec, ctx["job_store"], ctx)

    task.__name__ = f"job_{spec.name}"
    task.__qualname__ = task.__name__
    return task


async def startup(ctx: dict[str, Any]) -> None:
    configure_logging(get_settings())
    ctx["job_store"] = JobStore(ctx["redis"])
    logger.info("KrishiOS worker started")


def _redis_settings() -> RedisSettings:
    s = get_settings()
    return RedisSettings(host=s.REDIS_HOST, port=s.REDIS_PORT, database=s.REDIS_DB,
                         password=s.REDIS_PASSWORD)


_JOBS = [j for j in build_jobs() if j.enabled]
_TASKS = {spec.name: _make_task(spec) for spec in _JOBS}


class WorkerSettings:
    """arq settings object."""

    functions: ClassVar[list] = list(_TASKS.values())
    cron_jobs: ClassVar[list] = [
        cron(_TASKS[spec.name], name=spec.name, timeout=spec.timeout_seconds,
             max_tries=spec.max_tries, run_at_startup=True, unique=True,
             **_cron_seconds(spec.interval_seconds))
        for spec in _JOBS
    ]
    on_startup = startup
    redis_settings = _redis_settings()
    queue_name = get_settings().WORKER_QUEUE_NAME
    job_timeout = get_settings().WORKER_JOB_TIMEOUT_SECONDS
    max_tries = get_settings().WORKER_MAX_TRIES
