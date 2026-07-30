"""Backward-compatible interface re-exports for legacy imports."""

from app.agents.contracts.agent import AgentMetadata
from app.agents.execution.context import ExecutionContext as AgentContext
from app.agents.execution.context import ExecutionResult as AgentResult

__all__ = ["AgentContext", "AgentMetadata", "AgentResult"]
