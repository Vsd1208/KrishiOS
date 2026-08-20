"""Circuit Breaker implementation protecting against failing downstream external providers."""

import asyncio
from datetime import UTC, datetime
from enum import Enum
from time import perf_counter
from typing import Any, Awaitable, Callable, TypeVar

from loguru import logger

T = TypeVar("T")


class CircuitState(str, Enum):
    CLOSED = "CLOSED"      # Normal operation
    OPEN = "OPEN"          # Failing: reject requests immediately
    HALF_OPEN = "HALF_OPEN"  # Testing single canary request


class CircuitBreakerOpenError(Exception):
    """Raised when request is rejected because the circuit breaker is OPEN."""

    def __init__(self, name: str, retry_after_seconds: float) -> None:
        super().__init__(f"Circuit breaker '{name}' is OPEN. Retry after {retry_after_seconds:.1f}s")
        self.name = name
        self.retry_after_seconds = retry_after_seconds


class CircuitBreaker:
    """Three-state circuit breaker with configurable failure thresholds and recovery cooldown."""

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_time_seconds: float = 30.0,
        half_open_success_threshold: int = 1,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_time_seconds = recovery_time_seconds
        self.half_open_success_threshold = half_open_success_threshold

        self._state: CircuitState = CircuitState.CLOSED
        self._consecutive_failures: int = 0
        self._consecutive_successes: int = 0
        self._last_failure_time: float = 0.0
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        """Current circuit state, auto-transitioning from OPEN to HALF_OPEN when recovery time elapses."""
        if self._state == CircuitState.OPEN:
            elapsed = perf_counter() - self._last_failure_time
            if elapsed >= self.recovery_time_seconds:
                self._state = CircuitState.HALF_OPEN
                logger.info("CircuitBreaker '{}': transitioned to HALF_OPEN (probe request allowed)", self.name)
        return self._state

    async def call(self, func: Callable[..., Awaitable[T]], *args: Any, **kwargs: Any) -> T:
        """Execute async function guarded by circuit breaker state."""
        async with self._lock:
            current_state = self.state
            if current_state == CircuitState.OPEN:
                remaining = max(0.0, self.recovery_time_seconds - (perf_counter() - self._last_failure_time))
                raise CircuitBreakerOpenError(self.name, remaining)

        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except Exception as exc:
            await self._on_failure(exc)
            raise

    async def _on_success(self) -> None:
        async with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._consecutive_successes += 1
                if self._consecutive_successes >= self.half_open_success_threshold:
                    self._state = CircuitState.CLOSED
                    self._consecutive_failures = 0
                    self._consecutive_successes = 0
                    logger.info("CircuitBreaker '{}': probe succeeded, reset to CLOSED", self.name)
            elif self._state == CircuitState.CLOSED:
                self._consecutive_failures = 0

    async def _on_failure(self, exc: Exception) -> None:
        async with self._lock:
            self._last_failure_time = perf_counter()
            self._consecutive_failures += 1
            logger.warning(
                "CircuitBreaker '{}': call failed ({}: {}), failure count={}/{}",
                self.name,
                type(exc).__name__,
                exc,
                self._consecutive_failures,
                self.failure_threshold,
            )
            if self._state in (CircuitState.CLOSED, CircuitState.HALF_OPEN):
                if self._consecutive_failures >= self.failure_threshold or self._state == CircuitState.HALF_OPEN:
                    self._state = CircuitState.OPEN
                    logger.error(
                        "CircuitBreaker '{}': threshold reached, OPENING circuit for {:.1f}s",
                        self.name,
                        self.recovery_time_seconds,
                    )

    def reset(self) -> None:
        """Force reset to CLOSED state."""
        self._state = CircuitState.CLOSED
        self._consecutive_failures = 0
        self._consecutive_successes = 0
        self._last_failure_time = 0.0
