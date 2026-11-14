"""District weather feed (Phase 5): forecast + independent cross-check + proactive events.

For every district with KrishiOS farmers (and coordinates), each run:
1. fetches the 7-day forecast (Open-Meteo) and its last-7-day values;
2. cross-checks those against NASA POWER (independent source; ADR-023);
3. stores a ``DistrictWeatherSnapshot`` (dashboard feed, freshness, reliability);
4. emits ``weather.heavy_rain`` (≥ 40 mm/day) and ``weather.extreme_heat`` (≥ 39 °C) events for
   the next 3 days into the proactive engine, carrying the cross-check status.

Model forecasts are advisory; official warnings come from SACHET/IMD bulletins and always take
precedence in the farmer UI.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Any, Protocol

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.events.contracts import EventEnvelope, EventType
from app.live_data.services.crosscheck import compare
from app.models.govconnect import DistrictWeatherSnapshot

HEAVY_RAIN_MM = 40.0  # matches HeavyRainfallRule's actionable threshold
EXTREME_HEAT_C = 39.0  # matches ExtremeHeatRule
EVENT_HORIZON_DAYS = 3
HISTORY_DAYS = 7


class Forecaster(Protocol):
    provider_name: str

    async def get_forecast(self, latitude: float, longitude: float, days: int = 7) -> Any: ...

    async def get_daily_history(
        self, latitude: float, longitude: float, past_days: int = 7
    ) -> dict: ...


class Reference(Protocol):
    provider_name: str

    async def daily(self, latitude: float, longitude: float, start: date, end: date) -> dict: ...


class EventSink(Protocol):
    async def __call__(self, session: AsyncSession, event: EventEnvelope) -> Any: ...


@dataclass(slots=True)
class FeedDistrict:
    lgd_district_code: int
    district_name: str
    state_name: str
    latitude: float
    longitude: float


@dataclass(slots=True)
class FeedResult:
    districts: int = 0
    ok: int = 0
    partial: int = 0
    failed: int = 0
    events: int = 0
    crosscheck: dict[str, int] = field(default_factory=dict)
    skipped_no_coordinates: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "districts": self.districts,
            "ok": self.ok,
            "partial": self.partial,
            "failed": self.failed,
            "events": self.events,
            "crosscheck": self.crosscheck,
            "skipped_no_coordinates": self.skipped_no_coordinates,
        }


async def feed_districts(session: AsyncSession) -> tuple[list[FeedDistrict], int]:
    """Districts with farmers or saved locations that have coordinates in ``district``."""
    from app.govconnect.feeds.sachet import active_district_codes  # noqa: PLC0415
    from app.models.district import District  # noqa: PLC0415

    codes = await active_district_codes(session)
    rows = (
        (await session.scalars(select(District).where(District.lgd_district_code.in_(codes)))).all()
        if codes
        else []
    )
    found = {r.lgd_district_code for r in rows}
    out = [
        FeedDistrict(
            r.lgd_district_code, r.district_name, r.state, float(r.latitude), float(r.longitude)
        )
        for r in rows
    ]
    return out, len(codes - found)


def events_for(
    d: FeedDistrict, forecast_days: list[Any], crosscheck_status: str, today: date
) -> list[EventEnvelope]:
    horizon = today + timedelta(days=EVENT_HORIZON_DAYS)
    events = []
    for day in forecast_days:
        when = date.fromisoformat(day.date)
        if not today <= when < horizon:
            continue
        base = {
            "district": d.district_name,
            "state": d.state_name,
            "lgd_district_code": d.lgd_district_code,
            "date": day.date,
            "source": "open-meteo forecast",
            "crosscheck": crosscheck_status,
            "official": False,
        }
        if day.precipitation_sum_mm >= HEAVY_RAIN_MM:
            events.append(
                EventEnvelope(
                    event_type=EventType.HEAVY_RAIN_EXPECTED.value,
                    source="weather_feed",
                    payload={
                        **base,
                        "rainfall_mm": day.precipitation_sum_mm,
                        "probability": day.precipitation_probability_percent / 100.0,
                    },
                )
            )
        if day.temperature_max_celsius >= EXTREME_HEAT_C:
            events.append(
                EventEnvelope(
                    event_type=EventType.EXTREME_HEAT.value,
                    source="weather_feed",
                    payload={**base, "max_temperature_celsius": day.temperature_max_celsius},
                )
            )
    return events


async def run_weather_feed(
    session: AsyncSession,
    *,
    forecaster: Forecaster,
    reference: Reference,
    sink: EventSink | None,
    now: datetime | None = None,
) -> FeedResult:
    now = now or datetime.now(UTC)
    today = now.date()
    districts, missing = await feed_districts(session)
    result = FeedResult(districts=len(districts), skipped_no_coordinates=missing)
    for d in districts:
        snap = DistrictWeatherSnapshot(
            lgd_district_code=d.lgd_district_code,
            fetched_at=now,
            status="failed",
            forecast=[],
            crosscheck={},
            spray={},
            providers={},
            events_emitted=[],
        )
        try:
            fc = await forecaster.get_forecast(d.latitude, d.longitude, days=7)
        except Exception as exc:  # one district must not stop the others
            snap.error = f"forecast: {type(exc).__name__}"
            result.failed += 1
            session.add(snap)
            continue
        snap.forecast = [day.model_dump() for day in fc.forecast_days]
        snap.spray = {"favorable": fc.spray_window_favorable, "reason": fc.spray_window_reason}
        snap.providers = {"forecast": forecaster.provider_name, "summary": fc.summary}
        status = "unverified"
        try:
            mine = await forecaster.get_daily_history(d.latitude, d.longitude, HISTORY_DAYS)
            theirs = await reference.daily(
                d.latitude, d.longitude, today - timedelta(days=HISTORY_DAYS), today
            )
            check = compare(
                mine,
                theirs,
                primary_name=forecaster.provider_name,
                reference_name=reference.provider_name,
            )
            snap.crosscheck = check.to_dict()
            status = check.status
            snap.status = "ok"
            result.ok += 1
        except Exception as exc:
            snap.crosscheck = {
                "status": "unverified",
                "reasons": [f"reference unavailable ({type(exc).__name__})"],
            }
            snap.status = "partial"
            result.partial += 1
        result.crosscheck[status] = result.crosscheck.get(status, 0) + 1
        snap.providers["reference"] = reference.provider_name
        for event in events_for(d, fc.forecast_days, status, today):
            snap.events_emitted.append({"type": event.event_type, "date": event.payload["date"]})
            if sink is not None:
                try:
                    await sink(session, event)
                    result.events += 1
                except Exception as exc:
                    logger.warning("Weather event processing failed: {}", type(exc).__name__)
        session.add(snap)
    await session.flush()
    logger.info("Weather feed | {}", result.to_dict())
    return result


async def latest_snapshot(session: AsyncSession, code: int) -> DistrictWeatherSnapshot | None:
    return await session.scalar(
        select(DistrictWeatherSnapshot)
        .where(
            DistrictWeatherSnapshot.lgd_district_code == code,
            DistrictWeatherSnapshot.status != "failed",
        )
        .order_by(DistrictWeatherSnapshot.fetched_at.desc())
        .limit(1)
    )
