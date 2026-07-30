"""Runtime engine for lifecycle management, registration, and execution control."""

from __future__ import annotations

from app.agents.events.bus import EventBus
from app.agents.interfaces import AgentContext, AgentResult
from app.agents.orchestrator.orchestrator import Orchestrator
from app.agents.registry.registry import AgentRegistry
from app.agents.tools.registry import ToolRegistry


class AgentRuntime:
    """Top-level runtime that glues registry, orchestrator, tools, and events together."""

    def __init__(self, registry: AgentRegistry | None = None, tool_registry: ToolRegistry | None = None) -> None:
        self._registry = registry or AgentRegistry()
        self._tool_registry = tool_registry or ToolRegistry()
        self._event_bus = EventBus()
        self._orchestrator = Orchestrator(self._registry, self._event_bus)

    async def execute(self, goal: str, session_id: str | None = None) -> list[AgentResult]:
        """Execute a user goal through the orchestrator."""
        return await self._orchestrator.execute(goal, session_id)

    def registry(self) -> AgentRegistry:
        """Return the runtime's agent registry."""
        return self._registry

    def tools(self) -> ToolRegistry:
        """Return the runtime's tool registry."""
        return self._tool_registry
