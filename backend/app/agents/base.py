"""BaseAgent abstract interface for all KrishiOS AI agents.

No business logic inside runtime; all agents adhere strictly to this contract.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.agents.execution.context import AgentStatus, ExecutionContext, ExecutionResult


@dataclass(frozen=True, slots=True)
class AgentMetadata:
    """Agent declaration metadata registered in AgentRegistry."""

    name: str
    description: str
    capabilities: list[str]
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    supported_tools: list[str]
    priority: int = 100
    version: str = "1.0.0"


class BaseAgent(ABC):
    """Abstract contract that every KrishiOS agent must implement."""

    def __init__(self, metadata: AgentMetadata) -> None:
        self._metadata = metadata
        self._status: AgentStatus = AgentStatus.IDLE

    @property
    def metadata(self) -> AgentMetadata:
        """Return declared agent metadata."""
        return self._metadata

    @property
    def status(self) -> AgentStatus:
        """Return current lifecycle status."""
        return self._status

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize agent resources or connections."""
        ...

    @abstractmethod
    async def execute(
        self,
        task: str,
        context: ExecutionContext,
        parameters: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        """Execute the agent task within the given context."""
        ...

    @abstractmethod
    async def validate(self, result: ExecutionResult) -> bool:
        """Validate agent output quality, schema, and grounding."""
        ...

    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up transient state or active locks."""
        ...

    @abstractmethod
    async def health(self) -> dict[str, Any]:
        """Return current health status and diagnostic checks."""
        ...
