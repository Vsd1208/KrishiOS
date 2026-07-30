"""Core interfaces for the enterprise agent runtime."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(slots=True)
class AgentMetadata:
    """Registration metadata for a runtime agent."""

    name: str
    description: str
    capabilities: list[str] = field(default_factory=list)
    input_schema: dict[str, Any] | None = None
    output_schema: dict[str, Any] | None = None
    supported_tools: list[str] = field(default_factory=list)
    priority: int = 0
    version: str = "1.0"
    health_status: str = "healthy"


@dataclass(slots=True)
class AgentContext:
    """Runtime context propagated to agents and tools."""

    task_id: str
    user_goal: str
    session_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AgentResult:
    """Structured result emitted by an agent."""

    agent_name: str
    status: str
    output: dict[str, Any]
    confidence: float = 0.0
    citations: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None


class BaseAgent(Protocol):
    """Base interface that every agent must implement."""

    async def initialize(self, context: AgentContext) -> None:
        """Prepare the agent for execution."""

    async def execute(self, context: AgentContext) -> AgentResult:
        """Execute the agent against the supplied context."""

    async def validate(self, result: AgentResult) -> bool:
        """Validate the agent result before it is surfaced."""

    async def cleanup(self, context: AgentContext) -> None:
        """Release runtime resources used by the agent."""

    async def health(self) -> str:
        """Return the runtime health status of the agent."""

    def metadata(self) -> AgentMetadata:
        """Return agent registration metadata."""
