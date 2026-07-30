"""Registry for agent discovery and runtime registration."""

from __future__ import annotations

from app.agents.interfaces import AgentMetadata, BaseAgent


class AgentRegistry:
    """Maintain registered agents and provide lookup utilities."""

    def __init__(self) -> None:
        self._agents: dict[str, tuple[BaseAgent, AgentMetadata]] = {}

    def register(self, agent: BaseAgent, metadata: AgentMetadata) -> None:
        """Register an agent implementation with metadata."""
        self._agents[metadata.name] = (agent, metadata)

    def get(self, name: str) -> tuple[BaseAgent, AgentMetadata] | None:
        """Return a registered agent and metadata by name."""
        return self._agents.get(name)

    def list(self) -> list[tuple[BaseAgent, AgentMetadata]]:
        """Return all registered agents."""
        return list(self._agents.values())

    def names(self) -> list[str]:
        """Return the registered agent names."""
        return sorted(self._agents)
