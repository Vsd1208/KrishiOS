"""Communication package for inter-agent messaging."""

from app.agents.communication.bus import AgentMessage, CommunicationBus

__all__ = ["AgentMessage", "CommunicationBus"]
