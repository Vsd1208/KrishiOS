"""Phase 10c: background jobs for document analysis (minutes on a laptop GPU, too long to hold a
request open).

Jobs run one at a time (one GPU), in submission order. Results live only in this process's
memory and expire after ``TTL_SECONDS``: a farmer's document and its summary are personal data
and are never written to disk. Only the user who submitted a job can read it.

Single backend process only: with several workers, a job would be invisible to the others; a
shared store (e.g. Redis) would be needed then.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

TTL_SECONDS = 3600


@dataclass(slots=True)
class Job:
    job_id: str
    owner: str
    status: str = "queued"  # queued | running | done | failed
    result: Any = None
    error: str | None = None
    created: float = field(default_factory=time.time)
    seq: int = 0  # submission order
    finished: float | None = None


class JobStore:
    def __init__(self, ttl_seconds: int = TTL_SECONDS) -> None:
        self._jobs: dict[str, Job] = {}
        self._ttl = ttl_seconds
        self._gpu = asyncio.Semaphore(1)
        self._tasks: set[asyncio.Task] = set()
        self._seq = 0

    def _expire(self) -> None:
        now = time.time()
        for job_id in [j for j, job in self._jobs.items()
                       if job.finished and now - job.finished > self._ttl]:
            del self._jobs[job_id]

    def submit(self, owner: str, work: Callable[[], Awaitable[Any]]) -> Job:
        self._expire()
        self._seq += 1
        job = Job(job_id=uuid.uuid4().hex, owner=owner, seq=self._seq)
        self._jobs[job.job_id] = job

        async def run() -> None:
            async with self._gpu:
                job.status = "running"
                try:
                    job.result = await work()
                    job.status = "done"
                except Exception as exc:
                    job.status, job.error = "failed", type(exc).__name__
                finally:
                    job.finished = time.time()

        task = asyncio.create_task(run())
        self._tasks.add(task)  # keep a reference until it finishes
        task.add_done_callback(self._tasks.discard)
        return job

    def get(self, job_id: str, owner: str) -> Job | None:
        """The job, or None if it does not exist, expired, or belongs to someone else."""
        self._expire()
        job = self._jobs.get(job_id)
        return job if job is not None and job.owner == owner else None

    def position(self, job: Job) -> int:
        """Jobs ahead of this one (0 = running or next)."""
        return sum(1 for j in self._jobs.values()
                   if j.status == "queued" and j.seq < job.seq)


_store: JobStore | None = None


def get_job_store() -> JobStore:
    global _store  # noqa: PLW0603 - one store per process
    if _store is None:
        _store = JobStore()
    return _store
