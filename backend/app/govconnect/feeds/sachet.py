"""NDMA SACHET CAP feed adapter (Phase 5): official warnings → Govt Connect bulletins.

Source: ``https://sachet.ndma.gov.in/cap_public_website/rss/rss_<area>.xml`` (RSS 2.0, the feed
declares ``public domain``). Each item links to a CAP 1.2 alert. Structured CAP fields are
official and are used as-is (severity, LGD district codes, effective/expires, sender, event);
the text extractor only adds advice sentences and crops. Alerts are idempotent by CAP URL.

Fetching is polite: sequential, ``SACHET_REQUEST_INTERVAL_SECONDS`` between CAP files, a cap
on new alerts per run, and a descriptive User-Agent without personal data.
"""

from __future__ import annotations

import asyncio
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import httpx
from loguru import logger

CAP_NS = {"cap": "urn:oasis:names:tc:emergency:cap:1.2"}
USER_AGENT = "KrishiOS-GovConnect/1.0 (+agricultural advisory; CAP subscriber)"
CAP_SEVERITY = {"Minor": "LOW", "Moderate": "MEDIUM", "Severe": "HIGH", "Extreme": "CRITICAL"}
CAP_LANG = {"en": "en", "en-in": "en", "hi": "hi", "hi-in": "hi", "te": "te", "te-in": "te"}
# CAP event -> KrishiOS hazard by keyword (same rules as the benchmark, ml/scripts).
EVENT_RULES = [
    ("thunder", "thunderstorm"),
    ("lightning", "thunderstorm"),
    ("hail", "hailstorm"),
    ("cyclon", "cyclone"),
    ("flood", "flood"),
    ("heat", "heatwave"),
    ("cold", "cold_wave"),
    ("frost", "cold_wave"),
    ("fog", "fog"),
    ("squall", "strong_wind"),
    ("wind", "strong_wind"),
    ("heavy rain", "heavy_rain"),
    ("rain", "heavy_rain"),
]


def map_event(event: str) -> str | None:
    e = event.lower()
    return next((hazard for key, hazard in EVENT_RULES if key in e), None)


def authority_of(sender: str) -> tuple[str, str]:
    """('IMD-Chennai' | 'IMD Chennai') -> ('India Meteorological Department (Chennai)', level)."""
    s = sender.replace("-", " ").strip()
    if s.upper().startswith("IMD"):
        place = s[3:].strip()
        return (
            f"India Meteorological Department ({place})"
            if place
            else "India Meteorological Department",
            "state" if place else "national",
        )
    if "SDMA" in s.upper():
        return s, "state"
    if "NDMA" in s.upper():
        return "NDMA", "national"
    return s or "NDMA SACHET", "state"


@dataclass(slots=True)
class CapAlert:
    url: str
    identifier: str
    sender: str
    sent: datetime | None
    language: str | None  # en | hi | te, or None when unsupported
    raw_language: str
    event: str
    headline: str
    description: str
    instruction: str
    severity: str | None
    effective: datetime | None
    expires: datetime | None
    district_codes: list[int] = field(default_factory=list)
    area_desc: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n".join(p for p in (self.headline, self.description, self.instruction) if p)


def _t(el: ET.Element | None, path: str) -> str:
    found = el.find(path, CAP_NS) if el is not None else None
    return (found.text or "").strip() if found is not None and found.text else ""


def _dt(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value) if value else None
    except ValueError:
        return None


def parse_rss(xml: bytes) -> list[str]:
    root = ET.fromstring(xml)  # noqa: S314 - official feed; no external entities resolved
    return [
        link.strip()
        for item in root.iter("item")
        if (link := item.findtext("link")) and "identifier=" in link
    ]


def parse_cap(xml: bytes, url: str) -> CapAlert | None:
    root = ET.fromstring(xml)  # noqa: S314
    info = root.find("cap:info", CAP_NS)
    if info is None or _t(root, "cap:status") not in {"Actual", ""}:
        return None  # exercises, tests and system messages are never published
    codes: list[int] = []
    areas: list[str] = []
    for area in info.findall("cap:area", CAP_NS):
        areas.append(_t(area, "cap:areaDesc"))
        for gc in area.findall("cap:geocode", CAP_NS):
            value = _t(gc, "cap:value")
            if _t(gc, "cap:valueName") == "LGD District Code" and value.isdigit():
                codes.append(int(value))
    raw_lang = _t(info, "cap:language")
    return CapAlert(
        url=url,
        identifier=_t(root, "cap:identifier"),
        sender=_t(root, "cap:sender"),
        sent=_dt(_t(root, "cap:sent")),
        language=CAP_LANG.get(raw_lang.lower()),
        raw_language=raw_lang,
        event=_t(info, "cap:event"),
        headline=_t(info, "cap:headline"),
        description=_t(info, "cap:description"),
        instruction=_t(info, "cap:instruction"),
        severity=CAP_SEVERITY.get(_t(info, "cap:severity")),
        effective=_dt(_t(info, "cap:effective")),
        expires=_dt(_t(info, "cap:expires")),
        district_codes=sorted(set(codes)),
        area_desc=areas,
    )


class SachetClient:
    def __init__(self, *, timeout: float = 30.0, interval: float = 1.0) -> None:
        self._timeout, self._interval = timeout, interval

    async def fetch(self, url: str) -> bytes:
        async with httpx.AsyncClient(
            timeout=self._timeout, headers={"User-Agent": USER_AGENT}
        ) as client:
            r = await client.get(url)
            r.raise_for_status()
            return r.content

    async def pause(self) -> None:
        await asyncio.sleep(self._interval)


SKIP_TTL_SECONDS = 3 * 24 * 3600  # CAP alerts are short-lived; re-check after 3 days at most


class SeenCache:
    """Remembers CAP URLs already rejected (expired, no LGD code, ...) so they are not fetched
    again on every poll. Backed by Redis in the worker (any client with get/set(ex=)), or a
    process-local dict."""

    def __init__(self, redis: Any | None = None) -> None:
        self._redis = redis
        self._local: dict[str, float] = {}

    @staticmethod
    def _key(url: str) -> str:
        import hashlib  # noqa: PLC0415

        return f"krishios:sachet:skip:{hashlib.sha256(url.encode()).hexdigest()[:32]}"

    async def contains(self, url: str) -> bool:
        if self._redis is not None:
            return bool(await self._redis.get(self._key(url)))
        import time  # noqa: PLC0415

        return self._local.get(url, 0.0) > time.time()

    async def add(self, url: str, reason: str, ttl: int = SKIP_TTL_SECONDS) -> None:
        if self._redis is not None:
            await self._redis.set(self._key(url), reason, ex=ttl)
            return
        import time  # noqa: PLC0415

        self._local[url] = time.time() + ttl


@dataclass(slots=True)
class PollResult:
    feeds_ok: int = 0
    feeds_failed: int = 0
    seen: int = 0
    created: int = 0
    already_known: int = 0
    previously_skipped: int = 0
    skipped: dict[str, int] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    created_ids: list[int] = field(default_factory=list)

    def skip(self, reason: str) -> None:
        self.skipped[reason] = self.skipped.get(reason, 0) + 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "feeds_ok": self.feeds_ok,
            "feeds_failed": self.feeds_failed,
            "seen": self.seen,
            "created": self.created,
            "already_known": self.already_known,
            "previously_skipped": self.previously_skipped,
            "skipped": self.skipped,
            "errors": self.errors[:10],
        }


async def active_district_codes(session: Any) -> set[int]:
    """LGD districts where KrishiOS has farmers (registered district or saved location)."""
    from sqlalchemy import select  # noqa: PLC0415

    from app.models.district import District  # noqa: PLC0415
    from app.models.farmer import Farmer  # noqa: PLC0415
    from app.models.govconnect import FarmerLocation  # noqa: PLC0415

    registered = (
        await session.scalars(
            select(District.lgd_district_code)
            .join(Farmer, Farmer.district_id == District.id)
            .where(District.lgd_district_code.is_not(None))
            .distinct()
        )
    ).all()
    saved = (await session.scalars(select(FarmerLocation.lgd_district_code).distinct())).all()
    return {int(c) for c in [*registered, *saved] if c is not None}


async def poll(  # noqa: PLR0913 - keyword-only options
    session: Any,
    *,
    feed_urls: list[str],
    client: SachetClient | None = None,
    districts: set[int] | None = None,
    max_new: int = 50,
    seen: SeenCache | None = None,
    now: datetime | None = None,
) -> PollResult:
    """Fetch the feeds and create one bulletin per new, current, relevant CAP alert.

    ``districts``: only alerts touching these LGD districts are kept (None = all). Existing
    bulletins are recognised by CAP URL, so re-running is safe.
    """
    from sqlalchemy import select  # noqa: PLC0415

    from app.govconnect import service as svc  # noqa: PLC0415
    from app.models.govconnect import GovtBulletin  # noqa: PLC0415

    client = client or SachetClient()
    seen = seen or SeenCache()
    now = now or datetime.now(UTC)
    result = PollResult()
    links: list[str] = []
    for feed in feed_urls:
        try:
            links.extend(parse_rss(await client.fetch(feed)))
            result.feeds_ok += 1
        except (httpx.HTTPError, ET.ParseError) as exc:
            result.feeds_failed += 1
            result.errors.append(f"{feed}: {type(exc).__name__}")
    links = list(dict.fromkeys(links))  # national and state feeds overlap
    result.seen = len(links)
    known = (
        set(
            (
                await session.scalars(
                    select(GovtBulletin.source_url).where(GovtBulletin.source_url.in_(links))
                )
            ).all()
        )
        if links
        else set()
    )
    for url in links:
        if url in known:
            result.already_known += 1
            continue
        if await seen.contains(url):
            result.previously_skipped += 1
            continue
        if result.created >= max_new:
            result.skip("run_limit")
            continue
        try:
            alert = parse_cap(await client.fetch(url), url)
            await client.pause()
        except (httpx.HTTPError, ET.ParseError) as exc:
            result.errors.append(f"{url}: {type(exc).__name__}")
            continue
        reason = _skip_reason(alert, districts, now)
        if reason:
            result.skip(reason)
            # The service area grows as farmers join: re-check those after a day.
            ttl = 24 * 3600 if reason == "outside_service_area" else SKIP_TTL_SECONDS
            await seen.add(url, reason, ttl)
            continue
        try:
            b = await svc.create_bulletin(
                session,
                source_type="feed",
                body=alert.text,
                actor="system:sachet",
                overrides=_overrides(alert, districts),
            )
        except svc.GovConnectError as exc:  # e.g. an LGD code newer than our reference
            result.skip("invalid")
            result.errors.append(f"{url}: {exc.message}")
            continue
        b.extraction = {
            **b.extraction,
            "cap": {
                "identifier": alert.identifier,
                "sender": alert.sender,
                "event": alert.event,
                "raw_language": alert.raw_language,
                "area_desc": alert.area_desc,
                "sent": alert.sent.isoformat() if alert.sent else None,
            },
        }
        result.created += 1
        result.created_ids.append(b.id)
    await session.flush()
    logger.info("SACHET poll | {}", result.to_dict())
    return result


def _skip_reason(  # noqa: PLR0911 - one reason per guard
    alert: CapAlert | None, districts: set[int] | None, now: datetime
) -> str | None:
    if alert is None:
        return "not_actual"
    if not alert.district_codes:
        return "no_lgd_district"
    if alert.expires is not None and alert.expires <= now:
        return "expired"
    if alert.language is None:
        return f"unsupported_language:{alert.raw_language or 'unknown'}"
    if districts is not None and not set(alert.district_codes) & districts:
        return "outside_service_area"
    if not alert.text:
        return "empty"
    return None


def _overrides(alert: CapAlert, districts: set[int] | None) -> dict[str, Any]:
    authority, level = authority_of(alert.sender)
    codes = (
        alert.district_codes
        if districts is None
        else sorted(set(alert.district_codes) & districts) or alert.district_codes
    )
    return {
        "title": alert.headline[:300] or alert.event,
        "authority": authority,
        "authority_level": level,
        "source_name": "NDMA SACHET (CAP)",
        "source_url": alert.url,
        "issued_at": alert.sent,
        "valid_from": alert.effective or alert.sent,
        "valid_to": alert.expires,
        "severity": alert.severity,
        "hazard_type": map_event(alert.event),
        "district_codes": codes,
        "original_language": alert.language,
    }
