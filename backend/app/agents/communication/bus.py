"""Inter-agent communication channel for decoupled message passing."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class AgentMessage:
    """Message exchanged between agents via the communication bus."""

    sender: str
    recipient: str
    message_type: str
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    correlation_id: str | None = None


class CommunicationBus:
    """In-process mailbox for agent-to-agent communication."""

    def __init__(self, max_queue_size: int = 256) -> None:
        self._mailboxes: dict[str, deque[AgentMessage]] = defaultdict(deque)
        self._max_queue_size = max_queue_size

    def send(self, message: AgentMessage) -> None:
        """Deliver a message to the recipient mailbox."""
        mailbox = self._mailboxes[message.recipient]
        if len(mailbox) >= self._max_queue_size:
            mailbox.popleft()
        mailbox.append(message)

    def receive(self, recipient: str, limit: int = 10) -> list[AgentMessage]:
        """Drain up to ``limit`` messages for a recipient."""
        mailbox = self._mailboxes[recipient]
        messages: list[AgentMessage] = []
        while mailbox and len(messages) < limit:
            messages.append(mailbox.popleft())
        return messages

    def pending_count(self, recipient: str) -> int:
        """Return the number of pending messages for a recipient."""
        return len(self._mailboxes[recipient])
