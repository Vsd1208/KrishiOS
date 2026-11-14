"""Automated official feeds (Phase 5): NDMA SACHET warnings and the district weather feed."""

from __future__ import annotations

from typing import Any

AUTO_PUBLISH_SEVERITIES = {"LOW", "MEDIUM"}


async def sachet_poll(ctx: dict[str, Any]) -> dict[str, Any]:
    from app.config.settings import get_settings  # noqa: PLC0415
    from app.database.session import async_session_factory  # noqa: PLC0415
    from app.govconnect import service as svc  # noqa: PLC0415
    from app.govconnect.feeds.sachet import (  # noqa: PLC0415
        SachetClient,
        SeenCache,
        active_district_codes,
        poll,
    )
    from app.govconnect.indexing import get_indexer  # noqa: PLC0415
    from app.models.govconnect import GovtBulletin  # noqa: PLC0415
    from app.notifications.service import NotificationService  # noqa: PLC0415
    from app.translation.service import get_translation_service  # noqa: PLC0415

    s = get_settings()
    published: list[int] = []
    async with async_session_factory() as session:
        districts = await active_district_codes(session) if s.SACHET_SERVICE_AREA_ONLY else None
        result = await poll(
            session,
            feed_urls=s.SACHET_FEED_URLS,
            districts=districts,
            max_new=s.SACHET_MAX_NEW_PER_RUN,
            client=SachetClient(interval=s.SACHET_REQUEST_INTERVAL_SECONDS),
            seen=SeenCache(ctx.get("redis")),
        )
        if s.GOVCONNECT_FEED_AUTO_PUBLISH:
            for bid in result.created_ids:
                b = await session.get(GovtBulletin, bid)
                if b is None or b.severity not in AUTO_PUBLISH_SEVERITIES:
                    continue
                await svc.generate_translations(
                    session, b, get_translation_service(), "system:sachet"
                )
                if not svc.readiness(b, await svc.translations_of(session, b)):
                    await svc.approve(
                        session, b, "system:sachet", publish_at=None, notifier=NotificationService()
                    )
                    published.append(b.id)
        await session.commit()
    for bid in published:
        await svc.index_after_commit(bid, get_indexer())
    if result.feeds_ok == 0 and result.feeds_failed:
        raise RuntimeError(f"all SACHET feeds failed: {result.errors[:3]}")  # job health: failed
    return {
        **result.to_dict(),
        "auto_published": len(published),
        "service_area_districts": None if districts is None else len(districts),
    }


async def weather_feed(ctx: dict[str, Any]) -> dict[str, Any]:
    from app.config.settings import get_settings  # noqa: PLC0415
    from app.database.session import async_session_factory  # noqa: PLC0415
    from app.govconnect.weather_feed import run_weather_feed  # noqa: PLC0415
    from app.live_data.providers.nasa_power import NasaPowerClient  # noqa: PLC0415
    from app.live_data.providers.weather_provider import OpenMeteoWeatherProvider  # noqa: PLC0415
    from app.proactive.api.dependencies import get_event_processor  # noqa: PLC0415

    s = get_settings()
    async with async_session_factory() as session:
        processor = get_event_processor(session=session)
        result = await run_weather_feed(
            session,
            forecaster=OpenMeteoWeatherProvider(base_url=s.WEATHER_API_BASE_URL, timeout=30.0),
            reference=NasaPowerClient(),
            sink=processor.process_event,
        )
        await session.commit()
    if result.districts and result.failed == result.districts:
        raise RuntimeError("weather feed failed for every district")
    return result.to_dict()


async def mandi_history(ctx: dict[str, Any]) -> dict[str, Any]:
    """Daily: store the last few days of official prices (late reports included) and raise
    ``market.price_changed`` for sharp 7-day moves in districts with farmers."""
    from datetime import date, timedelta  # noqa: PLC0415

    from sqlalchemy import select  # noqa: PLC0415

    from app.catalog.resolver import get_crop_catalog  # noqa: PLC0415
    from app.config.settings import get_settings  # noqa: PLC0415
    from app.database.session import async_session_factory  # noqa: PLC0415
    from app.events.contracts import EventEnvelope, EventType  # noqa: PLC0415
    from app.live_data.market_history import sync_days, trend  # noqa: PLC0415
    from app.models.district import District  # noqa: PLC0415
    from app.models.farmer import Farmer  # noqa: PLC0415
    from app.models.govconnect import MandiPriceDaily  # noqa: PLC0415
    from app.proactive.api.dependencies import get_event_processor  # noqa: PLC0415

    s = get_settings()
    today = date.today()
    days = [today - timedelta(days=i) for i in range(s.MANDI_HISTORY_RECHECK_DAYS)]
    alerts = 0
    async with async_session_factory() as session:
        result = await sync_days(session, days, s.MANDI_HISTORY_STATES)
        await session.commit()
        districts = (
            await session.execute(
                select(District.district_name, District.state)
                .join(Farmer, Farmer.district_id == District.id)
                .distinct()
            )
        ).all()
        processor = get_event_processor(session=session)
        catalog = get_crop_catalog()
        for district, state in districts:
            crops = (
                await session.scalars(
                    select(MandiPriceDaily.crop_canonical)
                    .where(
                        MandiPriceDaily.district.ilike(district),
                        MandiPriceDaily.crop_canonical.is_not(None),
                        MandiPriceDaily.arrival_date >= today - timedelta(days=3),
                    )
                    .distinct()
                )
            ).all()
            for crop in crops:
                t = await trend(session, crop=crop, district=district, days=30, today=today)
                if not t.sharp or t.latest is None:
                    continue
                entry = catalog.get(crop)
                await processor.process_event(
                    session,
                    EventEnvelope(
                        event_type=EventType.MARKET_PRICE_CHANGED.value,
                        source="mandi_history",
                        payload={
                            "commodity": entry.name_en.split("(")[0].strip() if entry else crop,
                            "crop_canonical": crop,
                            "change_percent": t.change_7d_pct,
                            "current_price": t.latest["median_modal"],
                            "market": f"{district} mandis (median of {t.latest['markets']})",
                            "district": district,
                            "state": state,
                            "date": t.latest["date"],
                            "source": "AGMARKNET via data.gov.in",
                        },
                    ),
                )
                alerts += 1
        await session.commit()
    if result.failed_days and result.rows == 0:
        raise RuntimeError(f"mandi history failed: {result.failed_days[:3]}")
    return {**result.to_dict(), "alerts": alerts}
