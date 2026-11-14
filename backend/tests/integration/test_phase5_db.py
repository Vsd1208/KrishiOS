"""Phase 5 flows against a real Postgres (see test_phase3_db.py for the setup)."""

import os
from datetime import UTC, datetime

import pytest
from app.govconnect.feeds import sachet
from sqlalchemy import select

from tests.govconnect.test_sachet import RSS, cap

pytestmark = pytest.mark.skipif(os.environ.get("KRISHIOS_INTEGRATION_DB") != "1",
                                reason="needs a migrated Postgres (KRISHIOS_INTEGRATION_DB=1)")


class FakeClient:
    def __init__(self, pages: dict[str, bytes]) -> None:
        self.pages, self.calls = pages, []

    async def fetch(self, url: str) -> bytes:
        self.calls.append(url)
        if url not in self.pages:
            import httpx  # noqa: PLC0415

            raise httpx.ConnectError("offline")
        return self.pages[url]

    async def pause(self) -> None:
        return None


async def test_sachet_poll_creates_review_bulletins_idempotently() -> None:
    from app.database.session import async_session_factory  # noqa: PLC0415
    from app.models.govconnect import GovtBulletin  # noqa: PLC0415

    base = "https://sachet.ndma.gov.in/cap_public_website/FetchXMLFile?identifier="
    unique = str(datetime.now(UTC).timestamp()).replace(".", "")
    rss = RSS.replace(b"identifier=1", f"identifier=1{unique}".encode()).replace(
        b"identifier=2", f"identifier=2{unique}".encode())
    pages = {"feed": rss,
             f"{base}1{unique}": cap(expires="2099-01-01T00:00:00+05:30"),
             f"{base}2{unique}": cap(lang="BN", expires="2099-01-01T00:00:00+05:30")}
    client = FakeClient(pages)
    async with async_session_factory() as session:
        r = await sachet.poll(session, feed_urls=["feed", "down-feed"], client=client)
        await session.commit()
        assert r.created == 1 and r.feeds_failed == 1
        assert r.skipped == {"unsupported_language:BN": 1}
        b = await session.get(GovtBulletin, r.created_ids[0])
        assert b.source_type == "feed" and b.status == "needs_review"
        assert b.district_codes == [730] and b.severity == "MEDIUM"
        assert b.authority == "India Meteorological Department (Chennai)"
        assert b.extraction["cap"]["identifier"] == "IN-1794565243439007_43"

        again = await sachet.poll(session, feed_urls=["feed"], client=client)
        await session.commit()
        assert again.created == 0 and again.already_known == 1
        n = len((await session.scalars(select(GovtBulletin).where(
            GovtBulletin.source_url == f"{base}1{unique}"))).all())
        assert n == 1
    from app.database.session import dispose_database_engine  # noqa: PLC0415

    await dispose_database_engine()  # pooled connections belong to this test's event loop


def test_sms_and_ivr_inbound_for_a_registered_farmer(client) -> None:
    from app.api.dependencies.auth import get_current_auth_context  # noqa: PLC0415
    from app.main import app  # noqa: PLC0415
    from app.models.user import UserRole  # noqa: PLC0415
    from sqlalchemy import text  # noqa: PLC0415

    from tests.integration.test_phase4_db import _engine, as_role, make_farmer  # noqa: PLC0415

    farmer = make_farmer(509, "Khammam", "te")
    with _engine().begin() as c:
        phone = c.execute(text("SELECT phone FROM farmer WHERE id=:i"),
                          {"i": farmer.farmer_id}).scalar_one()
        c.execute(text(
            "INSERT INTO district_weather_snapshot (lgd_district_code, fetched_at, status,"
            " forecast, crosscheck, spray, providers, events_emitted) VALUES (509, now(), 'ok',"
            " CAST(:f AS JSON), CAST(:c AS JSON), '{}', '{}', '[]')"),
            {"f": '[{"date": "2099-01-01", "temperature_max_celsius": 31.2,'
                  ' "temperature_min_celsius": 20, "precipitation_sum_mm": 12.4,'
                  ' "precipitation_probability_percent": 70, "max_wind_speed_mps": 2,'
                  ' "weather_condition": "Rainy"}]',
             "c": '{"status": "agree"}'})
    app.dependency_overrides[get_current_auth_context] = lambda: as_role(UserRole.OFFICER)
    try:
        weather = client.post("/api/v1/channels/sms/inbound",
                              json={"from_phone": f"+91{phone}", "text": "WEATHER"}).json()
        assert weather["action"] == "weather" and weather["reply"]["encoding"] == "ucs2"
        assert "31°C" in weather["reply"]["text"] and "మరో మూలంతో సరిచూశాం" in weather["reply"]["text"]
        alerts = client.post("/api/v1/channels/sms/inbound",
                             json={"from_phone": phone, "text": "alerts"}).json()
        assert alerts["action"] == "alerts"
        stop = client.post("/api/v1/channels/sms/inbound",
                           json={"from_phone": phone, "text": "STOP"}).json()
        assert stop["action"] == "stop"
        unknown = client.post("/api/v1/channels/sms/inbound",
                              json={"from_phone": "9000000000", "text": "help"}).json()
        assert unknown["action"] == "unknown_number"
        menu = client.post("/api/v1/channels/ivr/inbound", json={"from_phone": phone}).json()
        assert menu["action"] == "menu" and menu["language"] == "te"
        assert client.get("/api/v1/channels/sandbox/outbox").status_code == 200
    finally:
        app.dependency_overrides.clear()
    with _engine().begin() as c:
        channel = c.execute(text("SELECT preferred_channel FROM notification_preference_record"
                                 " WHERE farmer_id=:i"), {"i": farmer.farmer_id}).scalar_one()
    assert channel == "IN_APP"


async def test_trend_median_change_and_stale_guard() -> None:
    from datetime import date  # noqa: PLC0415

    from app.database.session import async_session_factory, dispose_database_engine  # noqa: PLC0415
    from app.live_data.market_history import to_rows, trend, upsert  # noqa: PLC0415

    district = f"TestDist{datetime.now(UTC).timestamp():.0f}"

    def rec(day: str, market: str, modal: int) -> dict:
        return {"State": "Telangana", "District": district, "Market": market,
                "Commodity": "Cotton", "Variety": "V", "Grade": "G", "Arrival_Date": day,
                "Modal_Price": modal}

    records = [rec("01/11/2026", "A", 8000), rec("01/11/2026", "B", 8200),
               rec("01/11/2026", "C", 9999),  # one unusual market does not move the median
               rec("08/11/2026", "A", 9000), rec("08/11/2026", "B", 9100)]
    async with async_session_factory() as session:
        await upsert(session, to_rows(records, "test", datetime.now(UTC)))
        await session.commit()
        fresh = await trend(session, crop="cotton", district=district, today=date(2026, 11, 9))
        assert [p["median_modal"] for p in fresh.points] == [8200.0, 9050.0]
        assert fresh.change_7d_pct == 10.4 and fresh.sharp and not fresh.stale
        old = await trend(session, crop="cotton", district=district, today=date(2026, 11, 30))
        assert old.stale and not old.sharp and old.days_since_latest == 22
    await dispose_database_engine()
