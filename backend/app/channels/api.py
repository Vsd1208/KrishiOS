"""Channel API (F5). Sandbox webhooks for inbound SMS / IVR and the sandbox outbox.

Real provider callbacks need the provider's signature check and are added with the provider.
Until then the inbound endpoints are officer-only test harnesses (they simulate a farmer's
phone), so they cannot be used to impersonate farmers from outside.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import AuthContext, RequirePermission
from app.auth.permissions import Permission
from app.channels import inbound
from app.channels.providers import mask, sms_selector, voice_selector, whatsapp_selector
from app.config.settings import get_settings
from app.database.session import get_db_session

router = APIRouter(prefix="/channels", tags=["Channels (F5)"])
DbSession = Annotated[AsyncSession, Depends(get_db_session)]
Tester = Annotated[AuthContext, Depends(RequirePermission(Permission.GOVCONNECT_PUBLISH))]


class SmsIn(BaseModel):
    from_phone: str = Field(min_length=10, max_length=15)
    text: str = Field(min_length=1, max_length=1000)


class IvrIn(BaseModel):
    from_phone: str = Field(min_length=10, max_length=15)
    digits: str | None = Field(default=None, max_length=4)


async def _ask(session: AsyncSession, farmer: Any, text: str, lang: str) -> str | None:
    """Answer a free-text SMS question through the bot, as the farmer's own account."""
    from app.auth.permissions import ROLE_PERMISSIONS  # noqa: PLC0415
    from app.conversation.manager import TurnInput  # noqa: PLC0415
    from app.conversation.service import build_manager, db_sink  # noqa: PLC0415
    from app.models.user import User, UserRole  # noqa: PLC0415

    user = await session.scalar(select(User).where(User.farmer_profile_id == farmer.id))
    if user is None:
        return None
    import uuid  # noqa: PLC0415

    auth = AuthContext(
        user_uuid=user.uuid,
        role=UserRole.FARMER,
        permissions=ROLE_PERMISSIONS[UserRole.FARMER],
        jti=uuid.uuid4(),
    )
    result = await build_manager(sink=db_sink(session, channel="sms")).handle(
        TurnInput(user_uuid=str(user.uuid), text=text, language=lang, auth=auth)
    )
    return result.reply_text


@router.post("/sms/inbound")
async def sms_inbound(body: SmsIn, session: DbSession, auth: Tester) -> dict:
    reply, action = await inbound.handle_sms(
        session, body.from_phone, body.text, ask=lambda f, text, lang: _ask(session, f, text, lang)
    )
    await session.commit()
    return {
        "from": mask(inbound.normalize_phone(body.from_phone)),
        "action": action,
        "reply": {
            "text": reply.text,
            "encoding": reply.encoding,
            "segments": reply.segments,
            "truncated": reply.truncated,
        },
    }


@router.post("/ivr/inbound")
async def ivr_inbound(body: IvrIn, session: DbSession, auth: Tester) -> dict:
    script = await inbound.handle_ivr(session, body.from_phone, body.digits)
    await session.commit()
    return script


@router.get("/sandbox/outbox")
async def outbox(auth: Tester, channel: str | None = None, limit: int = 50) -> list[dict]:
    """What the sandbox adapters would have sent (pseudonymised recipients)."""
    s = get_settings()
    items: list[dict] = []
    for name, selector, setting in (
        ("SMS", sms_selector, s.SMS_PROVIDER),
        ("VOICE", voice_selector, s.VOICE_PROVIDER),
        ("WHATSAPP", whatsapp_selector, s.WHATSAPP_PROVIDER),
    ):
        if channel and channel.upper() != name:
            continue
        provider = selector.get(setting)
        items.extend(getattr(provider, "outbox", []))
    return sorted(items, key=lambda m: m["at"], reverse=True)[: min(limit, 500)]
