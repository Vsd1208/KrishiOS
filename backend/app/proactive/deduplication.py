"""Deterministic Event and Notification Deduplication Engine."""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any

from loguru import logger

from app.events.contracts import EventEnvelope


class EventDeduplicator:
    """Computes deterministic fingerprints and prevents duplicate event processing.
    
    Supports:
      1. Event Deduplication: Drops identical external telemetry arriving within cooldown.
      2. Notification Deduplication: Suppresses redundant alerts to the same farmer for the same issue.
    """

    def __init__(self, default_cooldown_seconds: int = 3600, redis_client: Any | None = None) -> None:
        self._default_cooldown = default_cooldown_seconds
        self._redis = redis_client
        self._memory_cache: dict[str, float] = {}

    def compute_event_fingerprint(self, event: EventEnvelope) -> str:
        """Compute a deterministic SHA-256 fingerprint for an event."""
        payload = event.payload or {}
        
        # Normalize key identifiers
        normalized = {
            "event_type": event.event_type,
            "district": str(payload.get("district", "")).strip().lower(),
            "state": str(payload.get("state", "")).strip().lower(),
            "crop": str(payload.get("crop", "")).strip().lower(),
            "commodity": str(payload.get("commodity", "")).strip().lower(),
            "scheme_code": str(payload.get("scheme_code", "")).strip().lower(),
            "severity": str(payload.get("severity", "")).strip().lower(),
            "date": str(payload.get("date", payload.get("forecast_date", ""))),
            # For market price checks, bucket price change into bands (e.g. 5% buckets)
            "change_pct_bucket": round(float(payload.get("change_percent", 0.0)) / 5.0) * 5
            if "change_percent" in payload else None,
        }

        canonical_str = json.dumps(normalized, sort_keys=True, default=str)
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

    def compute_notification_fingerprint(
        self, farmer_id: int, alert_type: str, topic_key: str
    ) -> str:
        """Compute fingerprint for a farmer notification to prevent alert spam."""
        raw = f"farmer:{farmer_id}|type:{alert_type}|topic:{topic_key.lower().strip()}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    async def is_duplicate_event(
        self, event: EventEnvelope, cooldown_seconds: int | None = None
    ) -> bool:
        """Check whether this event is a duplicate within the cooldown window."""
        fingerprint = self.compute_event_fingerprint(event)
        key = f"krishios:dedup:event:{fingerprint}"
        cooldown = cooldown_seconds or self._default_cooldown

        return await self._check_and_set(key, cooldown)

    async def is_duplicate_notification(
        self, farmer_id: int, alert_type: str, topic_key: str, cooldown_seconds: int = 86400
    ) -> bool:
        """Check whether a notification was already sent to this farmer for this issue."""
        fingerprint = self.compute_notification_fingerprint(farmer_id, alert_type, topic_key)
        key = f"krishios:dedup:notif:{fingerprint}"

        return await self._check_and_set(key, cooldown_seconds)

    async def _check_and_set(self, key: str, ttl_seconds: int) -> bool:
        """Atomically test if key exists; if not, set with TTL. Returns True if duplicate."""
        now = time.time()

        # 1. Try Redis if available
        if self._redis is not None:
            try:
                # SET key 1 NX EX ttl -> returns True if set (i.e. new), False/None if already existed
                was_set = await self._redis.set(key, "1", ex=ttl_seconds, nx=True)
                is_duplicate = not bool(was_set)
                if is_duplicate:
                    logger.info("Deduplicator: suppressed duplicate key='{}'", key)
                return is_duplicate
            except Exception as exc:
                logger.warning("Deduplicator: Redis check failed ({}), falling back to memory", exc)

        # 2. In-memory fallback
        # Clean expired entries
        expired_keys = [k for k, expiry in self._memory_cache.items() if expiry <= now]
        for k in expired_keys:
            del self._memory_cache[k]

        if key in self._memory_cache:
            logger.info("Deduplicator: suppressed duplicate in-memory key='{}'", key)
            return True

        self._memory_cache[key] = now + ttl_seconds
        return False

    def clear(self) -> None:
        """Clear memory cache for testing."""
        self._memory_cache.clear()
