"""Grievance API (F4): farmers raise and follow tickets; officers triage with SLA tracking."""

from __future__ import annotations

from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import AuthContext, RequirePermission
from app.auth.permissions import Permission
from app.database.session import get_db_session
from app.govconnect.api import current_farmer_id, get_notifier
from app.grievance import service as svc
from app.models.district import District
from app.models.farmer import Farmer
from app.models.govconnect import GrievanceEvent, GrievanceTicket

router = APIRouter(prefix="/grievances", tags=["Grievances (F4)"])
DbSession = Annotated[AsyncSession, Depends(get_db_session)]
Submitter = Annotated[AuthContext, Depends(RequirePermission(Permission.GRIEVANCE_SUBMIT))]
Manager = Annotated[AuthContext, Depends(RequirePermission(Permission.GRIEVANCE_MANAGE))]
Notifier = Annotated[Any, Depends(get_notifier)]


def _raise(exc: svc.GrievanceError) -> None:
    raise HTTPException(exc.status_code, exc.message) from exc


def _out(
    t: GrievanceTicket, events: list[GrievanceEvent] | None = None, *, officer: bool = False
) -> dict:
    data = {
        "uuid": str(t.uuid),
        "category": t.category,
        "subject": t.subject,
        "description": t.description,
        "language": t.language,
        "status": t.status,
        "priority": t.priority,
        "scheme_key": t.scheme_key,
        "lgd_district_code": t.lgd_district_code,
        "created_at": t.created_at.isoformat(),
        "resolved_at": t.resolved_at.isoformat() if t.resolved_at else None,
        **svc.sla_state(t),
    }
    if officer:
        data.update(
            {
                "farmer_id": t.farmer_id,
                "assigned_to": str(t.assigned_to) if t.assigned_to else None,
                "first_response_at": t.first_response_at.isoformat()
                if t.first_response_at
                else None,
            }
        )
    if events is not None:
        data["events"] = [
            {
                "at": e.at.isoformat(),
                "status": e.status,
                "note": e.note,
                "public": e.public,
                "by": "officer" if e.actor != "farmer" else "farmer",
            }
            for e in events
            if officer or e.public
        ]
    return data


async def _events(session: AsyncSession, t: GrievanceTicket) -> list[GrievanceEvent]:
    return list(
        (
            await session.scalars(
                select(GrievanceEvent)
                .where(GrievanceEvent.ticket_id == t.id)
                .order_by(GrievanceEvent.at)
            )
        ).all()
    )


async def _ticket(session: AsyncSession, uuid: UUID) -> GrievanceTicket:
    t = await session.scalar(select(GrievanceTicket).where(GrievanceTicket.uuid == uuid))
    if t is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ticket not found")
    return t


class TicketIn(BaseModel):
    category: Literal[
        "payment",
        "insurance_claim",
        "scheme_enrollment",
        "input_quality",
        "advisory",
        "infrastructure",
        "other",
    ]
    subject: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=5, max_length=5000)
    language: Literal["en", "hi", "te"]
    scheme_key: str | None = Field(default=None, max_length=64)


@router.post("", status_code=status.HTTP_201_CREATED)
async def raise_ticket(body: TicketIn, session: DbSession, auth: Submitter) -> dict:
    farmer_id = await current_farmer_id(session, auth)
    district = await session.scalar(
        select(District.lgd_district_code)
        .join(Farmer, Farmer.district_id == District.id)
        .where(Farmer.id == farmer_id)
    )
    try:
        t = await svc.create_ticket(
            session,
            farmer_id=farmer_id,
            category=body.category,
            subject=body.subject,
            description=body.description,
            language=body.language,
            lgd_district_code=district,
            scheme_key=body.scheme_key,
            actor="farmer",
        )
    except svc.GrievanceError as exc:
        _raise(exc)
    await session.commit()
    return _out(t, await _events(session, t))


@router.get("/mine")
async def my_tickets(session: DbSession, auth: Submitter) -> list[dict]:
    farmer_id = await current_farmer_id(session, auth)
    rows = (
        await session.scalars(
            select(GrievanceTicket)
            .where(GrievanceTicket.farmer_id == farmer_id)
            .order_by(GrievanceTicket.created_at.desc())
        )
    ).all()
    return [_out(t) for t in rows]


@router.get("/mine/{uuid}")
async def my_ticket(uuid: UUID, session: DbSession, auth: Submitter) -> dict:
    farmer_id = await current_farmer_id(session, auth)
    t = await _ticket(session, uuid)
    if t.farmer_id != farmer_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ticket not found")
    return _out(t, await _events(session, t))


class FarmerActionIn(BaseModel):
    action: Literal["close", "reopen"]
    note: str | None = Field(default=None, max_length=2000)


@router.post("/mine/{uuid}")
async def farmer_action(
    uuid: UUID, body: FarmerActionIn, session: DbSession, auth: Submitter
) -> dict:
    """The farmer confirms (close) or disputes (reopen) a resolved/rejected ticket."""
    farmer_id = await current_farmer_id(session, auth)
    t = await _ticket(session, uuid)
    if t.farmer_id != farmer_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ticket not found")
    target = "closed" if body.action == "close" else "reopened"
    try:
        await svc.change_status(session, t, target, "farmer", note=body.note)
    except svc.GrievanceError as exc:
        _raise(exc)
    await session.commit()
    return _out(t, await _events(session, t))


@router.get("/queue")
async def queue(
    session: DbSession,
    auth: Manager,
    status_filter: str | None = None,
    district: int | None = None,
    breached_only: bool = False,
) -> list[dict]:
    q = select(GrievanceTicket).order_by(GrievanceTicket.sla_due_at)
    if status_filter:
        q = q.where(GrievanceTicket.status == status_filter)
    else:
        q = q.where(GrievanceTicket.status.in_(sorted(svc.OPEN_STATES)))
    if district is not None:
        q = q.where(GrievanceTicket.lgd_district_code == district)
    rows = [_out(t, officer=True) for t in (await session.scalars(q.limit(500))).all()]
    return [r for r in rows if r["breached"]] if breached_only else rows


@router.get("/queue/{uuid}")
async def queue_ticket(uuid: UUID, session: DbSession, auth: Manager) -> dict:
    t = await _ticket(session, uuid)
    return _out(t, await _events(session, t), officer=True)


class OfficerActionIn(BaseModel):
    status: Literal["assigned", "in_progress", "resolved", "rejected", "closed"]
    note: str | None = Field(default=None, max_length=2000)
    public: bool = True
    assignee: UUID | None = None


@router.post("/queue/{uuid}")
async def officer_action(
    uuid: UUID, body: OfficerActionIn, session: DbSession, auth: Manager, notifier: Notifier
) -> dict:
    t = await _ticket(session, uuid)
    try:
        await svc.change_status(
            session,
            t,
            body.status,
            str(auth.user_uuid),
            note=body.note,
            public=body.public,
            assignee=body.assignee or auth.user_uuid,
            notifier=notifier,
        )
    except svc.GrievanceError as exc:
        _raise(exc)
    await session.commit()
    return _out(t, await _events(session, t), officer=True)
