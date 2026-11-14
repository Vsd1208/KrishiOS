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
