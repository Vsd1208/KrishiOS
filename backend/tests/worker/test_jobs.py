"""Worker runner: idempotency, retries, health classification."""

from datetime import UTC, datetime, timedelta

import pytest
from app.worker.health import evaluate
from app.worker.jobs import JobSkipped, JobSpec, build_jobs, run_job
from app.worker.main import WorkerSettings, _cron_seconds
from app.worker.store import JobStore


class FakeRedis:
    """Minimal async stand-in for the redis client subset JobStore uses."""

    def __init__(self) -> None:
        self.data: dict[str, str] = {}

    async def get(self, name):
        return self.data.get(name)

    async def set(self, name, value, ex=None, nx=False):
        if nx and name in self.data:
            return None
        self.data[name] = value
        return True

    async def delete(self, name):
        self.data.pop(name, None)


@pytest.fixture
def store() -> JobStore:
    return JobStore(FakeRedis())


async def _ok(ctx):
    ctx["calls"] = ctx.get("calls", 0) + 1
    return {"n": ctx["calls"]}


async def _boom(ctx):
    raise RuntimeError("source down")


async def _skip(ctx):
    raise JobSkipped("IMD key not configured")


AT = datetime(2026, 11, 12, 10, 0, 30, tzinfo=UTC)


async def test_same_slot_runs_once(store) -> None:
    spec = JobSpec("feed", _ok, interval_seconds=3600)
    ctx: dict = {}
    assert await run_job(spec, store, ctx, at=AT) == "success"
    assert await run_job(spec, store, ctx, at=AT + timedelta(minutes=5)) == "duplicate"
    assert ctx["calls"] == 1
    assert await run_job(spec, store, ctx, at=AT + timedelta(hours=1)) == "success"
    state = await store.load("feed", 3600)
    assert state.runs_ok == 2 and state.last_result == {"n": 2}


async def test_failure_is_recorded_and_slot_released_for_retry(store) -> None:
    spec = JobSpec("feed", _boom, interval_seconds=3600)
    with pytest.raises(RuntimeError):
        await run_job(spec, store, {}, at=AT)
    state = await store.load("feed", 3600)
    assert state.last_status == "failed" and state.consecutive_failures == 1
    assert "source down" in state.last_error
    with pytest.raises(RuntimeError):  # same slot may be retried after a failure
        await run_job(spec, store, {}, at=AT)
    assert (await store.load("feed", 3600)).consecutive_failures == 2


async def test_skip_is_not_failure(store) -> None:
    spec = JobSpec("imd", _skip, interval_seconds=3600)
    assert await run_job(spec, store, {}, at=AT) == "skipped"
    state = await store.load("imd", 3600)
    assert state.runs_skipped == 1 and state.consecutive_failures == 0


async def test_health_classification(store) -> None:
    spec = JobSpec("feed", _ok, interval_seconds=3600)
    assert evaluate(spec, await store.load("feed", 3600), 3.0).status == "never_run"
    await run_job(spec, store, {}, at=datetime.now(UTC))
    state = await store.load("feed", 3600)
    assert evaluate(spec, state, 3.0).status == "ok"
    later = datetime.now(UTC) + timedelta(hours=4)
    assert evaluate(spec, state, 3.0, now=later).status == "stale"


def test_cron_translation() -> None:
    assert _cron_seconds(3600) == {"hour": set(range(24)), "minute": 0, "second": 0}
    assert _cron_seconds(900)["minute"] == {0, 15, 30, 45}


def test_worker_settings_build() -> None:
    names = {c.name for c in WorkerSettings.cron_jobs}
    assert names == {j.name for j in build_jobs() if j.enabled}


def test_jobs_health_endpoint_without_redis(client) -> None:
    body = client.get("/api/v1/health/jobs").json()
    assert body["status"] in {"ok", "degraded", "unavailable"}
