"""Tool registry for registration, lookup, and permission validation."""

from __future__ import annotations

from loguru import logger

from app.agents.contracts.tool import BaseTool, ToolMetadata, ToolResult
from app.agents.execution.policies import run_with_retry, run_with_timeout


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

    def list_for_agent(self, agent_type: str) -> list[ToolMetadata]:
        """Return tools available to a given agent type."""
        return [
            tool.metadata
            for tool in self._tools.values()
            if not tool.metadata.supported_agent_types or agent_type in tool.metadata.supported_agent_types
        ]

    def has_permission(self, tool_name: str, agent_name: str) -> bool:
        """Check whether an agent is permitted to invoke a tool."""
        tool = self._tools.get(tool_name)
        if tool is None:
            return False
        supported = tool.metadata.supported_agent_types
        if not supported:
            return True
        return agent_name in supported

    async def invoke(
        self,
        tool_name: str,
        parameters: dict[str, object],
        agent_name: str,
    ) -> ToolResult:
        """Invoke a tool with retry and timeout policies."""
        tool = self._tools.get(tool_name)
        if tool is None:
            return ToolResult(tool_name=tool_name, success=False, data={}, error_message=f"Tool '{tool_name}' not found")
        if not self.has_permission(tool_name, agent_name):
            return ToolResult(
                tool_name=tool_name,
                success=False,
                data={},
                error_message=f"Agent '{agent_name}' lacks permission for tool '{tool_name}'",
            )

        policy = tool.metadata.retry_policy
        timeout = tool.metadata.timeout_seconds

        async def _execute():
            return await tool.execute(dict(parameters))

        try:
            result, retry_count = await run_with_retry(_execute, policy, tool_name)
            result.retry_count = retry_count
            return result
        except Exception as exc:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                data={},
                error_message=str(exc),
            )

    def count(self) -> int:
        """Return the number of registered tools."""
        return len(self._tools)
