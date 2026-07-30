"""Registry for agent discovery, registration, and health tracking."""

from __future__ import annotations

from loguru import logger

from app.agents.contracts.agent import AgentMetadata, BaseAgent


class AgentRegistry:
    """Maintain registered agents and provide lookup, discovery, and health utilities."""

    def __init__(self) -> None:
        self._agents: dict[str, BaseAgent] = {}

    def register(self, agent: BaseAgent) -> None:
        """Register an agent implementation using its declared metadata."""
        metadata = agent.metadata
        self._agents[metadata.name] = agent
        logger.info("AgentRegistry: registered agent '{}' v{}", metadata.name, metadata.version)

    def get(self, name: str) -> BaseAgent | None:
        """Return a registered agent by name."""
        return self._agents.get(name)

    def get_metadata(self, name: str) -> AgentMetadata | None:
        """Return metadata for a registered agent."""
        agent = self._agents.get(name)
        return agent.metadata if agent else None

    def list_agents(self) -> list[BaseAgent]:
        """Return all registered agents sorted by priority (descending)."""
        return sorted(self._agents.values(), key=lambda a: a.metadata.priority, reverse=True)

    def list_metadata(self) -> list[AgentMetadata]:
        """Return metadata for all registered agents."""
        return [agent.metadata for agent in self.list_agents()]

    def names(self) -> list[str]:
        """Return registered agent names."""
        return sorted(self._agents)

    def discover_by_capability(self, capability: str) -> list[BaseAgent]:
        """Find agents that declare a given capability."""
        return [
            agent
            for agent in self.list_agents()
            if capability in agent.metadata.capabilities
        ]

    def discover_by_tool(self, tool_name: str) -> list[BaseAgent]:
        """Find agents that support a given tool."""
        return [
            agent
            for agent in self.list_agents()
            if tool_name in agent.metadata.supported_tools
        ]

    async def health_check_all(self) -> dict[str, dict[str, object]]:
        """Run health checks on all registered agents."""
        results: dict[str, dict[str, object]] = {}
        for name, agent in self._agents.items():
            try:
                results[name] = await agent.health()
            except Exception as exc:
                results[name] = {"status": "unhealthy", "error": str(exc)}
        return results

    def count(self) -> int:
        """Return the number of registered agents."""
        return len(self._agents)
