# ruff: noqa: E501 - the CAP fixture is a verbatim official alert
"""NDMA SACHET CAP adapter: parsing and polling rules (no network, no database)."""

from datetime import UTC, datetime

from app.govconnect.feeds import sachet

RSS = b"""<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel>
<item><title>a</title><link>https://sachet.ndma.gov.in/cap_public_website/FetchXMLFile?identifier=1</link></item>
<item><title>b</title><link>https://sachet.ndma.gov.in/cap_public_website/FetchXMLFile?identifier=2</link></item>
</channel></rss>"""

# Real public-domain CAP alert (IMD Chennai, 2026-11-13), trimmed.
CAP = """<cap:alert xmlns:cap="urn:oasis:names:tc:emergency:cap:1.2">
<cap:identifier>IN-1794565243439007_43</cap:identifier><cap:sender>IMD-Chennai</cap:sender>
<cap:sent>2026-11-13T15:50:15+05:30</cap:sent><cap:status>{status}</cap:status>
<cap:info><cap:language>{lang}</cap:language><cap:category>Met</cap:category>
<cap:event>Moderate Rain</cap:event><cap:severity>Moderate</cap:severity>
<cap:effective>2026-11-13T16:00:00+05:30</cap:effective>
<cap:expires>{expires}</cap:expires>
<cap:headline>Light to Moderate Rain is very likely to occur at isolated places over Chengalpattu in next 3 hours.</cap:headline>
<cap:description/><cap:instruction>Please follow SDMA guidelines.</cap:instruction>
<cap:area><cap:areaDesc>Chengalpattu district of Tamil Nadu</cap:areaDesc>
<cap:geocode><cap:valueName>LGD District Code</cap:valueName><cap:value>730</cap:value></cap:geocode>
</cap:area></cap:info></cap:alert>"""


def cap(status="Actual", lang="en-IN", expires="2026-11-13T19:00:00+05:30") -> bytes:
    return CAP.format(status=status, lang=lang, expires=expires).encode()


def test_parse_cap_uses_official_structured_fields() -> None:
    a = sachet.parse_cap(cap(), "u")
    assert a is not None
    assert a.district_codes == [730] and a.severity == "MEDIUM" and a.language == "en"
    assert a.expires.isoformat() == "2026-11-13T19:00:00+05:30"
    assert sachet.map_event(a.event) == "heavy_rain"
    assert sachet.authority_of(a.sender) == ("India Meteorological Department (Chennai)", "state")
    assert sachet.parse_cap(cap(status="Exercise"), "u") is None  # never publish drills
    assert sachet.parse_rss(RSS)[1].endswith("identifier=2")


def test_skip_rules() -> None:
    now = datetime(2026, 11, 13, 12, 0, tzinfo=UTC)
    ok = sachet.parse_cap(cap(), "u")
    assert sachet._skip_reason(ok, None, now) is None
    assert sachet._skip_reason(ok, {509}, now) == "outside_service_area"
    expired = sachet.parse_cap(cap(expires="2026-11-13T10:00:00+05:30"), "u")
    assert sachet._skip_reason(expired, None, now) == "expired"
    bengali = sachet.parse_cap(cap(lang="BN"), "u")
    assert sachet._skip_reason(bengali, None, now) == "unsupported_language:BN"
    o = sachet._overrides(ok, None)
    assert o["district_codes"] == [730] and o["severity"] == "MEDIUM"
    assert o["source_name"] == "NDMA SACHET (CAP)" and o["valid_to"] == ok.expires


async def test_seen_cache_skips_refetching_rejected_alerts() -> None:
    class FakeRedis:
        def __init__(self) -> None:
            self.data = {}

        async def get(self, k):
            return self.data.get(k)

        async def set(self, k, v, ex=None):
            self.data[k] = (v, ex)

    redis = FakeRedis()
    cache = sachet.SeenCache(redis)
    assert not await cache.contains("u")
    await cache.add("u", "expired")
    assert await cache.contains("u")
    assert next(iter(redis.data.values())) == ("expired", sachet.SKIP_TTL_SECONDS)
    local = sachet.SeenCache()
    await local.add("v", "expired")
    assert await local.contains("v") and not await local.contains("w")
