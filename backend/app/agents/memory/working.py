"""WorkingMemory and SessionMemory implementations for transient state management."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class WorkingMemory:
    """Transient key-value store for an agent during task execution."""

    data: dict[str, Any] = field(default_factory=dict)

    def set(self, key: str, value: Any) -> None:
        """Set a value in working memory."""
        self.data[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from working memory."""
        return self.data.get(key, default)

    def clear(self) -> None:
        """Clear transient working memory."""
        self.data.clear()


class SessionMemory:
    """In-memory session context for multi-turn conversations or steps."""

    def __init__(self) -> None:
        self._sessions: dict[str, WorkingMemory] = {}

    def get_session(self, session_id: str) -> WorkingMemory:
        """Retrieve or create session working memory."""
        if session_id not in self._sessions:
            self._sessions[session_id] = WorkingMemory()
        return self._sessions[session_id]

    def clear_session(self, session_id: str) -> None:
        """Clear session memory."""
        if session_id in self._sessions:
            del self._sessions[session_id]
