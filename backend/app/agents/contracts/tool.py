"""Canonical tool contract for agent-invokable capabilities."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """Retry configuration applied during tool invocation."""

    max_retries: int = 3
    backoff_seconds: float = 0.5
    retryable_errors: tuple[str, ...] = ("timeout", "connection", "rate_limit")


@dataclass(frozen=True, slots=True)
class ToolMetadata:
    """Tool specification metadata registered in the ToolRegistry."""

    name: str
    description: str
    parameters: dict[str, Any]
    permissions: list[str] = field(default_factory=list)
    timeout_seconds: float = 30.0
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    supported_agent_types: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ToolResult:
    """Output produced by tool execution."""

    tool_name: str
    success: bool
    data: dict[str, Any]
    duration_ms: float = 0.0
    error_message: str | None = None
    retry_count: int = 0


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
