"""Translation API (Sprint 11)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from app.api.dependencies.auth import AuthContext, RequirePermission, get_current_auth_context
from app.auth.permissions import Permission
from app.database.session import get_db_session
from app.models.translation import TranslationRecord
from app.translation.checks import check_translation
from app.translation.glossary import get_glossary
from app.translation.schemas import (
    ApproveRequest,
    AttemptOut,
    CheckOut,
    CheckRequest,
    GlossaryOut,
    RecordOut,
    TranslateRequest,
    TranslateResponse,
)
from app.translation.service import TranslationStatus, get_translation_service
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/translation", tags=["Translation"])

Auth = Annotated[AuthContext, Depends(get_current_auth_context)]
DbSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.post(
    "/translate",
    response_model=TranslateResponse,
    dependencies=[Depends(RequirePermission(Permission.TRANSLATION_USE))],
)
async def translate(req: TranslateRequest, auth: Auth,
                    session: DbSession) -> TranslateResponse:
    """Translate with protected terms, number/unit checks and the approval policy."""
    out = await get_translation_service().translate(
        req.text, req.source_language, req.target_language, severity=req.severity,
        personal_data=req.personal_data, back_translate=req.back_translate,
    )
    record_uuid = None
    if req.persist and out.status is not TranslationStatus.PASSTHROUGH:
        record = TranslationRecord(
            content_hash=out.content_hash, source_language=out.source_language,
            target_language=out.target_language, source_text=out.source_text,
            translated_text=out.text, back_translation=out.back_translation,
            provider=out.provider, provider_version=out.provider_version,
            glossary_version=out.glossary_version, severity=req.severity,
            status=out.status.value, checks=out.checks.to_dict(),
            attempts=out.to_dict()["attempts"],
        )
        session.add(record)
        await session.commit()
        record_uuid = record.uuid
    return TranslateResponse(
        source_language=out.source_language, target_language=out.target_language,
        text=out.text, status=out.status.value, deliverable=out.deliverable,
        checks=CheckOut(**out.checks.to_dict()), provider=out.provider,
        provider_version=out.provider_version, glossary_version=out.glossary_version,
        cached=out.cached, protected_spans=out.protected_spans,
        attempts=[AttemptOut(**a) for a in out.to_dict()["attempts"]],
        back_translation=out.back_translation, record_uuid=record_uuid,
    )


@router.post("/check", response_model=CheckOut,
             dependencies=[Depends(RequirePermission(Permission.TRANSLATION_USE))])
async def check(req: CheckRequest) -> CheckOut:
    """Run the number/unit/protected-term checks on any source/translation pair."""
    return CheckOut(**check_translation(req.source, req.translation).to_dict())


@router.get("/glossary", response_model=GlossaryOut)
async def glossary() -> GlossaryOut:
    g = get_glossary()
    return GlossaryOut(version=g.version, protected_terms=list(g.protected_terms),
                       units={k: list(v) for k, v in g.units.items()})


@router.post(
    "/records/{record_uuid}/approve",
    response_model=RecordOut,
    dependencies=[Depends(RequirePermission(Permission.TRANSLATION_APPROVE))],
)
async def approve(record_uuid: UUID, req: ApproveRequest, auth: Auth,
                  session: DbSession) -> RecordOut:
    """Officer approval of a translation (optionally edited; edits are re-checked)."""
    record = await session.scalar(
        select(TranslationRecord).where(TranslationRecord.uuid == record_uuid)
    )
    if record is None:
        raise HTTPException(status_code=404, detail="Translation record not found")
    text = req.edited_text or record.translated_text
    checks = check_translation(record.source_text, text)
    if not checks.passed:
        raise HTTPException(status_code=422, detail={"message": "Edited text fails checks",
                                                     "reasons": checks.reasons})
    record.edited_by_reviewer = req.edited_text is not None and text != record.translated_text
    record.translated_text = text
    record.checks = checks.to_dict()
    record.status = "approved"
    record.approved_by = auth.user_uuid
    record.approved_at = datetime.now(UTC)
    await session.commit()
    return RecordOut(uuid=record.uuid, status=record.status,
                     translated_text=record.translated_text, provider=record.provider,
                     approved_by=record.approved_by,
                     edited_by_reviewer=record.edited_by_reviewer, checks=record.checks)
