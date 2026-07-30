"""Memory provider interfaces for working, session, and future long-term memory."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Protocol, runtime_checkable

from app.agents.memory.working import SessionMemory, WorkingMemory


@runtime_checkable
class MemoryProvider(Protocol):
    """Protocol for replaceable memory backends."""

    async def get_working(self, scope_id: str) -> WorkingMemory:
        """Return working memory for the given scope."""

    async def clear_working(self, scope_id: str) -> None:
        """Clear working memory for the given scope."""

    async def get_session(self, session_id: str) -> WorkingMemory:
        """Return session-scoped memory."""

    async def clear_session(self, session_id: str) -> None:
        """Clear session-scoped memory."""


class InMemoryProvider:
    """Default in-process memory provider backed by SessionMemory."""

    def __init__(self) -> None:
        self._working: dict[str, WorkingMemory] = {}
        self._sessions = SessionMemory()

    async def get_working(self, scope_id: str) -> WorkingMemory:
        """Return or create working memory for a scope."""
        if scope_id not in self._working:
            self._working[scope_id] = WorkingMemory()
        return self._working[scope_id]

    async def clear_working(self, scope_id: str) -> None:
        """Clear working memory for a scope."""
        if scope_id in self._working:
            self._working[scope_id].clear()

    async def get_session(self, session_id: str) -> WorkingMemory:
        """Return session memory."""
        return self._sessions.get_session(session_id)

    async def clear_session(self, session_id: str) -> None:
        """Clear session memory."""
        self._sessions.clear_session(session_id)


class LongTermMemoryStore(ABC):
    """Abstract interface for future persistent long-term memory implementations."""

    @abstractmethod
    async def store(self, key: str, value: dict[str, Any], user_id: str) -> None:
        """Persist a memory entry."""

    @abstractmethod
    async def recall(self, query: str, user_id: str, limit: int = 5) -> list[dict[str, Any]]:
        """Recall relevant long-term memories for a query."""
