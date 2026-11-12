"""Redis-backed job run records and idempotency keys.

The store depends only on a tiny async subset of the redis client API so tests can use an
in-memory fake.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol

KEY_PREFIX = "krishios:worker"


class RedisLike(Protocol):
    async def get(self, name: str) -> Any: ...
    async def set(self, name: str, value: Any, ex: int | None = None, nx: bool = False) -> Any: ...


@dataclass(slots=True)
class JobRunState:
    """Latest health state for one job."""

    job: str
    interval_seconds: int
    last_started_at: str | None = None
    last_finished_at: str | None = None
    last_success_at: str | None = None
    last_status: str = "never_run"  # never_run | running | success | failed | skipped
    last_error: str | None = None
    last_duration_ms: float | None = None
    consecutive_failures: int = 0
    runs_ok: int = 0
    runs_failed: int = 0
    runs_skipped: int = 0
    last_result: dict[str, Any] = field(default_factory=dict)


def _now() -> str:
    return datetime.now(UTC).isoformat()


class JobStore:
    """Persist job state and claim idempotency slots."""

    def __init__(self, redis: RedisLike) -> None:
        self._redis = redis

    @staticmethod
    def _state_key(job: str) -> str:
        return f"{KEY_PREFIX}:state:{job}"

    async def load(self, job: str, interval_seconds: int) -> JobRunState:
        raw = await self._redis.get(self._state_key(job))
        if raw is None:
            return JobRunState(job=job, interval_seconds=interval_seconds)
        data = json.loads(raw)
        data["interval_seconds"] = interval_seconds
        return JobRunState(**data)

    async def save(self, state: JobRunState) -> None:
        await self._redis.set(self._state_key(state.job), json.dumps(asdict(state)))

    async def claim(self, idempotency_key: str, ttl_seconds: int) -> bool:
        """True if this caller owns the key (first claim within ``ttl_seconds``)."""
        ok = await self._redis.set(f"{KEY_PREFIX}:idem:{idempotency_key}", _now(),
                                   ex=ttl_seconds, nx=True)
        return bool(ok)

    async def release(self, idempotency_key: str) -> None:
        """Release a claim so a failed slot can be retried."""
        delete = getattr(self._redis, "delete", None)
        if delete is not None:
            await delete(f"{KEY_PREFIX}:idem:{idempotency_key}")
