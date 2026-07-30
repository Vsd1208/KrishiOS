"""Redis cache for retrieval and embedding workloads."""

import hashlib
import json
from typing import Any

try:
    from redis.asyncio import Redis
except ImportError:  # pragma: no cover - exercised in lightweight environments
    Redis = None  # type: ignore[assignment]


class RetrievalCache:
    """Cache retrieval artifacts with deterministic namespaced keys."""

    def __init__(self, redis_url: str, ttl_seconds: int) -> None:
        self._redis = Redis.from_url(redis_url, decode_responses=True) if Redis is not None else None
        self._ttl_seconds = ttl_seconds
        self._memory: dict[str, tuple[dict[str, Any], int]] = {}

    async def get_json(self, namespace: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        """Read a JSON value from cache."""
        key = self._key(namespace, payload)
        if self._redis is None:
            entry = self._memory.get(key)
            if entry is None:
                return None
            value, expires_at = entry
            if expires_at <= 0:
                self._memory.pop(key, None)
                return None
            return value

        raw = await self._redis.get(key)
        if raw is None:
            return None
        return json.loads(raw)

    async def set_json(self, namespace: str, payload: dict[str, Any], value: dict[str, Any]) -> None:
        """Write a JSON value to cache."""
        key = self._key(namespace, payload)
        if self._redis is None:
            self._memory[key] = (value, self._ttl_seconds)
            return
        await self._redis.setex(key, self._ttl_seconds, json.dumps(value, sort_keys=True, default=str))

    async def close(self) -> None:
        """Close the Redis connection."""
        if self._redis is not None:
            await self._redis.aclose()

    @staticmethod
    def _key(namespace: str, payload: dict[str, Any]) -> str:
        encoded = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        digest = hashlib.sha256(encoded).hexdigest()
        return f"retrieval:{namespace}:{digest}"

