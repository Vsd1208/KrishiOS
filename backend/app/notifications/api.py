"""Web Push subscription API (Phase 5)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import AuthContext, RequirePermission
from app.auth.permissions import Permission
from app.config.settings import get_settings
from app.database.session import get_db_session
from app.govconnect.api import current_farmer_id
from app.models.govconnect import PushSubscription

router = APIRouter(prefix="/notifications/push", tags=["Push notifications"])
DbSession = Annotated[AsyncSession, Depends(get_db_session)]
Reader = Annotated[AuthContext, Depends(RequirePermission(Permission.GOVCONNECT_READ))]


class Keys(BaseModel):
    p256dh: str = Field(min_length=10, max_length=255)
    auth: str = Field(min_length=4, max_length=255)


class SubscriptionIn(BaseModel):
    endpoint: str = Field(pattern=r"^https://", max_length=2000)
    keys: Keys


@router.get("/config")
async def push_config() -> dict:
    """The VAPID public key for the browser (null = push not configured, sandbox only)."""
    s = get_settings()
    return {
        "public_key": s.VAPID_PUBLIC_KEY,
        "enabled": bool(s.VAPID_PUBLIC_KEY and s.VAPID_PRIVATE_KEY and s.VAPID_SUBJECT),
    }


@router.post("/subscriptions", status_code=status.HTTP_201_CREATED)
async def subscribe(body: SubscriptionIn, session: DbSession, auth: Reader) -> dict:
    farmer_id = await current_farmer_id(session, auth)
    sub = await session.scalar(
        select(PushSubscription).where(PushSubscription.endpoint == body.endpoint)
    )
    if sub is None:
        sub = PushSubscription(
            farmer_id=farmer_id,
            endpoint=body.endpoint,
            p256dh=body.keys.p256dh,
            auth=body.keys.auth,
        )
        session.add(sub)
    else:  # the same browser re-subscribing (possibly another farmer logging in)
        sub.farmer_id, sub.p256dh, sub.auth, sub.failures = (
            farmer_id,
            body.keys.p256dh,
            body.keys.auth,
            0,
        )
    await session.commit()
    return {"subscribed": True}


class UnsubscribeIn(BaseModel):
    endpoint: str = Field(max_length=2000)


@router.post("/subscriptions/remove")
async def unsubscribe(body: UnsubscribeIn, session: DbSession, auth: Reader) -> dict:
    farmer_id = await current_farmer_id(session, auth)
    await session.execute(
        delete(PushSubscription).where(
            PushSubscription.endpoint == body.endpoint, PushSubscription.farmer_id == farmer_id
        )
    )
    await session.commit()
    return {"subscribed": False}
