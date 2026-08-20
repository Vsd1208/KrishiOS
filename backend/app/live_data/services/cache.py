"""Redis-backed Cache Service for Live Agricultural Data."""

import hashlib
import json
from time import perf_counter
from typing import Any
from loguru import logger

from app.config.settings import get_settings

try:
    from redis.asyncio import Redis
except ImportError:  # pragma: no cover
    Redis = None  # type: ignore[assignment]


class LiveDataCacheService:
    """Provides namespaced caching with domain-specific TTLs and automatic memory fallback."""

    def __init__(self, redis_url: str | None = None) -> None:
        settings = get_settings()
        url = redis_url or str(settings.redis_url)
        self._redis = Redis.from_url(url, decode_responses=True) if Redis is not None else None
        self._memory: dict[str, tuple[dict[str, Any], float]] = {}  # key -> (value, expiry_timestamp)

    def _generate_key(self, namespace: str, params: dict[str, Any]) -> str:
        """Create deterministic key from namespace and sorted parameter payload."""
        encoded = json.dumps(params, sort_keys=True, default=str).encode("utf-8")
        digest = hashlib.sha256(encoded).hexdigest()[:16]
        return f"live_data:{namespace}:{digest}"

    async def get(self, namespace: str, params: dict[str, Any]) -> dict[str, Any] | None:
        """Retrieve cached JSON payload if present and not expired."""
        key = self._generate_key(namespace, params)
        if self._redis is None:
            entry = self._memory.get(key)
            if entry is None:
                return None
            val, expiry = entry
            if perf_counter() > expiry:
                self._memory.pop(key, None)
                return None
            return val

        try:
            raw = await self._redis.get(key)
            if raw is None:
                return None
            return json.loads(raw)
        except Exception as exc:
            logger.warning("LiveDataCacheService: Redis read failed ({}), falling back to memory", exc)
            self._redis = None
            entry = self._memory.get(key)
            if entry and perf_counter() <= entry[1]:
                return entry[0]
            return None

    async def set(
        self,
        namespace: str,
        params: dict[str, Any],
        value: dict[str, Any],
        ttl_seconds: int,
    ) -> None:
        """Store JSON payload with TTL."""
        key = self._generate_key(namespace, params)
        self._memory[key] = (value, perf_counter() + ttl_seconds)

        if self._redis is not None:
            try:
                await self._redis.set(
                    key,
                    json.dumps(value, sort_keys=True, default=str),
                    ex=ttl_seconds,
                )
            except Exception as exc:
                logger.warning("LiveDataCacheService: Redis write failed ({})", exc)
                self._redis = None

    async def invalidate(self, namespace: str, params: dict[str, Any]) -> None:
        """Explicitly evict key from cache."""
        key = self._generate_key(namespace, params)
        self._memory.pop(key, None)
        if self._redis is not None:
            try:
                await self._redis.delete(key)
            except Exception:
                pass

    async def close(self) -> None:
        if self._redis is not None:
            await self._redis.aclose()
