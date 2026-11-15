"""Grievance tickets (F4): lifecycle, SLA and farmer notification.

open → assigned → in_progress → resolved | rejected → closed (a resolved/rejected ticket may be
reopened by the farmer once). SLA hours per category come from settings (configurable
defaults, not official service standards). Ticket text is personal data and never leaves the
device.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.models.govconnect import GrievanceEvent, GrievanceTicket

CATEGORIES = (
    "payment",
    "insurance_claim",
    "scheme_enrollment",
    "input_quality",
    "advisory",
    "infrastructure",
    "other",
)
TRANSITIONS: dict[str, set[str]] = {
    "open": {"assigned", "in_progress", "rejected"},
    "assigned": {"in_progress", "resolved", "rejected"},
    "in_progress": {"resolved", "rejected"},
    "resolved": {"closed", "reopened"},
    "rejected": {"closed", "reopened"},
    "reopened": {"assigned", "in_progress", "resolved", "rejected"},
    "closed": set(),
}
OPEN_STATES = {"open", "assigned", "in_progress", "reopened"}


class GrievanceError(Exception):
    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code, self.message = status_code, message


def sla_hours(category: str) -> int:
    table = get_settings().GRIEVANCE_SLA_HOURS
    return int(table.get(category, table.get("other", 120)))


def now_utc() -> datetime:
    return datetime.now(UTC)


def _aware(v: datetime) -> datetime:
    return v if v.tzinfo else v.replace(tzinfo=UTC)


def sla_state(t: GrievanceTicket, now: datetime | None = None) -> dict[str, Any]:
    now = now or now_utc()
    due = _aware(t.sla_due_at)
    end = _aware(t.resolved_at) if t.resolved_at else now
    breached = end > due
    return {
        "sla_due_at": due.isoformat(),
        "breached": breached,
        "hours_left": None
        if t.status not in OPEN_STATES
        else round((due - now).total_seconds() / 3600, 1),
    }


def event(  # noqa: PLR0913 - keyword-only options
    session: AsyncSession,
    t: GrievanceTicket,
    actor: str,
    *,
    status: str | None = None,
    note: str | None = None,
    public: bool = True,
) -> None:
    session.add(
        GrievanceEvent(
            ticket_id=t.id, actor=actor, status=status, note=note, public=public, at=now_utc()
        )
    )


async def create_ticket(  # noqa: PLR0913 - keyword-only options
    session: AsyncSession,
    *,
    farmer_id: int,
    category: str,
    subject: str,
    description: str,
    language: str,
    lgd_district_code: int | None,
    scheme_key: str | None,
    actor: str,
) -> GrievanceTicket:
    if category not in CATEGORIES:
        raise GrievanceError(422, f"category must be one of {CATEGORIES}")
    now = now_utc()
    t = GrievanceTicket(
        farmer_id=farmer_id,
        category=category,
        subject=subject.strip(),
        description=description.strip(),
        language=language,
        lgd_district_code=lgd_district_code,
        scheme_key=scheme_key,
        status="open",
        sla_due_at=now + timedelta(hours=sla_hours(category)),
    )
    session.add(t)
    await session.flush()
    event(session, t, actor, status="open")
    return t


async def change_status(  # noqa: PLR0913 - keyword-only options
    session: AsyncSession,
    t: GrievanceTicket,
    new_status: str,
    actor: str,
    *,
    note: str | None = None,
    public: bool = True,
    assignee: Any = None,
    notifier: Any = None,
) -> GrievanceTicket:
    allowed = TRANSITIONS.get(t.status, set())
    if new_status not in allowed:
        raise GrievanceError(409, f"Cannot move a {t.status} ticket to {new_status}")
    if new_status in {"rejected", "resolved"} and not (note or "").strip():
        raise GrievanceError(422, "A note explaining the outcome is required")
    now = now_utc()
    if new_status == "assigned":
        t.assigned_to = assignee
    if t.first_response_at is None and actor != "farmer":
        t.first_response_at = now
    if new_status in {"resolved", "rejected"}:
        t.resolved_at = now
    if new_status == "reopened":
        t.resolved_at = None
        t.sla_due_at = now + timedelta(hours=sla_hours(t.category))
    t.status = new_status
    event(session, t, actor, status=new_status, note=note, public=public)
    await session.flush()
    if notifier is not None and public and actor != "farmer":
        await notifier.dispatch_alert(
            session,
            t.farmer_id,
            title=f"Grievance update: {t.subject}"[:255],
            message=(note or new_status)[:1000],
            alert_type="grievance.update",
            topic_key=f"grievance:{t.uuid}:{new_status}",
        )
    return t
