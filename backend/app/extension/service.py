"""Assisted mode rules (F6): who may act for whom, consent, review-before-share."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select

from app.auth.permissions import Permission
from app.models.extension import ExtensionAssignment
from app.models.farmer import Farmer

CONSENT_METHODS = {"verbal_recorded", "signed_form", "otp", "in_app"}


async def active_assignment(session: Any, worker_uuid: UUID,
                            farmer_id: int) -> ExtensionAssignment | None:
    return await session.scalar(select(ExtensionAssignment).where(
        ExtensionAssignment.worker_user_uuid == worker_uuid,
        ExtensionAssignment.farmer_id == farmer_id,
        ExtensionAssignment.active.is_(True),
    ))


async def check_act_as(session: Any, auth: Any, farmer_id: int) -> Farmer:
    """Return the farmer if ``auth`` may act for them, else raise 403.

    Requires the ``extension:act_as`` permission, an active assignment and granted consent.
    """
    if not auth.has_permission(Permission.EXTENSION_ACT_AS):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not allowed to act for farmers")
    assignment = await active_assignment(session, auth.user_uuid, farmer_id)
    if assignment is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Farmer is not assigned to you")
    if assignment.consent_status != "granted":
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            "Farmer consent is not recorded; record consent first")
    farmer = await session.get(Farmer, farmer_id)
    if farmer is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Farmer not found")
    return farmer


def record_consent(assignment: ExtensionAssignment, *, granted: bool, method: str,
                   evidence: str | None) -> None:
    if method not in CONSENT_METHODS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            f"consent method must be one of {sorted(CONSENT_METHODS)}")
    assignment.consent_status = "granted" if granted else "revoked"
    assignment.consent_method = method
    assignment.consent_evidence = evidence
    assignment.consent_recorded_at = datetime.now(UTC)
