"""Tool interface contracts and ToolRegistry for agent tool execution."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from loguru import logger


@dataclass(frozen=True, slots=True)
class ToolMetadata:
    """Tool specification metadata."""

    name: str
    description: str
    parameters: dict[str, Any]
    permissions: list[str] = field(default_factory=list)
    timeout_seconds: float = 30.0
    max_retries: int = 3
    supported_agent_types: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ToolResult:
    """Output produced by tool execution."""

    tool_name: str
    success: bool
    data: dict[str, Any]
    duration_ms: float = 0.0
    error_message: str | None = None


class BaseTool(ABC):
    """Abstract base class for all tools executable by KrishiOS agents."""

    def __init__(self, metadata: ToolMetadata) -> None:
        self._metadata = metadata

    @property
    def metadata(self) -> ToolMetadata:
        """Return tool metadata."""
        return self._metadata

    @abstractmethod
    async def execute(self, parameters: dict[str, Any]) -> ToolResult:
        """Execute the tool with given arguments."""
        ...


class ToolRegistry:
    """Registry for tool registration, lookup, and permission validation."""

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool instance."""
        name = tool.metadata.name
        self._tools[name] = tool
        logger.info("ToolRegistry: registered tool '{}'", name)

    def get(self, name: str) -> BaseTool | None:
        """Retrieve a registered tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> list[ToolMetadata]:
        """Return metadata for all registered tools."""
        return [tool.metadata for tool in self._tools.values()]
