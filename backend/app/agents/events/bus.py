"""Internal event system for agent lifecycle and tool coordination."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any

from app.agents.contracts.events import AgentEvent, EventTypes

EventHandler = Callable[[AgentEvent], Awaitable[None]]


class EventBus:
    """In-process publish/subscribe event bus for decoupled agent communication."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)
        self._history: list[AgentEvent] = []
        self._max_history = 500

    async def publish(self, event: AgentEvent) -> None:
        """Publish an event to all registered handlers."""
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history :]

        for handler in list(self._handlers.get(event.event_type, [])):
            await handler(event)
        for handler in list(self._handlers.get("*", [])):
            await handler(event)

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Register a handler for an event type. Use ``*`` for all events."""
        self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """Remove a handler from an event type."""
        if event_type in self._handlers:
            self._handlers[event_type] = [h for h in self._handlers[event_type] if h is not handler]

    def history(self, event_type: str | None = None, limit: int = 50) -> list[AgentEvent]:
        """Return recent event history, optionally filtered by type."""
        events = self._history if event_type is None else [e for e in self._history if e.event_type == event_type]
        return events[-limit:]


__all__ = ["AgentEvent", "EventBus", "EventHandler", "EventTypes"]
