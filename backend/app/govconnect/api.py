"""Govt–Farmer Connect API (Phase 4): officer publishing console and farmer Govt Updates inbox."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, Literal
from uuid import UUID, uuid4

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import AuthContext, RequirePermission
from app.auth.permissions import Permission
from app.config.settings import get_settings
from app.database.session import get_db_session
from app.govconnect import service as svc
from app.govconnect.indexing import get_indexer
from app.models.conversation import ConversationTurnRecord
from app.models.govconnect import (
    BulletinDelivery,
    BulletinTranslation,
    GovConnectAudit,
    GovtBulletin,
)
from app.models.user import User

router = APIRouter(prefix="/govconnect", tags=["Govt Connect"])
DbSession = Annotated[AsyncSession, Depends(get_db_session)]
Officer = Annotated[AuthContext, Depends(RequirePermission(Permission.GOVCONNECT_PUBLISH))]
Reader = Annotated[AuthContext, Depends(RequirePermission(Permission.GOVCONNECT_READ))]
MAX_UPLOAD_BYTES = 20 * 1024 * 1024
FLAG_REASONS = ("not_applicable", "unclear", "wrong_location", "other")


def get_notifier() -> Any:
    from app.notifications.service import NotificationService  # noqa: PLC0415

    return NotificationService()


def get_translator() -> Any:
    from app.translation.service import get_translation_service  # noqa: PLC0415

    return get_translation_service()


Notifier = Annotated[Any, Depends(get_notifier)]
Translator = Annotated[Any, Depends(get_translator)]


def _raise(exc: svc.GovConnectError) -> None:
    raise HTTPException(exc.status_code, {"message": exc.message, "reasons": exc.reasons}) from exc


async def _bulletin(session: AsyncSession, uuid: UUID) -> GovtBulletin:
    b = await session.scalar(select(GovtBulletin).where(GovtBulletin.uuid == uuid))
    if b is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Bulletin not found")
    return b


def _iso(v: datetime | None) -> str | None:
    return v.isoformat() if v else None


def _summary(b: GovtBulletin) -> dict[str, Any]:
    return {
        "uuid": str(b.uuid),
        "status": b.status,
        "title": b.title,
        "authority": b.authority,
        "authority_level": b.authority_level,
        "severity": b.severity,
        "hazard_type": b.hazard_type,
        "original_language": b.original_language,
        "issued_at": _iso(b.issued_at),
        "valid_from": _iso(b.valid_from),
        "valid_to": _iso(b.valid_to),
        "district_codes": b.district_codes,
        "block_codes": b.block_codes,
        "crops": b.crops,
        "source_type": b.source_type,
        "publish_at": _iso(b.publish_at),
        "published_at": _iso(b.published_at),
        "index_state": b.index_state,
        "created_at": _iso(b.created_at),
    }


def _translation_out(t: BulletinTranslation) -> dict[str, Any]:
    return {
        "language": t.language,
        "title": t.title,
        "body": t.body,
        "status": t.status,
        "provider": t.provider,
        "check_issues": t.check_issues,
        "back_translation": t.back_translation,
        "approved_at": _iso(t.approved_at),
    }


async def _detail(session: AsyncSession, b: GovtBulletin) -> dict[str, Any]:
    translations = await svc.translations_of(session, b)
    supersedes = await session.get(GovtBulletin, b.supersedes_id) if b.supersedes_id else None
    return {
        **_summary(b),
        "body": b.body,
        "source_name": b.source_name,
        "source_url": b.source_url,
        "recommended_actions": b.recommended_actions,
        "target_languages": b.target_languages,
        "segment": b.segment,
        "provenance": b.provenance,
        "extraction": b.extraction,
        "translations": [_translation_out(t) for t in translations],
        "readiness": svc.readiness(b, translations) if b.status in svc.APPROVABLE else [],
        "supersedes": str(supersedes.uuid) if supersedes else None,
        "withdrawn_reason": b.withdrawn_reason,
    }


# ── Officer: ingest and compose ───────────────────────────────────────────────


class BulletinFields(BaseModel):
    title: str | None = Field(default=None, max_length=300)
    authority: str | None = Field(default=None, max_length=200)
    authority_level: Literal["national", "state", "district", "block"] | None = None
    source_name: str | None = Field(default=None, max_length=200)
    source_url: str | None = Field(default=None, max_length=2000)
    issued_at: datetime | None = None
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    hazard_type: str | None = Field(default=None, max_length=32)
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] | None = None
    district_codes: list[int] | None = Field(default=None, max_length=100)
    block_codes: list[int] | None = Field(default=None, max_length=500)
    crops: list[str] | None = Field(default=None, max_length=30)
    recommended_actions: list[str] | None = Field(default=None, max_length=20)
    target_languages: list[Literal["en", "hi", "te"]] | None = None
    segment: dict[str, float] | None = None
    original_language: Literal["en", "hi", "te"] | None = None


class ComposeIn(BulletinFields):
    body: str = Field(min_length=1, max_length=20000)


class EditIn(BulletinFields):
    body: str | None = Field(default=None, max_length=20000)


@router.post("/bulletins/upload", status_code=status.HTTP_201_CREATED)
async def upload_bulletin(
    session: DbSession,
    auth: Officer,
    file: Annotated[UploadFile, File(description="PDF, image (OCR), DOCX or text bulletin")],
    fields: Annotated[str | None, Form(description="Optional JSON of BulletinFields")] = None,
) -> dict:
    """Officer upload → parse/OCR → structured extraction with provenance → review."""
    data = await file.read()
    if not data or len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Empty or oversized file")
    overrides = BulletinFields(**json.loads(fields)).model_dump(exclude_none=True) if fields else {}
    from app.knowledge.parsers.selector import ParserSelector  # noqa: PLC0415

    try:
        parsed, mime = await ParserSelector().parse(data, file.filename or "bulletin")
    except Exception as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, f"Could not read the file ({type(exc).__name__})"
        ) from exc
    text = "\n\n".join(p.text for p in parsed.pages if p.text and p.text.strip())
    digest = hashlib.sha256(data).hexdigest()
    folder = Path(get_settings().GOVCONNECT_STORAGE_PATH) / "uploads"
    folder.mkdir(parents=True, exist_ok=True)
    suffix = Path(file.filename or "").suffix[:10] or ".bin"
    path = folder / f"{digest[:16]}-{uuid4().hex[:8]}{suffix}"
    path.write_bytes(data)
    try:
        b = await svc.create_bulletin(
            session,
            source_type="upload",
            body=text,
            actor=str(auth.user_uuid),
            overrides=overrides,
            file_path=str(path),
            file_sha256=digest,
        )
    except svc.GovConnectError as exc:
        _raise(exc)
    b.extraction = {**b.extraction, "parser_mime": mime, "pages": len(parsed.pages)}
    await session.commit()
    return await _detail(session, b)


@router.post("/bulletins", status_code=status.HTTP_201_CREATED)
async def compose_bulletin(body: ComposeIn, session: DbSession, auth: Officer) -> dict:
    """Officer-composed bulletin (or from a template). Extraction pre-fills empty fields."""
    try:
        b = await svc.create_bulletin(
            session,
            source_type="composed",
            body=body.body,
            actor=str(auth.user_uuid),
            overrides=body.model_dump(exclude={"body"}, exclude_none=True),
        )
    except svc.GovConnectError as exc:
        _raise(exc)
    await session.commit()
    return await _detail(session, b)


@router.get("/bulletins")
async def list_bulletins(
    session: DbSession, auth: Officer, status_filter: str | None = None, limit: int = 100
) -> list[dict]:
    q = select(GovtBulletin).order_by(GovtBulletin.created_at.desc()).limit(min(limit, 500))
    if status_filter:
        q = q.where(GovtBulletin.status == status_filter)
    return [_summary(b) for b in (await session.scalars(q)).all()]


@router.get("/bulletins/{uuid}")
async def get_bulletin(uuid: UUID, session: DbSession, auth: Officer) -> dict:
    return await _detail(session, await _bulletin(session, uuid))


@router.patch("/bulletins/{uuid}")
async def edit_bulletin(uuid: UUID, body: EditIn, session: DbSession, auth: Officer) -> dict:
    b = await _bulletin(session, uuid)
    try:
        await svc.update_bulletin(
            session, b, body.model_dump(exclude_unset=True), str(auth.user_uuid)
        )
    except svc.GovConnectError as exc:
        _raise(exc)
    await session.commit()
    return await _detail(session, b)


@router.post("/bulletins/{uuid}/translate")
async def translate_bulletin(
    uuid: UUID, session: DbSession, auth: Officer, translator: Translator
) -> dict:
    """Translation preview in every target language (number/unit/term checked)."""
    b = await _bulletin(session, uuid)
    try:
        await svc.generate_translations(session, b, translator, str(auth.user_uuid))
    except svc.GovConnectError as exc:
        _raise(exc)
    await session.commit()
    return await _detail(session, b)


class TranslationApproveIn(BaseModel):
    title: str | None = Field(default=None, max_length=1000)
    body: str | None = Field(default=None, max_length=30000)


@router.post("/bulletins/{uuid}/translations/{language}/approve")
async def approve_bulletin_translation(
    uuid: UUID,
    language: Literal["en", "hi", "te"],
    body: TranslationApproveIn,
    session: DbSession,
    auth: Officer,
) -> dict:
    b = await _bulletin(session, uuid)
    try:
        await svc.approve_translation(
            session, b, language, str(auth.user_uuid), title=body.title, body=body.body
        )
    except svc.GovConnectError as exc:
        _raise(exc)
    await session.commit()
    return await _detail(session, b)


class ApproveIn(BaseModel):
    publish_at: datetime | None = None


@router.post("/bulletins/{uuid}/approve")
async def approve_bulletin(  # noqa: PLR0913, PLR0917 - FastAPI dependencies
    uuid: UUID,
    body: ApproveIn,
    session: DbSession,
    auth: Officer,
    notifier: Notifier,
    background: BackgroundTasks,
) -> dict:
    """Approve and publish now, or schedule for ``publish_at``."""
    b = await _bulletin(session, uuid)
    try:
        result = await svc.approve(
            session, b, str(auth.user_uuid), publish_at=body.publish_at, notifier=notifier
        )
    except svc.GovConnectError as exc:
        _raise(exc)
    await session.commit()
    if b.status == "published":
        background.add_task(svc.index_after_commit, b.id, get_indexer())
    return {"result": result, "bulletin": await _detail(session, b)}


class WithdrawIn(BaseModel):
    reason: str = Field(min_length=3, max_length=1000)


@router.post("/bulletins/{uuid}/withdraw")
async def withdraw_bulletin(
    uuid: UUID, body: WithdrawIn, session: DbSession, auth: Officer
) -> dict:
    b = await _bulletin(session, uuid)
    try:
        await svc.withdraw(session, b, body.reason, str(auth.user_uuid), get_indexer())
    except svc.GovConnectError as exc:
        _raise(exc)
    await session.commit()
    return await _detail(session, b)


@router.post("/bulletins/{uuid}/supersede", status_code=status.HTTP_201_CREATED)
async def supersede_bulletin(uuid: UUID, session: DbSession, auth: Officer) -> dict:
    """Start a corrected version (a draft copy). Publishing it marks this one superseded."""
    b = await _bulletin(session, uuid)
    try:
        new = await svc.start_supersession(session, b, str(auth.user_uuid))
    except svc.GovConnectError as exc:
        _raise(exc)
    await session.commit()
    return await _detail(session, new)


@router.get("/bulletins/{uuid}/audit")
async def bulletin_audit(uuid: UUID, session: DbSession, auth: Officer) -> list[dict]:
    b = await _bulletin(session, uuid)
    rows = (
        await session.scalars(
            select(GovConnectAudit)
            .where(GovConnectAudit.bulletin_id == b.id)
            .order_by(GovConnectAudit.at)
        )
    ).all()
    return [
        {"at": r.at.isoformat(), "actor": r.actor, "action": r.action, "detail": r.detail}
        for r in rows
    ]


@router.get("/analytics")
async def analytics(session: DbSession, auth: Officer, limit: int = 50) -> list[dict]:
    """Delivery, read, acknowledgement and flag rates, plus farmer questions, per bulletin."""
    bulletins = (
        await session.scalars(
            select(GovtBulletin)
            .where(GovtBulletin.published_at.is_not(None))
            .order_by(GovtBulletin.published_at.desc())
            .limit(min(limit, 200))
        )
    ).all()
    out = []
    for b in bulletins:
        d = BulletinDelivery
        row = (
            await session.execute(
                select(
                    func.count(d.id),
                    func.count(d.id).filter(d.notification_status == "sent"),
                    func.count(d.id).filter(d.notification_status == "suppressed"),
                    func.count(d.id).filter(d.notification_status == "deduplicated"),
                    func.count(d.read_at),
                    func.count(d.acknowledged_at),
                    func.count(d.flagged_at),
                ).where(d.bulletin_id == b.id)
            )
        ).one()
        questions = await session.scalar(
            select(func.count(ConversationTurnRecord.id)).where(
                ConversationTurnRecord.bulletin_uuid == str(b.uuid)
            )
        )
        total = row[0] or 0

        def rate(n: int, total: int = total) -> float | None:
            return round(n / total, 3) if total else None

        out.append(
            {
                **_summary(b),
                "recipients": total,
                "notified": row[1],
                "suppressed": row[2],
                "deduplicated": row[3],
                "read": row[4],
                "acknowledged": row[5],
                "flagged": row[6],
                "questions": questions or 0,
                "read_rate": rate(row[4]),
                "ack_rate": rate(row[5]),
                "flag_rate": rate(row[6]),
            }
        )
    return out


@router.get("/flags")
async def flags(session: DbSession, auth: Officer, status_filter: str = "new") -> list[dict]:
    """Farmer flags ("doesn't apply to me", "unclear") for officer follow-up."""
    rows = (
        await session.execute(
            select(BulletinDelivery, GovtBulletin)
            .join(GovtBulletin, GovtBulletin.id == BulletinDelivery.bulletin_id)
            .where(
                BulletinDelivery.flagged_at.is_not(None),
                BulletinDelivery.flag_status == status_filter,
            )
            .order_by(BulletinDelivery.flagged_at.desc())
            .limit(200)
        )
    ).all()
    return [
        {
            "delivery_id": d.id,
            "bulletin_uuid": str(b.uuid),
            "title": b.title,
            "farmer_id": d.farmer_id,
            "language": d.language,
            "match_level": d.match_level,
            "reason": d.flag_reason,
            "comment": d.flag_comment,
            "flagged_at": _iso(d.flagged_at),
            "status": d.flag_status,
        }
        for d, b in rows
    ]


class FlagTriageIn(BaseModel):
    status: Literal["reviewed", "dismissed"]


@router.post("/flags/{delivery_id}/triage")
async def triage_flag(
    delivery_id: int, body: FlagTriageIn, session: DbSession, auth: Officer
) -> dict:
    d = await session.get(BulletinDelivery, delivery_id)
    if d is None or d.flagged_at is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Flag not found")
    d.flag_status = body.status
    b = await session.get(GovtBulletin, d.bulletin_id)
    if b is not None:
        svc.audit(
            session,
            b,
            str(auth.user_uuid),
            "flag_triaged",
            delivery_id=delivery_id,
            status=body.status,
        )
    await session.commit()
    return {"delivery_id": delivery_id, "status": d.flag_status}


# ── Farmer: Govt Updates inbox ────────────────────────────────────────────────


async def current_farmer_id(session: AsyncSession, auth: AuthContext) -> int:
    farmer_id = await session.scalar(
        select(User.farmer_profile_id).where(User.uuid == auth.user_uuid)
    )
    if farmer_id is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No farmer profile is linked to this user")
    return farmer_id


def _inbox_state(b: GovtBulletin, now: datetime) -> str:
    if b.status in {"withdrawn", "superseded"}:
        return b.status
    if b.status == "expired" or (b.valid_to and svc._aware(b.valid_to) <= now):
        return "expired"
    return "active"


@router.get("/inbox")
async def inbox(
    session: DbSession, auth: Reader, active_only: bool = False, limit: int = 50
) -> list[dict]:
    """Official bulletins delivered to me, in my language, newest first."""
    farmer_id = await current_farmer_id(session, auth)
    rows = (
        await session.execute(
            select(BulletinDelivery, GovtBulletin)
            .join(GovtBulletin, GovtBulletin.id == BulletinDelivery.bulletin_id)
            .where(BulletinDelivery.farmer_id == farmer_id)
            .order_by(GovtBulletin.published_at.desc())
            .limit(min(limit, 200))
        )
    ).all()
    now = datetime.now(UTC)
    out = []
    for d, b in rows:
        state = _inbox_state(b, now)
        if active_only and state != "active":
            continue
        tr = await session.scalar(
            select(BulletinTranslation).where(
                BulletinTranslation.bulletin_id == b.id, BulletinTranslation.language == d.language
            )
        )
        superseded_by = None
        if b.status == "superseded":
            newer = await session.scalar(
                select(GovtBulletin.uuid).where(
                    GovtBulletin.supersedes_id == b.id, GovtBulletin.status == "published"
                )
            )
            superseded_by = str(newer) if newer else None
        out.append(
            {
                "bulletin_uuid": str(b.uuid),
                "official": True,
                "state": state,
                "language": d.language,
                "title": tr.title if tr else b.title,
                "body": tr.body if tr else b.body,
                "original_language": b.original_language,
                "original_title": b.title,
                "original_body": b.body,
                "recommended_actions": b.recommended_actions
                if d.language == b.original_language
                else [],
                "authority": b.authority,
                "authority_level": b.authority_level,
                "severity": b.severity,
                "hazard_type": b.hazard_type,
                "issued_at": _iso(b.issued_at),
                "valid_from": _iso(b.valid_from),
                "valid_to": _iso(b.valid_to),
                "source_url": b.source_url,
                "translated": d.language != b.original_language,
                "withdrawn_reason": b.withdrawn_reason,
                "superseded_by": superseded_by,
                "read_at": _iso(d.read_at),
                "acknowledged_at": _iso(d.acknowledged_at),
                "flag_reason": d.flag_reason,
            }
        )
    return out


async def _my_delivery(
    session: AsyncSession, auth: AuthContext, bulletin_uuid: UUID
) -> tuple[BulletinDelivery, GovtBulletin]:
    farmer_id = await current_farmer_id(session, auth)
    row = (
        await session.execute(
            select(BulletinDelivery, GovtBulletin)
            .join(GovtBulletin, GovtBulletin.id == BulletinDelivery.bulletin_id)
            .where(GovtBulletin.uuid == bulletin_uuid, BulletinDelivery.farmer_id == farmer_id)
        )
    ).first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not in your inbox")
    return row[0], row[1]


@router.post("/inbox/{bulletin_uuid}/read")
async def mark_read(bulletin_uuid: UUID, session: DbSession, auth: Reader) -> dict:
    d, _ = await _my_delivery(session, auth, bulletin_uuid)
    d.read_at = d.read_at or datetime.now(UTC)
    await session.commit()
    return {"read_at": _iso(d.read_at)}


@router.post("/inbox/{bulletin_uuid}/ack")
async def acknowledge(bulletin_uuid: UUID, session: DbSession, auth: Reader) -> dict:
    d, _ = await _my_delivery(session, auth, bulletin_uuid)
    now = datetime.now(UTC)
    d.read_at = d.read_at or now
    d.acknowledged_at = d.acknowledged_at or now
    await session.commit()
    return {"acknowledged_at": _iso(d.acknowledged_at)}


class FlagIn(BaseModel):
    reason: Literal["not_applicable", "unclear", "wrong_location", "other"]
    comment: str | None = Field(default=None, max_length=1000)


@router.post("/inbox/{bulletin_uuid}/flag")
async def flag(bulletin_uuid: UUID, body: FlagIn, session: DbSession, auth: Reader) -> dict:
    """ "This doesn't apply to me" / "unclear": goes to the officer flag queue."""
    d, _ = await _my_delivery(session, auth, bulletin_uuid)
    d.flag_reason, d.flag_comment = body.reason, body.comment
    d.flagged_at, d.flag_status = datetime.now(UTC), "new"
    await session.commit()
    return {"flagged": True}


@router.post("/inbox/{bulletin_uuid}/listen")
async def listen(bulletin_uuid: UUID, session: DbSession, auth: Reader) -> dict:
    """Synthesize the bulletin in the delivered language; fetch via /conversation/audio/{id}."""
    d, b = await _my_delivery(session, auth, bulletin_uuid)
    tr = await session.scalar(
        select(BulletinTranslation).where(
            BulletinTranslation.bulletin_id == b.id, BulletinTranslation.language == d.language
        )
    )
    text = f"{b.authority}. {tr.title if tr else b.title}. {tr.body if tr else b.body}"
    from app.voice.providers.selection import get_tts_provider  # noqa: PLC0415

    try:
        result = await get_tts_provider().synthesize(text=text[:4000], language=d.language)
    except Exception as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, f"Speech is unavailable ({type(exc).__name__})"
        ) from exc
    d.read_at = d.read_at or datetime.now(UTC)
    await session.commit()
    return {"audio_uuid": str(result.audio_uuid), "provider": result.model_name}


async def bulletin_context(
    session: AsyncSession, auth: AuthContext, bulletin_uuid: str
) -> tuple[str, Any]:
    """English context for "ask about this", plus a profile pre-filled from the bulletin.
    Farmers may only ask about bulletins in their inbox; publishers about any."""
    from app.conversation.manager import FarmerProfile  # noqa: PLC0415

    try:
        uid = UUID(bulletin_uuid)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "bad bulletin id") from exc
    if auth.has_permission(Permission.GOVCONNECT_PUBLISH):
        b = await _bulletin(session, uid)
    else:
        _, b = await _my_delivery(session, auth, uid)
    english = await session.scalar(
        select(BulletinTranslation).where(
            BulletinTranslation.bulletin_id == b.id, BulletinTranslation.language == "en"
        )
    )
    text = english.body if english else b.body
    valid = f" valid until {b.valid_to.isoformat()}" if b.valid_to else ""
    context = (
        f"Official bulletin from {b.authority}{valid} (status: {b.status}). "
        f"Treat it as authoritative and do not contradict it: {text}"
    )
    profile = FarmerProfile(
        district_lgd_code=b.district_codes[0] if len(b.district_codes) == 1 else None,
        crops=list(b.crops),
    )
    return context, profile
