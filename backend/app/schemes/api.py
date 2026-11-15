"""Scheme catalog and eligibility Q&A (F4). Officer-maintained; nothing is scraped.

Farmers (and the bot) see only ``verified`` entries. Officers import drafts, edit them and
verify each against its ``source_url``. Personal status (e.g. PM-KISAN payment) is a link to
the official portal: there is no public API, so it is never looked up for the farmer.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, Literal

import yaml
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import AuthContext, RequirePermission
from app.auth.permissions import Permission
from app.database.session import get_db_session
from app.models.govconnect import SchemeEntry
from app.schemes.eligibility import CriteriaError, evaluate, validate_criteria

router = APIRouter(prefix="/schemes", tags=["Schemes (F4)"])
DbSession = Annotated[AsyncSession, Depends(get_db_session)]
Reader = Annotated[AuthContext, Depends(RequirePermission(Permission.SCHEME_READ))]
Manager = Annotated[AuthContext, Depends(RequirePermission(Permission.SCHEME_MANAGE))]
DRAFTS = Path(__file__).with_name("drafts.yaml")


def _out(s: SchemeEntry, language: str | None = None, *, full: bool = False) -> dict:
    def pick(d: dict[str, str]) -> Any:
        return d if language is None else (d.get(language) or d.get("en"))

    data = {
        "key": s.key,
        "name": pick(s.names),
        "authority": s.authority,
        "scope": s.scope,
        "summary": pick(s.summary),
        "benefits": pick(s.benefits or {}),
        "source_url": s.source_url,
        "status_lookup_url": s.status_lookup_url,
        "status": s.status,
        "verified_at": s.verified_at.isoformat() if s.verified_at else None,
        "questions": [
            {
                "id": c["id"],
                "type": c["type"],
                "question": pick(c["question"]),
                "options": c.get("options"),
            }
            for c in s.criteria
        ],
    }
    if full:
        data["criteria"] = s.criteria
        data["state_codes"] = s.state_codes
    return data


async def _scheme(session: AsyncSession, key: str, *, verified_only: bool) -> SchemeEntry:
    s = await session.scalar(select(SchemeEntry).where(SchemeEntry.key == key))
    if s is None or (verified_only and s.status != "verified"):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Scheme not found")
    return s


@router.get("")
async def list_schemes(
    session: DbSession, auth: Reader, language: Literal["en", "hi", "te"] = "en"
) -> list[dict]:
    manager = auth.has_permission(Permission.SCHEME_MANAGE)
    q = select(SchemeEntry).order_by(SchemeEntry.key)
    if not manager:
        q = q.where(SchemeEntry.status == "verified")
    return [
        _out(s, None if manager else language, full=manager)
        for s in (await session.scalars(q)).all()
    ]


@router.get("/insurance/helper")
async def insurance_helper(  # noqa: PLR0913, PLR0917 - query parameters
    session: DbSession, auth: Reader, lgd_district_code: int | None = None,
    crop: str | None = None, season: str | None = None,
    language: Literal["en", "hi", "te"] = "en",
) -> dict:
    """F15: PMFBY guidance + the district yield outlook (labelled as a model estimate)."""
    from app.catalog.resolver import get_crop_catalog  # noqa: PLC0415
    from app.forecasting.selection import get_yield_provider  # noqa: PLC0415
    from app.schemes.insurance import build_helper  # noqa: PLC0415

    officer = Permission.SCHEME_MANAGE in auth.permissions
    s = await session.scalar(select(SchemeEntry).where(SchemeEntry.key == "pmfby"))
    verified = s is not None and s.status == "verified"
    scheme = _out(s, language) if s is not None and (verified or officer) else None
    card = None
    crop_key = get_crop_catalog().resolve_name(crop) if crop else None
    if lgd_district_code and crop_key:
        f = await get_yield_provider().forecast(session, lgd_district_code, crop_key, season)
        card = f.to_dict() if f else None
    return build_helper(scheme=scheme, verified=verified, officer=officer, language=language,
                        yield_card=card)


@router.get("/{key}")
async def get_scheme(
    key: str, session: DbSession, auth: Reader, language: Literal["en", "hi", "te"] = "en"
) -> dict:
    manager = auth.has_permission(Permission.SCHEME_MANAGE)
    s = await _scheme(session, key, verified_only=not manager)
    return _out(s, None if manager else language, full=manager)


class EligibilityIn(BaseModel):
    answers: dict[str, Any] = Field(default_factory=dict)
    language: Literal["en", "hi", "te"] = "en"


@router.post("/{key}/eligibility")
async def check_eligibility(
    key: str, body: EligibilityIn, session: DbSession, auth: Reader
) -> dict:
    """Guidance only: the scheme authority makes the final decision."""
    s = await _scheme(session, key, verified_only=True)
    result = evaluate(s.criteria, body.answers, body.language)
    return {
        **result,
        "scheme": s.key,
        "source_url": s.source_url,
        "status_lookup_url": s.status_lookup_url,
        "guidance_only": True,
    }


class SchemeIn(BaseModel):
    key: str = Field(pattern=r"^[a-z0-9_]{2,64}$")
    names: dict[str, str]
    authority: str = Field(min_length=2, max_length=200)
    scope: Literal["central", "state"]
    state_codes: list[int] = Field(default_factory=list)
    summary: dict[str, str]
    benefits: dict[str, str] = Field(default_factory=dict)
    criteria: list[dict[str, Any]] = Field(default_factory=list)
    source_url: str = Field(min_length=8, max_length=2000)
    status_lookup_url: str | None = None


def _check(body: SchemeIn) -> None:
    if not body.names.get("en") or not body.summary.get("en"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "English name/summary required")
    try:
        validate_criteria(body.criteria)
    except CriteriaError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc


@router.put("/{key}")
async def upsert_scheme(key: str, body: SchemeIn, session: DbSession, auth: Manager) -> dict:
    """Create or edit; any edit returns the entry to ``draft`` until re-verified."""
    if key != body.key:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "key mismatch")
    _check(body)
    s = await session.scalar(select(SchemeEntry).where(SchemeEntry.key == key))
    if s is None:
        s = SchemeEntry(**body.model_dump())
        session.add(s)
    else:
        for k, v in body.model_dump().items():
            setattr(s, k, v)
    s.status, s.verified_by, s.verified_at = "draft", None, None
    await session.commit()
    return _out(s, full=True)


@router.post("/{key}/verify")
async def verify_scheme(key: str, session: DbSession, auth: Manager) -> dict:
    """The officer confirms every criterion was checked against ``source_url``."""
    s = await _scheme(session, key, verified_only=False)
    s.status, s.verified_by, s.verified_at = "verified", auth.user_uuid, datetime.now(UTC)
    await session.commit()
    return _out(s, full=True)


@router.post("/import-drafts")
async def import_drafts(session: DbSession, auth: Manager) -> dict:
    """Load bundled DRAFT entries that are not in the catalog yet (never overwrites)."""
    created = []
    for item in yaml.safe_load(DRAFTS.read_text(encoding="utf-8")):
        body = SchemeIn(**item)
        _check(body)
        if await session.scalar(select(SchemeEntry.id).where(SchemeEntry.key == body.key)):
            continue
        session.add(SchemeEntry(**body.model_dump(), status="draft"))
        created.append(body.key)
    await session.commit()
    return {"created": created}
