"""Tool registry for enterprise agent execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ToolDefinition:
    """Metadata for a tool that can be invoked by agents."""

    name: str
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)
    permissions: list[str] = field(default_factory=list)
    timeout_seconds: int = 30
    retry_policy: dict[str, Any] = field(default_factory=lambda: {"max_retries": 1})
    supported_agents: list[str] = field(default_factory=list)


class ToolRegistry:
    """Store tool metadata and support lookup by tool name."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        """Register a tool definition."""
        self._tools[tool.name] = tool

    def get(self, name: str) -> ToolDefinition | None:
        """Return a tool definition by name."""
        return self._tools.get(name)

    def list(self) -> list[ToolDefinition]:
        """Return all registered tools."""
        return list(self._tools.values())
