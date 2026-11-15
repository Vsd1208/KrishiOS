"""Official mandi price history (AGMARKNET via data.gov.in) and trends.

Each day's state-wide rows are fetched with one request (the variety-wise resource supports an
``Arrival_Date`` filter; ~500 Telangana rows/day) and upserted unchanged. Trends use the daily
**median modal price across the district's markets**, so one unusual market does not swing
the line. A 7-day change at or beyond ``MANDI_ALERT_CHANGE_PCT`` is a sharp move.
"""

from __future__ import annotations

import asyncio
import statistics
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Any

import httpx
from loguru import logger
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.models.govconnect import MandiPriceDaily

USER_AGENT = "KrishiOS-market/1.0"
RETRIES = 3
STALE_AFTER_DAYS = 5  # an older latest report is shown as stale and never alerted on


def _num(v: Any) -> float | None:
    try:
        return float(str(v).replace(",", "")) if v not in (None, "", "NR") else None
    except ValueError:
        return None


def _field(rec: dict[str, Any], name: str) -> Any:
    """The history resource uses Title_Case keys, the daily one lower_case."""
    return rec.get(name, rec.get(name.lower(), rec.get(name.title())))


def crop_key(commodity: str) -> str | None:
    from app.catalog.resolver import get_crop_catalog  # noqa: PLC0415

    catalog = get_crop_catalog()
    return catalog.resolve_name(commodity.split("(", maxsplit=1)[0]) or catalog.resolve_name(
        commodity
    )


async def fetch_day(
    day: date,
    state: str,
    *,
    resource: str | None = None,
    date_filter: bool = True,
    client: httpx.AsyncClient | None = None,
) -> list[dict[str, Any]]:
    s = get_settings()
    if not s.DATA_GOV_IN_API_KEY:
        from app.providers import ProviderConfigurationError  # noqa: PLC0415

        raise ProviderConfigurationError("mandi history needs DATA_GOV_IN_API_KEY")
    resource = resource or s.DATA_GOV_IN_AGMARKNET_HISTORY_RESOURCE
    params: dict[str, Any] = {"api-key": s.DATA_GOV_IN_API_KEY, "format": "json", "limit": 2000}
    if date_filter:  # history resource: Title_Case filter keys, one day at a time
        params |= {"filters[State]": state, "filters[Arrival_Date]": day.strftime("%d/%m/%Y")}
    else:  # current-day resource: lower_case keys, always the latest batch
        params["filters[state]"] = state
    own = client is None
    client = client or httpx.AsyncClient(timeout=90, headers={"User-Agent": USER_AGENT})
    try:
        for attempt in range(1, RETRIES + 1):
            try:
                r = await client.get(
                    f"{s.MARKET_API_BASE_URL.rstrip('/')}/{resource}", params=params
                )
                r.raise_for_status()
                return list(r.json().get("records", []))
            except (httpx.TransportError, httpx.HTTPStatusError) as exc:
                if attempt == RETRIES:
                    raise
                logger.warning("data.gov.in retry {} for {}: {}", attempt, day, type(exc).__name__)
                await asyncio.sleep(5 * attempt)
    finally:
        if own:
            await client.aclose()
    return []


def to_rows(records: list[dict[str, Any]], resource: str, now: datetime) -> list[dict[str, Any]]:
    rows = []
    for rec in records:
        modal = _num(_field(rec, "Modal_Price"))
        try:
            day = datetime.strptime(str(_field(rec, "Arrival_Date")), "%d/%m/%Y").date()
        except ValueError:
            continue
        if modal is None:
            continue  # official rows without a modal price are not stored (never filled in)
        commodity = str(_field(rec, "Commodity") or "")
        rows.append(
            {
                "arrival_date": day,
                "state": str(_field(rec, "State") or ""),
                "district": str(_field(rec, "District") or ""),
                "market": str(_field(rec, "Market") or ""),
                "commodity": commodity,
                "variety": str(_field(rec, "Variety") or ""),
                "grade": str(_field(rec, "Grade") or ""),
                "crop_canonical": crop_key(commodity),
                "min_price": _num(_field(rec, "Min_Price")),
                "max_price": _num(_field(rec, "Max_Price")),
                "modal_price": modal,
                "source_resource": resource,
                "fetched_at": now,
            }
        )
    return rows


_KEY = ("arrival_date", "state", "district", "market", "commodity", "variety", "grade")


def dedupe(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    """The official feed occasionally repeats a (market, commodity, variety, grade, day) row;
    the last one published wins. Returns (unique rows, number of repeats dropped)."""
    unique: dict[tuple, dict[str, Any]] = {}
    for row in rows:
        unique[tuple(row[k] for k in _KEY)] = row
    return list(unique.values()), len(rows) - len(unique)


async def upsert(session: AsyncSession, rows: list[dict[str, Any]]) -> int:
    rows, repeats = dedupe(rows)
    if repeats:
        logger.info("mandi history: {} repeated official rows collapsed", repeats)
    if not rows:
        return 0
    stmt = insert(MandiPriceDaily).values(rows)
    stmt = stmt.on_conflict_do_update(
        constraint="uq_mandi_price_row",
        set_={
            k: stmt.excluded[k]
            for k in ("min_price", "max_price", "modal_price", "crop_canonical", "fetched_at")
        },
    )
    await session.execute(stmt)
    return len(rows)


@dataclass(slots=True)
class SyncResult:
    days: int = 0
    rows: int = 0
    failed_days: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"days": self.days, "rows": self.rows, "failed_days": self.failed_days}


async def sync_days(session: AsyncSession, days: list[date], states: list[str]) -> SyncResult:
    s = get_settings()
    result = SyncResult()
    now = datetime.now(UTC)
    async with httpx.AsyncClient(timeout=90, headers={"User-Agent": USER_AGENT}) as client:
        for day in days:
            for state in states:
                try:
                    records = await fetch_day(day, state, client=client)
                except (httpx.HTTPError, ValueError) as exc:
                    result.failed_days.append(f"{day.isoformat()} {state}: {type(exc).__name__}")
                    continue
                result.rows += await upsert(
                    session, to_rows(records, s.DATA_GOV_IN_AGMARKNET_HISTORY_RESOURCE, now)
                )
            result.days += 1
            await session.flush()
        # The history resource lags about a day; the current-day resource has the latest day.
        for state in states:
            try:
                latest = await fetch_day(
                    date.today(),
                    state,
                    client=client,
                    resource=s.DATA_GOV_IN_AGMARKNET_RESOURCE,
                    date_filter=False,
                )
                result.rows += await upsert(
                    session, to_rows(latest, s.DATA_GOV_IN_AGMARKNET_RESOURCE, now)
                )
            except (httpx.HTTPError, ValueError) as exc:
                result.failed_days.append(f"current {state}: {type(exc).__name__}")
        await session.flush()
    return result


@dataclass(slots=True)
class Trend:
    crop: str
    district: str
    points: list[dict[str, Any]]  # [{date, median_modal, markets}]
    latest: dict[str, Any] | None
    change_7d_pct: float | None
    sharp: bool
    stale: bool = False
    days_since_latest: int | None = None


async def trend(
    session: AsyncSession, *, crop: str, district: str, days: int = 30, today: date | None = None
) -> Trend:
    today = today or date.today()
    rows = (
        await session.execute(
            select(
                MandiPriceDaily.arrival_date, MandiPriceDaily.modal_price, MandiPriceDaily.market
            )
            .where(
                MandiPriceDaily.crop_canonical == crop,
                MandiPriceDaily.district.ilike(district),
                MandiPriceDaily.arrival_date >= today - timedelta(days=days),
            )
            .order_by(MandiPriceDaily.arrival_date)
        )
    ).all()
    by_day: dict[date, list[float]] = {}
    markets: dict[date, set[str]] = {}
    for d, modal, market in rows:
        by_day.setdefault(d, []).append(modal)
        markets.setdefault(d, set()).add(market)
    points = [
        {
            "date": d.isoformat(),
            "median_modal": round(statistics.median(v), 1),
            "markets": len(markets[d]),
        }
        for d, v in sorted(by_day.items())
    ]
    latest = points[-1] if points else None
    change = None
    if latest:
        last_day = date.fromisoformat(latest["date"])
        past = [p for p in points if date.fromisoformat(p["date"]) <= last_day - timedelta(days=7)]
        if past and past[-1]["median_modal"]:
            change = round(
                (latest["median_modal"] - past[-1]["median_modal"])
                / past[-1]["median_modal"]
                * 100,
                1,
            )
    threshold = get_settings().MANDI_ALERT_CHANGE_PCT
    age = (today - date.fromisoformat(latest["date"])).days if latest else None
    stale = age is None or age > STALE_AFTER_DAYS
    return Trend(
        crop,
        district,
        points,
        latest,
        change,
        sharp=not stale and change is not None and abs(change) >= threshold,
        stale=stale,
        days_since_latest=age,
    )
