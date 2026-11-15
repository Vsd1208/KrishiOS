"""``GET /api/v1/health/jobs``: scheduler and per-job health."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel
from redis.asyncio import Redis

from app.config.settings import get_settings
from app.worker.health import collect
from app.worker.jobs import build_jobs
from app.worker.store import JobStore

router = APIRouter(prefix="/health", tags=["Health"])


class JobHealthOut(BaseModel):
    job: str
    status: str
    interval_seconds: int
    freshness_lag_seconds: float | None
    last_status: str
    last_success_at: str | None
    last_error: str | None
    last_duration_ms: float | None
    consecutive_failures: int
    runs_ok: int
    runs_failed: int
    runs_skipped: int


class JobsHealthResponse(BaseModel):
    status: str  # ok | degraded | unavailable
    jobs: list[JobHealthOut]
    detail: str | None = None


@router.get("/jobs", response_model=JobsHealthResponse)
async def jobs_health() -> JobsHealthResponse:
    settings = get_settings()
    redis = Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB,
                  password=settings.REDIS_PASSWORD, socket_connect_timeout=2)
    try:
        health = await collect(build_jobs(), JobStore(redis), settings.WORKER_JOB_STALE_FACTOR)
    except Exception as exc:  # Redis unreachable: report, do not 500
        return JobsHealthResponse(status="unavailable", jobs=[], detail=type(exc).__name__)
    finally:
        await redis.aclose()
    jobs = [
        JobHealthOut(
            job=h.job, status=h.status, interval_seconds=h.interval_seconds,
            freshness_lag_seconds=h.freshness_lag_seconds, last_status=h.state.last_status,
            last_success_at=h.state.last_success_at, last_error=h.state.last_error,
            last_duration_ms=h.state.last_duration_ms,
            consecutive_failures=h.state.consecutive_failures, runs_ok=h.state.runs_ok,
            runs_failed=h.state.runs_failed, runs_skipped=h.state.runs_skipped,
        )
        for h in health
    ]
    overall = "ok" if all(j.status in {"ok", "disabled"} for j in jobs) else "degraded"
    return JobsHealthResponse(status=overall, jobs=jobs)
