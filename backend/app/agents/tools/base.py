"""Tool interface contracts and ToolRegistry for agent tool execution.

Re-exports the canonical contract from ``app.agents.contracts`` for backward compatibility.
"""

from app.agents.contracts.tool import BaseTool, RetryPolicy, ToolMetadata, ToolResult

__all__ = ["BaseTool", "RetryPolicy", "ToolMetadata", "ToolResult"]
