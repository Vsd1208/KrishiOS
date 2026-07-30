"""Execution policies for retry, timeout, and failure recovery."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from time import perf_counter
from typing import Any, TypeVar

from loguru import logger

from app.agents.contracts.tool import RetryPolicy

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class TimeoutPolicy:
    """Timeout configuration for agent and tool execution."""

    agent_timeout_seconds: float = 120.0
    tool_timeout_seconds: float = 30.0
    planning_timeout_seconds: float = 15.0


@dataclass(frozen=True, slots=True)
class ExecutionPolicy:
    """Combined execution policy applied by the runtime engine."""

    retry: RetryPolicy
    timeout: TimeoutPolicy


DEFAULT_EXECUTION_POLICY = ExecutionPolicy(
    retry=RetryPolicy(max_retries=3, backoff_seconds=0.5),
    timeout=TimeoutPolicy(),
)


async def run_with_retry(
    operation: Callable[[], Awaitable[T]],
    policy: RetryPolicy,
    operation_name: str,
) -> tuple[T, int]:
    """Execute an async operation with exponential backoff retry."""
    attempt = 0
    last_error: Exception | None = None

    while attempt <= policy.max_retries:
        try:
            result = await operation()
            return result, attempt
        except Exception as exc:
            last_error = exc
            attempt += 1
            if attempt > policy.max_retries:
                break
            if not _is_retryable(str(exc), policy.retryable_errors):
                break
            delay = policy.backoff_seconds * attempt
            logger.warning(
                "{} failed (attempt {}/{}): {} — retrying in {:.1f}s",
                operation_name,
                attempt,
                policy.max_retries,
                exc,
                delay,
            )
            await asyncio.sleep(delay)

    raise RuntimeError(f"{operation_name} failed after {attempt} attempts: {last_error}") from last_error


async def run_with_timeout(
    operation: Callable[[], Awaitable[T]],
    timeout_seconds: float,
    operation_name: str,
) -> T:
    """Execute an async operation with a hard timeout."""
    try:
        return await asyncio.wait_for(operation(), timeout=timeout_seconds)
    except TimeoutError as exc:
        raise TimeoutError(f"{operation_name} timed out after {timeout_seconds}s") from exc


def _is_retryable(error_message: str, retryable_errors: tuple[str, ...]) -> bool:
    """Return True when the error message matches a retryable category."""
    lowered = error_message.casefold()
    return any(token in lowered for token in retryable_errors)


class ExecutionTimer:
    """Lightweight timer for recording execution latency."""

    def __init__(self) -> None:
        self._started = perf_counter()

    def elapsed_ms(self) -> float:
        """Return elapsed milliseconds since timer creation."""
        return (perf_counter() - self._started) * 1000
