"""Job specification and the generic runner (idempotency + health + retries)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from time import perf_counter
from typing import Any

from loguru import logger

from app.worker.store import JobStore, _now

JobFunc = Callable[[dict[str, Any]], Awaitable[dict[str, Any] | None]]


class JobSkipped(Exception):  # noqa: N818 - control-flow signal, not an error
    """Raised by a job to record a deliberate skip (e.g. source not configured)."""


@dataclass(frozen=True, slots=True)
class JobSpec:
    """A scheduled job.

    ``interval_seconds`` defines both the cron cadence and the idempotency slot: a slot is
    ``floor(now / interval)``, so two workers firing in the same slot run the job once.
    """

    name: str
    func: JobFunc
    interval_seconds: int
    timeout_seconds: int = 300
    max_tries: int = 3
    description: str = ""
    enabled: bool = True

    def slot_key(self, at: datetime | None = None) -> str:
        ts = (at or datetime.now(UTC)).timestamp()
        return f"{self.name}:{int(ts // self.interval_seconds)}"


async def run_job(spec: JobSpec, store: JobStore, ctx: dict[str, Any],
                  at: datetime | None = None) -> str:
    """Run one scheduled slot of ``spec``. Returns the final status.

    Raises the job's exception after recording it, so arq's retry policy applies.
    """
    key = spec.slot_key(at)
    if not await store.claim(key, ttl_seconds=spec.interval_seconds):
        logger.info("Job slot already claimed | job={} | slot={}", spec.name, key)
        return "duplicate"

    state = await store.load(spec.name, spec.interval_seconds)
    state.last_started_at = _now()
    state.last_status = "running"
    await store.save(state)
    t0 = perf_counter()
    try:
        result = await spec.func(ctx) or {}
    except JobSkipped as skip:
        state.last_status = "skipped"
        state.last_error = str(skip) or None
        state.runs_skipped += 1
        return "skipped"
    except Exception as exc:
        state.last_status = "failed"
        state.last_error = f"{type(exc).__name__}: {exc}"[:500]
        state.consecutive_failures += 1
        state.runs_failed += 1
        await store.release(key)  # allow arq to retry this slot
        logger.exception("Job failed | job={} | slot={}", spec.name, key)
        raise
    else:
        state.last_status = "success"
        state.last_error = None
        state.last_success_at = _now()
        state.consecutive_failures = 0
        state.runs_ok += 1
        state.last_result = result
        return "success"
    finally:
        state.last_finished_at = _now()
        state.last_duration_ms = round((perf_counter() - t0) * 1000, 2)
        await store.save(state)
