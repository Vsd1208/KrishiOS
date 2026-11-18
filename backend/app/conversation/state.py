"""Dialogue state: slots carried across turns, pending clarification, short history.

The state is small JSON. It lives in Redis in deployment (TTL), and in-process for tests and
single-instance development. Turn records for audit and feedback are persisted separately
(``ConversationTurnRecord``).
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Protocol

MAX_HISTORY = 10
STATE_TTL_SECONDS = 24 * 3600


@dataclass(slots=True)
class Pending:
    """A clarification the bot asked and is waiting for."""

    slot: str  # crop | district
    choices: list[dict[str, Any]]  # [{"value": "cabbage", "label": "పత్తి"}]
    original_text: str  # the question to resume once the slot is filled
    original_language: str
    intent: str


@dataclass(slots=True)
class DialogueState:
    conversation_id: str
    user_uuid: str
    language: str  # reply language (the farmer's chosen language)
    acting_for_farmer_id: int | None = None
    crop: str | None = None  # catalog key
    district_lgd_code: int | None = None
    district_name: str | None = None
    state_name: str | None = None
    season: str | None = None
    pending: Pending | None = None
    # Phase 9: the latest photo in this conversation (image path + local vision result),
    # kept across the crop-confirmation chip so the condition can be re-read for that crop.
    photo: dict[str, Any] | None = None
    history: list[dict[str, Any]] = field(default_factory=list)
    updated_at: float = field(default_factory=time.time)

    @classmethod
    def new(cls, user_uuid: str, language: str, acting_for: int | None = None) -> DialogueState:
        return cls(conversation_id=uuid.uuid4().hex, user_uuid=user_uuid, language=language,
                   acting_for_farmer_id=acting_for)

    def remember(self, role: str, text: str, language: str) -> None:
        self.history.append({"role": role, "text": text, "language": language,
                             "at": round(time.time(), 1)})
        del self.history[:-MAX_HISTORY]
        self.updated_at = time.time()

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

    @classmethod
    def from_json(cls, raw: str) -> DialogueState:
        data = json.loads(raw)
        pending = data.pop("pending", None)
        state = cls(**data)
        state.pending = Pending(**pending) if pending else None
        return state


class StateStore(Protocol):
    async def get(self, conversation_id: str) -> DialogueState | None: ...
    async def save(self, state: DialogueState) -> None: ...


class InMemoryStateStore:
    """Process-local store (tests, single-instance dev)."""

    def __init__(self) -> None:
        self._data: dict[str, str] = {}

    async def get(self, conversation_id: str) -> DialogueState | None:
        raw = self._data.get(conversation_id)
        return DialogueState.from_json(raw) if raw else None

    async def save(self, state: DialogueState) -> None:
        self._data[state.conversation_id] = state.to_json()


class RedisStateStore:
    """Redis-backed store with a TTL (multi-instance deployments)."""

    def __init__(self, redis: Any, ttl_seconds: int = STATE_TTL_SECONDS) -> None:
        self._redis = redis
        self._ttl = ttl_seconds

    @staticmethod
    def _key(conversation_id: str) -> str:
        return f"krishios:conversation:{conversation_id}"

    async def get(self, conversation_id: str) -> DialogueState | None:
        raw = await self._redis.get(self._key(conversation_id))
        if raw is None:
            return None
        return DialogueState.from_json(raw.decode() if isinstance(raw, bytes) else raw)

    async def save(self, state: DialogueState) -> None:
        await self._redis.set(self._key(state.conversation_id), state.to_json(), ex=self._ttl)
