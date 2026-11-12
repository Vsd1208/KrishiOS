"""Heartbeat job: proves the scheduler is alive (feeds /health/jobs)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


async def heartbeat(ctx: dict[str, Any]) -> dict[str, Any]:
    return {"at": datetime.now(UTC).isoformat()}
