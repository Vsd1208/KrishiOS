"""Wiring: state store selection, providers, turn persistence."""

from __future__ import annotations

from functools import lru_cache
from typing import Any
from uuid import UUID

from loguru import logger

from app.config.settings import get_settings
from app.conversation.manager import ConversationManager, TurnInput, TurnResult
from app.conversation.state import DialogueState, InMemoryStateStore, RedisStateStore, StateStore


@lru_cache(maxsize=1)
def get_state_store() -> StateStore:
    settings = get_settings()
    if settings.CONVERSATION_STATE_BACKEND == "redis":
        from redis.asyncio import Redis  # noqa: PLC0415

        return RedisStateStore(Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT,
                                     db=settings.REDIS_DB, password=settings.REDIS_PASSWORD))
    return InMemoryStateStore()


def _tts() -> Any:
    from app.voice.providers.selection import get_tts_provider  # noqa: PLC0415

    try:
        return get_tts_provider()
    except Exception as exc:  # misconfigured TTS must not break text answers
        logger.warning("TTS provider unavailable: {}", exc)
        return None


def build_manager(sink=None) -> ConversationManager:
    return ConversationManager(store=get_state_store(), sink=sink, tts=_tts())


def db_sink(session: Any, channel: str = "text"):
    """Persist every turn as a ``ConversationTurnRecord`` (audit + feedback target)."""
    from app.models.conversation import ConversationTurnRecord  # noqa: PLC0415

    async def sink(state: DialogueState, inp: TurnInput, result: TurnResult) -> None:
        session.add(ConversationTurnRecord(
            turn_uuid=result.turn_id, conversation_id=result.conversation_id,
            user_uuid=UUID(str(inp.user_uuid)), acting_for_farmer_id=inp.acting_for_farmer_id,
            channel=channel, language=result.language,
            detected_language=result.detected_language, user_text=inp.text or "",
            intent=result.intent, status=result.status, reply_text=result.reply_text,
            reply_text_en=result.reply_text_en, slots=result.slots,
            citations=result.citations, providers=result.providers,
            translation_status=result.translation_status,
            requires_review=result.requires_review, review_reason=result.review_reason,
            # Assisted mode: an extension worker reviews AI answers before sharing (F6).
            shared_with_farmer=inp.acting_for_farmer_id is None,
        ))
        await session.commit()

    return sink
