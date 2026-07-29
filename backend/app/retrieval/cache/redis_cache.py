"""Redis cache for retrieval and embedding workloads."""

import hashlib
import json
from typing import Any

from redis.asyncio import Redis


class RetrievalCache:
    """Cache retrieval artifacts with deterministic namespaced keys."""

    def __init__(self, redis_url: str, ttl_seconds: int) -> None:
        self._redis = Redis.from_url(redis_url, decode_responses=True)
        self._ttl_seconds = ttl_seconds

    async def get_json(self, namespace: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        """Read a JSON value from cache."""
        raw = await self._redis.get(self._key(namespace, payload))
        if raw is None:
            return None
        return json.loads(raw)

    async def set_json(self, namespace: str, payload: dict[str, Any], value: dict[str, Any]) -> None:
        """Write a JSON value to cache."""
        await self._redis.setex(
            self._key(namespace, payload),
            self._ttl_seconds,
            json.dumps(value, sort_keys=True, default=str),
        )

    async def close(self) -> None:
        """Close the Redis connection."""
        await self._redis.aclose()

    @staticmethod
    def _key(namespace: str, payload: dict[str, Any]) -> str:
        encoded = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        digest = hashlib.sha256(encoded).hexdigest()
        return f"retrieval:{namespace}:{digest}"

