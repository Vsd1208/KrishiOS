"""F8: record photo diagnoses, aggregate them into a district x week heat grid, and find
possible outbreaks.

A possible outbreak is a district x crop x condition whose distinct reporters this week are
>= ``OUTBREAK_MIN_REPORTERS`` and >= ``OUTBREAK_RATIO`` x the mean of the previous 4 weeks.
"Healthy" findings never count. Findings are model output (possibilities); an outbreak only
reaches farmers after an officer approves the review draft created by the scan job.
"""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.models.surveillance import DiagnosisReport

TRAILING_WEEKS = 4


def week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())  # Monday


def reporter_hash(user_uuid: str) -> str:
    s = get_settings()
    key = (s.SURVEILLANCE_PSEUDONYM_KEY or s.JWT_SECRET_KEY).encode()
    return hmac.new(key, str(user_uuid).encode(), hashlib.sha256).hexdigest()[:32]


async def record(  # noqa: PLR0913 - keyword-only report fields
    session: AsyncSession, *, user_uuid: str, lgd_district_code: int, crop: str,
                 condition: str, confidence: float, confirmed: bool, model_version: str,
                 at: datetime | None = None) -> bool:
    """Store one report (idempotent per reporter x district x crop x condition x week).
    Returns False for healthy findings, which are not stored."""
    if condition.strip().lower() == "healthy":
        return False
    at = at or datetime.now(UTC)
    stmt = insert(DiagnosisReport).values(
        reported_at=at, week_start=week_start(at.date()), lgd_district_code=lgd_district_code,
        crop_canonical=crop, condition=condition, confidence=confidence,
        crop_confirmed_by_farmer=confirmed, model_version=model_version,
        reporter_hash=reporter_hash(user_uuid), source="photo_turn",
    ).on_conflict_do_nothing(constraint="uq_diagnosis_report_weekly")
    await session.execute(stmt)
    return True


async def heat_grid(session: AsyncSession, weeks: int = 8, today: date | None = None,
                    crop: str | None = None) -> list[dict[str, Any]]:
    """Distinct reporters per district x crop x condition x week (last ``weeks`` weeks)."""
    first = week_start(today or datetime.now(UTC).date()) - timedelta(weeks=weeks - 1)
    q = (select(DiagnosisReport.lgd_district_code, DiagnosisReport.crop_canonical,
                DiagnosisReport.condition, DiagnosisReport.week_start,
                func.count(func.distinct(DiagnosisReport.reporter_hash)),
                func.avg(DiagnosisReport.confidence))
         .where(DiagnosisReport.week_start >= first)
         .group_by(DiagnosisReport.lgd_district_code, DiagnosisReport.crop_canonical,
                   DiagnosisReport.condition, DiagnosisReport.week_start))
    if crop:
        q = q.where(DiagnosisReport.crop_canonical == crop)
    return [{"lgd_district_code": d, "crop": c, "condition": k, "week_start": w.isoformat(),
             "reporters": int(n), "mean_confidence": round(float(m), 3)}
            for d, c, k, w, n, m in (await session.execute(q)).all()]


@dataclass(frozen=True, slots=True)
class Outbreak:
    lgd_district_code: int
    crop: str
    condition: str
    week_start: date
    reporters: int
    baseline: float


def find_outbreaks(cells: list[dict[str, Any]], week: date,
                   min_reporters: int | None = None, ratio: float | None = None
                   ) -> list[Outbreak]:
    s = get_settings()
    min_reporters = s.OUTBREAK_MIN_REPORTERS if min_reporters is None else min_reporters
    ratio = s.OUTBREAK_RATIO if ratio is None else ratio
    by_key: dict[tuple, dict[date, int]] = {}
    for c in cells:
        key = (c["lgd_district_code"], c["crop"], c["condition"])
        by_key.setdefault(key, {})[date.fromisoformat(c["week_start"])] = c["reporters"]
    out = []
    for (d, crop, cond), series in by_key.items():
        now = series.get(week, 0)
        prev = [series.get(week - timedelta(weeks=i), 0) for i in range(1, TRAILING_WEEKS + 1)]
        base = sum(prev) / TRAILING_WEEKS
        if now >= min_reporters and now >= ratio * base:
            out.append(Outbreak(d, crop, cond, week, now, round(base, 2)))
    return sorted(out, key=lambda o: -o.reporters)
