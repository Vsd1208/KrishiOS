"""Token-bucket rate limiter for protecting external API quotas."""

import asyncio
from time import perf_counter


class TokenBucketRateLimiter:
    """In-memory token bucket rate limiter per provider/domain."""

    def __init__(self, rate_per_minute: int = 60, capacity: int | None = None) -> None:
        self.rate_per_second = rate_per_minute / 60.0
        self.capacity = capacity or rate_per_minute
        self.tokens = float(self.capacity)
        self.last_update = perf_counter()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: int = 1) -> bool:
        """Attempt to acquire tokens immediately. Returns True if acquired, False otherwise."""
        async with self._lock:
            now = perf_counter()
            elapsed = now - self.last_update
            self.last_update = now
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate_per_second)

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

    async def wait_and_acquire(self, tokens: int = 1, timeout: float = 5.0) -> bool:
        """Wait until tokens are available or timeout is reached."""
        t0 = perf_counter()
        while perf_counter() - t0 < timeout:
            if await self.acquire(tokens):
                return True
            await asyncio.sleep(0.05)
        return False
