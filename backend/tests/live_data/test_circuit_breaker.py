"""Tests for Circuit Breaker pattern."""

import asyncio
import pytest
from app.live_data.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpenError,
    CircuitState,
)


@pytest.mark.asyncio
async def test_circuit_breaker_closed_state_success():
    cb = CircuitBreaker(name="test_cb", failure_threshold=3, recovery_time_seconds=0.5)

    async def _success_op():
        return "success"

    res = await cb.call(_success_op)
    assert res == "success"
    assert cb.state == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_circuit_breaker_transitions_to_open_after_threshold():
    cb = CircuitBreaker(name="test_cb", failure_threshold=2, recovery_time_seconds=0.5)

    async def _failing_op():
        raise ConnectionError("Service unreachable")

    # Failure 1
    with pytest.raises(ConnectionError):
        await cb.call(_failing_op)
    assert cb.state == CircuitState.CLOSED

    # Failure 2 -> triggers OPEN state
    with pytest.raises(ConnectionError):
        await cb.call(_failing_op)
    assert cb.state == CircuitState.OPEN

    # Next call fails fast with CircuitBreakerOpenError
    with pytest.raises(CircuitBreakerOpenError):
        await cb.call(_failing_op)


@pytest.mark.asyncio
async def test_circuit_breaker_recovery_to_half_open_and_closed():
    cb = CircuitBreaker(name="test_cb", failure_threshold=2, recovery_time_seconds=0.2)

    async def _failing_op():
        raise ConnectionError("Boom")

    async def _success_op():
        return "recovered"

    # Trip breaker to OPEN
    for _ in range(2):
        with pytest.raises(ConnectionError):
            await cb.call(_failing_op)
    assert cb.state == CircuitState.OPEN

    # Wait for cooldown
    await asyncio.sleep(0.25)
    assert cb.state == CircuitState.HALF_OPEN

    # Probe call succeeds -> transitions back to CLOSED
    res = await cb.call(_success_op)
    assert res == "recovered"
    assert cb.state == CircuitState.CLOSED
