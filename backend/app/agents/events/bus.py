"""Internal event bus for agent lifecycle and tool coordination."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable


@dataclass(slots=True)
class AgentEvent:
    """Event emitted during agent execution or tool handling."""

    event_type: str
    payload: dict[str, Any] = field(default_factory=dict)


EventHandler = Callable[[AgentEvent], Awaitable[None]]


class EventBus:
    """Simple in-process event bus for agent communication."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)

    async def publish(self, event: AgentEvent) -> None:
        """Publish an event to all registered handlers."""
        for handler in list(self._handlers.get(event.event_type, [])):
            await handler(event)

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Register a handler for an event type."""
        self._handlers[event_type].append(handler)
