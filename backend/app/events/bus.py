"""Asynchronous Event Bus for decoupled event publication and subscription."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any

from loguru import logger

from app.events.contracts import EventEnvelope

AsyncEventHandler = Callable[[EventEnvelope], Awaitable[None]]


class AsyncEventBus:
    """Production asynchronous in-process event bus with error isolation and wildcard routing."""

    def __init__(self, max_history: int = 1000) -> None:
        self._handlers: dict[str, list[AsyncEventHandler]] = defaultdict(list)
        self._history: list[EventEnvelope] = []
        self._max_history = max_history
        self._lock = asyncio.Lock()

    async def publish(self, event: EventEnvelope) -> None:
        """Publish an event envelope to all subscribed handlers.
        
        Executes handlers concurrently with exception isolation so one failing
        subscriber does not crash other subscribers or the publisher.
        """
        async with self._lock:
            self._history.append(event)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history :]

        event_type = str(event.event_type)
        handlers: list[AsyncEventHandler] = list(self._handlers.get(event_type, []))

        # Support wildcard patterns e.g. "weather.*" or "*"
        for pattern, subscribers in self._handlers.items():
            if pattern == "*":
                handlers.extend(subscribers)
            elif pattern.endswith(".*"):
                prefix = pattern[:-2]
                if event_type.startswith(prefix):
                    handlers.extend(subscribers)

        if not handlers:
            logger.debug("AsyncEventBus: no handlers registered for event_type='{}'", event_type)
            return

        # Deduplicate handlers while preserving order
        unique_handlers = list(dict.fromkeys(handlers))

        async def _safe_execute(handler: AsyncEventHandler) -> None:
            try:
                await handler(event)
            except Exception as exc:
                logger.exception(
                    "AsyncEventBus: subscriber error handling event_id={} type='{}': {}",
                    event.event_id,
                    event.event_type,
                    exc,
                )

        await asyncio.gather(*[_safe_execute(h) for h in unique_handlers])

    def subscribe(self, event_type: str, handler: AsyncEventHandler) -> None:
        """Subscribe a callable handler to an event type or pattern."""
        if handler not in self._handlers[event_type]:
            self._handlers[event_type].append(handler)
            logger.debug("AsyncEventBus: subscribed handler to '{}'", event_type)

    def unsubscribe(self, event_type: str, handler: AsyncEventHandler) -> None:
        """Unsubscribe a handler from an event type."""
        if event_type in self._handlers:
            self._handlers[event_type] = [h for h in self._handlers[event_type] if h is not handler]

    def history(self, event_type: str | None = None, limit: int = 50) -> list[EventEnvelope]:
        """Retrieve recent published events."""
        if event_type is None:
            return self._history[-limit:]
        return [e for e in self._history if e.event_type == event_type][-limit:]

    def clear(self) -> None:
        """Clear all subscriptions and history (useful for test suites)."""
        self._handlers.clear()
        self._history.clear()


# Global singleton instance
_GLOBAL_EVENT_BUS: AsyncEventBus | None = None


def get_event_bus() -> AsyncEventBus:
    """Return process-wide singleton event bus."""
    global _GLOBAL_EVENT_BUS
    if _GLOBAL_EVENT_BUS is None:
        _GLOBAL_EVENT_BUS = AsyncEventBus()
    return _GLOBAL_EVENT_BUS
