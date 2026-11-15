"""Assisted-mode API (F6): my farmers, batch registration, consent, review-before-share."""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import AuthContext, RequirePermission
from app.auth.permissions import Permission
from app.database.session import get_db_session
from app.extension.service import active_assignment, record_consent
from app.models.conversation import ConversationTurnRecord
from app.models.extension import ExtensionAssignment
from app.models.farmer import Farmer

router = APIRouter(prefix="/extension", tags=["Extension (assisted mode)"])
DbSession = Annotated[AsyncSession, Depends(get_db_session)]
Worker = Annotated[AuthContext, Depends(RequirePermission(Permission.EXTENSION_ACT_AS))]
Manager = Annotated[AuthContext, Depends(RequirePermission(Permission.EXTENSION_MANAGE))]


class ConsentIn(BaseModel):
    granted: bool = True
    method: str = Field(description="verbal_recorded | signed_form | otp | in_app")
    evidence: str | None = Field(default=None, max_length=2000,
                                 description="Form number, recording reference, etc.")


class FarmerIn(BaseModel):
    full_name: str = Field(min_length=1, max_length=150)
    phone: str = Field(min_length=10, max_length=15)
    preferred_language: str = Field(pattern="^(en|hi|te)$")
    district_id: int
    village: str = Field(min_length=1, max_length=150)
    landholding_acres: Decimal = Field(ge=0, le=100000)
    consent: ConsentIn


class BatchIn(BaseModel):
    farmers: list[FarmerIn] = Field(min_length=1, max_length=50)


class BatchRow(BaseModel):
    phone: str
    status: str  # created | duplicate_phone | error
    farmer_id: int | None = None
    detail: str | None = None


class AssignedFarmer(BaseModel):
    farmer_id: int
    full_name: str
    preferred_language: str
    district_id: int
    village: str
    consent_status: str
    consent_method: str | None


class AssignIn(BaseModel):
    worker_user_uuid: UUID
    farmer_id: int


class ShareIn(BaseModel):
    share: bool


@router.get("/farmers", response_model=list[AssignedFarmer])
async def my_farmers(session: DbSession, auth: Worker) -> list[AssignedFarmer]:
    rows = (await session.execute(
        select(ExtensionAssignment, Farmer).join(Farmer, Farmer.id == ExtensionAssignment.farmer_id)
        .where(ExtensionAssignment.worker_user_uuid == auth.user_uuid,
               ExtensionAssignment.active.is_(True))
    )).all()
    return [AssignedFarmer(farmer_id=f.id, full_name=f.full_name,
                           preferred_language=f.preferred_language, district_id=f.district_id,
                           village=f.village, consent_status=a.consent_status,
                           consent_method=a.consent_method) for a, f in rows]


@router.post("/farmers/batch", response_model=list[BatchRow],
             dependencies=[Depends(RequirePermission(Permission.FARMER_CREATE))])
async def batch_register(body: BatchIn, session: DbSession, auth: Worker) -> list[BatchRow]:
    """Register up to 50 farmers; each is assigned to the worker with recorded consent."""
    out: list[BatchRow] = []
    for f in body.farmers:
        try:
            async with session.begin_nested():
                farmer = Farmer(full_name=f.full_name, phone=f.phone,
                                preferred_language=f.preferred_language,
                                district_id=f.district_id, village=f.village,
                                landholding_acres=f.landholding_acres)
                session.add(farmer)
                await session.flush()
                assignment = ExtensionAssignment(worker_user_uuid=auth.user_uuid,
                                                 farmer_id=farmer.id, assigned_by=auth.user_uuid)
                record_consent(assignment, granted=f.consent.granted, method=f.consent.method,
                               evidence=f.consent.evidence)
                session.add(assignment)
            out.append(BatchRow(phone=f.phone, status="created", farmer_id=farmer.id))
        except IntegrityError:
            out.append(BatchRow(phone=f.phone, status="duplicate_phone",
                                detail="phone already registered or invalid district"))
        except HTTPException as exc:
            out.append(BatchRow(phone=f.phone, status="error", detail=str(exc.detail)))
    await session.commit()
    return out


@router.post("/farmers/{farmer_id}/consent", response_model=AssignedFarmer)
async def set_consent(farmer_id: int, body: ConsentIn, session: DbSession,
                      auth: Worker) -> AssignedFarmer:
    assignment = await active_assignment(session, auth.user_uuid, farmer_id)
    farmer = await session.get(Farmer, farmer_id)
    if assignment is None or farmer is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Farmer is not assigned to you")
    record_consent(assignment, granted=body.granted, method=body.method, evidence=body.evidence)
    await session.commit()
    return AssignedFarmer(farmer_id=farmer.id, full_name=farmer.full_name,
                          preferred_language=farmer.preferred_language,
                          district_id=farmer.district_id, village=farmer.village,
                          consent_status=assignment.consent_status,
                          consent_method=assignment.consent_method)


@router.post("/assignments", status_code=status.HTTP_201_CREATED)
async def assign(body: AssignIn, session: DbSession, auth: Manager) -> dict:
    """Officer assigns an existing farmer to a worker (consent is still pending)."""
    if await session.get(Farmer, body.farmer_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Farmer not found")
    session.add(ExtensionAssignment(worker_user_uuid=body.worker_user_uuid,
                                    farmer_id=body.farmer_id, assigned_by=auth.user_uuid))
    try:
        await session.commit()
    except IntegrityError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, "Already assigned") from exc
    return {"worker_user_uuid": str(body.worker_user_uuid), "farmer_id": body.farmer_id,
            "consent_status": "pending"}


@router.get("/review-queue")
async def review_queue(session: DbSession, auth: Worker) -> list[dict]:
    """AI answers given in assisted mode that the worker has not yet shared or discarded."""
    rows = (await session.scalars(
        select(ConversationTurnRecord).where(
            ConversationTurnRecord.user_uuid == auth.user_uuid,
            ConversationTurnRecord.acting_for_farmer_id.is_not(None),
            ConversationTurnRecord.shared_with_farmer.is_(False),
            ConversationTurnRecord.review_reason.is_distinct_from("discarded_by_worker"),
        ).order_by(ConversationTurnRecord.created_at.desc()).limit(100)
    )).all()
    return [{"turn_uuid": t.turn_uuid, "farmer_id": t.acting_for_farmer_id,
             "language": t.language, "question": t.user_text, "answer": t.reply_text,
             "answer_en": t.reply_text_en, "requires_review": t.requires_review,
             "citations": t.citations, "created_at": t.created_at.isoformat()} for t in rows]


@router.post("/turns/{turn_uuid}/share")
async def share_turn(turn_uuid: str, body: ShareIn, session: DbSession, auth: Worker) -> dict:
    turn = await session.scalar(select(ConversationTurnRecord).where(
        ConversationTurnRecord.turn_uuid == turn_uuid,
        ConversationTurnRecord.user_uuid == auth.user_uuid))
    if turn is None or turn.acting_for_farmer_id is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Assisted-mode turn not found")
    if body.share:
        turn.shared_with_farmer = True
    else:
        turn.review_reason = "discarded_by_worker"
    await session.commit()
    return {"turn_uuid": turn_uuid, "shared": turn.shared_with_farmer}
