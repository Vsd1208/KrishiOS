"""BaseAgent abstract interface for all KrishiOS AI agents.

Re-exports the canonical contract from ``app.agents.contracts`` for backward compatibility.
"""

from app.agents.contracts.agent import AgentHealthReport, AgentMetadata, BaseAgent

__all__ = ["AgentHealthReport", "AgentMetadata", "BaseAgent"]
