"""Bulletin lifecycle: create → review/edit → translate → approve → (schedule) → publish →
withdraw | supersede | expire. Every step writes an audit row (``govconnect_audit``).

Translation policy (ADR-011) applies unchanged: HIGH/CRITICAL translations need an officer's
approval, lower severities need passing number/unit/term checks, and a bulletin is publishable
only when every target language is deliverable. AI never rewrites an official instruction:
only translation is applied, and the official original stays attached.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.govconnect.extraction import BulletinExtractor, as_utc, get_extractor
from app.govconnect.indexing import BulletinIndexer, chunk_metadata, prepare_document
from app.govconnect.targeting import load_targets, select_recipients
from app.models.govconnect import (
    BulletinDelivery,
    BulletinTranslation,
    GovConnectAudit,
    GovtBulletin,
)
from app.models.proactive import AlertPriority, RiskSeverity
from app.translation.checks import check_translation

EDITABLE = {"draft", "needs_review", "approved", "scheduled"}
APPROVABLE = {"draft", "needs_review"}
WITHDRAWABLE = {"approved", "scheduled", "published"}
DELIVERABLE = {"passthrough", "auto_approved", "approved"}
SEVERITIES = ("LOW", "MEDIUM", "HIGH", "CRITICAL")
REVIEW_SEVERITIES = {"HIGH", "CRITICAL"}
LEVELS = ("national", "state", "district", "block")
WEATHER_HAZARDS = {
    "heavy_rain",
    "thunderstorm",
    "hailstorm",
    "strong_wind",
    "cyclone",
    "flood",
    "heatwave",
    "cold_wave",
    "fog",
    "dry_spell",
}
_TR_RANK = {"passthrough": 0, "auto_approved": 1, "pending_review": 2, "blocked": 3}
EDITABLE_FIELDS = (
    "title",
    "body",
    "authority",
    "authority_level",
    "source_name",
    "source_url",
    "issued_at",
    "valid_from",
    "valid_to",
    "hazard_type",
    "severity",
    "district_codes",
    "block_codes",
    "crops",
    "recommended_actions",
    "target_languages",
    "segment",
    "original_language",
)


class GovConnectError(Exception):
    def __init__(self, status_code: int, message: str, reasons: list[str] | None = None) -> None:
        super().__init__(message)
        self.status_code, self.message, self.reasons = status_code, message, reasons or []


class Translator(Protocol):
    async def translate(  # noqa: PLR0913 - mirrors TranslationService.translate
        self,
        text: str,
        source_language: str,
        target_language: str,
        *,
        severity: str | None = None,
        personal_data: bool = True,
        back_translate: bool = False,
    ) -> Any: ...


class Notifier(Protocol):
    async def dispatch_alert(  # noqa: PLR0913, PLR0917 - mirrors NotificationService
        self,
        session: AsyncSession,
        farmer_id: int,
        title: str,
        message: str,
        alert_type: str,
        topic_key: str,
        severity: RiskSeverity = ...,
        priority: AlertPriority = ...,
        decision_id: int | None = None,
        requires_review: bool = False,
    ) -> Any: ...


def now_utc() -> datetime:
    return datetime.now(UTC)


def audit(session: AsyncSession, b: GovtBulletin, actor: str, action: str, **detail: Any) -> None:
    session.add(
        GovConnectAudit(
            bulletin_id=b.id, actor=actor, action=action, detail=_jsonable(detail), at=now_utc()
        )
    )


def _jsonable(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, list | tuple | set):
        return [_jsonable(v) for v in value]
    return value


def _validate(values: dict[str, Any]) -> None:
    if "severity" in values and values["severity"] not in SEVERITIES:
        raise GovConnectError(422, f"severity must be one of {SEVERITIES}")
    if "authority_level" in values and values["authority_level"] not in LEVELS:
        raise GovConnectError(422, f"authority_level must be one of {LEVELS}")
    if "target_languages" in values:
        bad = set(values["target_languages"]) - {"en", "hi", "te"}
        if bad:
            raise GovConnectError(422, f"unsupported languages {sorted(bad)}")
    if "district_codes" in values or "block_codes" in values:
        from app.catalog.lgd import get_lgd_directory  # noqa: PLC0415

        lgd = get_lgd_directory()
        for code in values.get("district_codes", []):
            if lgd.district(int(code)) is None:
                raise GovConnectError(422, f"unknown LGD district code {code}")
        for code in values.get("block_codes", []):
            if lgd.block(int(code)) is None:
                raise GovConnectError(422, f"unknown LGD block code {code}")
    if "crops" in values:
        from app.catalog.resolver import get_crop_catalog  # noqa: PLC0415

        catalog = get_crop_catalog()
        for key in values["crops"]:
            if catalog.get(key) is None:
                raise GovConnectError(422, f"unknown crop {key!r}")


def _apply_extraction(b: GovtBulletin, extraction: Any, overrides: dict[str, Any]) -> None:
    """Fill fields from the extraction; officer-supplied values always win."""
    defaults = {
        "title": extraction.value("title"),
        "original_language": extraction.value("original_language", "en"),
        "authority": extraction.value("authority"),
        "authority_level": extraction.value("authority_level", "state"),
        "issued_at": as_utc(extraction.value("issued_at")),
        "valid_from": as_utc(extraction.value("valid_from")),
        "valid_to": as_utc(extraction.value("valid_to")),
        "district_codes": extraction.value("district_codes", []),
        "block_codes": extraction.value("block_codes", []),
        "crops": extraction.value("crops", []),
        "hazard_type": extraction.value("hazard_type"),
        "severity": extraction.value("severity", "LOW"),
        "recommended_actions": extraction.value("recommended_actions", []),
    }
    for key, value in defaults.items():
        chosen = overrides.get(key, value)
        if chosen is not None:
            setattr(b, key, chosen)
    b.provenance = extraction.provenance()
    b.extraction = extraction.to_dict()


async def create_bulletin(  # noqa: PLR0913 - keyword-only inputs
    session: AsyncSession,
    *,
    source_type: str,
    body: str,
    actor: str,
    overrides: dict[str, Any] | None = None,
    file_path: str | None = None,
    file_sha256: str | None = None,
    extractor: BulletinExtractor | None = None,
) -> GovtBulletin:
    body = unicodedata.normalize("NFC", body).strip()
    if not body:
        raise GovConnectError(422, "The bulletin has no text (the file may need OCR or be empty)")
    overrides = {k: v for k, v in (overrides or {}).items() if v not in (None, "", [])}
    _validate(overrides)
    extraction = (extractor or get_extractor()).extract(body)
    b = GovtBulletin(
        source_type=source_type,
        body=body,
        file_path=file_path,
        file_sha256=file_sha256,
        title="",
        authority="",
        authority_level="state",
        original_language="en",
        severity="LOW",
        target_languages=list(get_settings().GOVCONNECT_DEFAULT_LANGUAGES),
        source_name=overrides.get("source_name"),
        source_url=overrides.get("source_url"),
        segment=overrides.get("segment") or {},
        created_by=_uuid_or_none(actor),
    )
    _apply_extraction(b, extraction, overrides)
    if "target_languages" in overrides:
        b.target_languages = overrides["target_languages"]
    b.title = (b.title or body.splitlines()[0])[:300]
    b.authority = b.authority or "Unknown authority"
    b.status = ("needs_review" if source_type in {"upload", "feed"} or extraction.low_confidence
                else "draft")
    session.add(b)
    await session.flush()
    audit(
        session,
        b,
        actor,
        "created",
        source_type=source_type,
        extractor=extraction.extractor,
        low_confidence=extraction.low_confidence,
        officer_fields=sorted(overrides),
    )
    return b


def _uuid_or_none(actor: str) -> Any:
    from uuid import UUID  # noqa: PLC0415

    try:
        return UUID(actor)
    except ValueError:
        return None


async def update_bulletin(
    session: AsyncSession, b: GovtBulletin, changes: dict[str, Any], actor: str
) -> GovtBulletin:
    if b.status not in EDITABLE:
        raise GovConnectError(409, f"A {b.status} bulletin cannot be edited; supersede it instead")
    changes = {k: v for k, v in changes.items() if k in EDITABLE_FIELDS}
    _validate(changes)
    changed = sorted(k for k, v in changes.items() if getattr(b, k) != v)
    if not changed:
        return b
    for key in changed:
        value = changes[key]
        if key == "body":
            value = unicodedata.normalize("NFC", value).strip()
        setattr(b, key, value)
    if "body" in changed:  # offsets moved: refresh provenance, keep officer-set fields
        extraction = get_extractor().extract(b.body)
        b.provenance = extraction.provenance()
        b.extraction = {**extraction.to_dict(), "refreshed_after_edit": True}
    if changed and set(changed) & {
        "title",
        "body",
        "severity",
        "target_languages",
        "original_language",
    }:
        for t in await translations_of(session, b):
            await session.delete(t)  # stale; regenerate before approval
    if b.status in {"approved", "scheduled"}:
        b.status = "needs_review"
        b.approved_by = b.approved_at = b.publish_at = None
    audit(session, b, actor, "edited", fields=changed)
    await session.flush()
    return b


async def translations_of(session: AsyncSession, b: GovtBulletin) -> list[BulletinTranslation]:
    return list(
        (
            await session.scalars(
                select(BulletinTranslation).where(BulletinTranslation.bulletin_id == b.id)
            )
        ).all()
    )


async def generate_translations(
    session: AsyncSession, b: GovtBulletin, translator: Translator, actor: str
) -> list[BulletinTranslation]:
    if b.status not in EDITABLE:
        raise GovConnectError(409, f"Cannot translate a {b.status} bulletin")
    existing = {t.language: t for t in await translations_of(session, b)}
    review = b.severity in REVIEW_SEVERITIES
    summary: dict[str, str] = {}
    for lang in b.target_languages:
        row = existing.get(lang) or BulletinTranslation(
            bulletin_id=b.id, language=lang, title="", body="", status="blocked"
        )
        if lang == b.original_language:
            row.title, row.body, row.status, row.provider = b.title, b.body, "passthrough", None
            row.check_issues, row.back_translation = [], None
        else:
            outs = [
                await translator.translate(
                    text,
                    b.original_language,
                    lang,
                    severity=b.severity,
                    personal_data=False,
                    back_translate=review,
                )
                for text in (b.title, b.body)
            ]
            status = max((str(o.status) for o in outs), key=lambda s: _TR_RANK.get(s, 3))
            row.title, row.body = outs[0].text, outs[1].text
            row.status = status
            row.provider = outs[1].provider
            row.check_issues = [r for o in outs for r in o.checks.reasons]
            row.back_translation = outs[1].back_translation
        row.approved_by = row.approved_at = None
        if row.id is None:
            session.add(row)
        summary[lang] = row.status
    await session.flush()
    audit(session, b, actor, "translated", statuses=summary)
    return await translations_of(session, b)


async def approve_translation(  # noqa: PLR0913, PLR0917
    session: AsyncSession,
    b: GovtBulletin,
    language: str,
    actor: str,
    title: str | None = None,
    body: str | None = None,
) -> BulletinTranslation:
    row = next((t for t in await translations_of(session, b) if t.language == language), None)
    if row is None:
        raise GovConnectError(404, f"No {language} translation; generate translations first")
    new_title, new_body = title or row.title, body or row.body
    reasons = [
        *check_translation(b.title, new_title).reasons,
        *check_translation(b.body, new_body).reasons,
    ]
    if reasons:
        raise GovConnectError(422, "The translation fails the number/unit/term checks", reasons)
    edited = (new_title, new_body) != (row.title, row.body)
    row.title, row.body, row.status, row.check_issues = new_title, new_body, "approved", []
    row.approved_by, row.approved_at = _uuid_or_none(actor), now_utc()
    await session.flush()
    audit(session, b, actor, "translation_approved", language=language, edited=edited)
    return row


def readiness(
    b: GovtBulletin, translations: list[BulletinTranslation], now: datetime | None = None
) -> list[str]:
    now = now or now_utc()
    problems = []
    if not b.title.strip() or not b.body.strip():
        problems.append("title and text are required")
    if not b.authority or b.authority == "Unknown authority":
        problems.append("issuing authority is required")
    if b.valid_to is None:
        problems.append("valid_to is required (bulletins must expire)")
    elif _aware(b.valid_to) <= now:
        problems.append("valid_to is in the past")
    if not b.district_codes:
        problems.append("at least one target district is required")
    if not b.target_languages:
        problems.append("at least one target language is required")
    by_lang = {t.language: t for t in translations}
    for lang in b.target_languages:
        t = by_lang.get(lang)
        if t is None:
            problems.append(f"{lang}: translation missing")
        elif t.status not in DELIVERABLE:
            problems.append(f"{lang}: translation {t.status} (needs officer approval)")
    return problems


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)


async def approve(
    session: AsyncSession,
    b: GovtBulletin,
    actor: str,
    *,
    publish_at: datetime | None,
    notifier: Notifier,
) -> dict[str, Any]:
    if b.status not in APPROVABLE:
        raise GovConnectError(409, f"A {b.status} bulletin cannot be approved")
    problems = readiness(b, await translations_of(session, b))
    if problems:
        raise GovConnectError(422, "The bulletin is not ready to publish", problems)
    now = now_utc()
    b.approved_by, b.approved_at = _uuid_or_none(actor), now
    b.publish_at = _aware(publish_at) if publish_at else now
    b.status = "approved"
    audit(session, b, actor, "approved", publish_at=b.publish_at)
    if b.publish_at <= now:
        return await publish(session, b, notifier=notifier, actor=actor)
    b.status = "scheduled"
    audit(session, b, actor, "scheduled", publish_at=b.publish_at)
    await session.flush()
    return {"status": b.status, "publish_at": b.publish_at.isoformat()}


def _alert_type(b: GovtBulletin) -> str:
    hazard = b.hazard_type or "advisory"
    if hazard in WEATHER_HAZARDS:
        return f"weather.govt.{hazard}"  # honours the farmer's weather-alert toggle
    if hazard in {"pest_outbreak", "disease_outbreak"}:
        return f"agronomy.govt.{hazard}"
    return f"govt.{hazard}"


def _priority(severity: str) -> AlertPriority:
    if severity == "CRITICAL":
        return (
            AlertPriority.URGENT
            if get_settings().GOVCONNECT_CRITICAL_BYPASS_QUIET_HOURS
            else AlertPriority.HIGH
        )
    return {"HIGH": AlertPriority.HIGH, "MEDIUM": AlertPriority.NORMAL}.get(
        severity, AlertPriority.LOW
    )


async def _active_overlaps(
    session: AsyncSession, b: GovtBulletin, farmer_ids: list[int], exclude: set[int], now: datetime
) -> set[int]:
    """Farmers who already hold an active, unexpired bulletin of the same hazard for an
    overlapping district: they get the new one in the inbox but no second notification."""
    if not b.hazard_type or not farmer_ids:
        return set()
    rows = (
        await session.execute(
            select(BulletinDelivery.farmer_id, GovtBulletin.district_codes, GovtBulletin.valid_to)
            .join(GovtBulletin, GovtBulletin.id == BulletinDelivery.bulletin_id)
            .where(
                GovtBulletin.status == "published",
                GovtBulletin.hazard_type == b.hazard_type,
                BulletinDelivery.farmer_id.in_(farmer_ids),
                GovtBulletin.id.not_in(exclude or {-1}),
            )
        )
    ).all()
    mine = set(b.district_codes)
    return {
        fid
        for fid, codes, valid_to in rows
        if valid_to is not None and _aware(valid_to) > now and mine & set(codes or [])
    }


@dataclass(slots=True)
class PublishCounts:
    recipients: int = 0
    notified: int = 0
    suppressed: int = 0
    deduplicated: int = 0
    failed: int = 0


async def publish(
    session: AsyncSession,
    b: GovtBulletin,
    *,
    notifier: Notifier,
    actor: str = "system",
    now: datetime | None = None,
) -> dict[str, Any]:
    if b.status not in {"approved", "scheduled"}:
        raise GovConnectError(409, f"A {b.status} bulletin cannot be published")
    now = now or now_utc()
    translations = {
        t.language: t for t in await translations_of(session, b) if t.status in DELIVERABLE
    }
    farmers = await load_targets(session, b.district_codes)
    recipients = select_recipients(
        farmers,
        district_codes=b.district_codes,
        block_codes=b.block_codes,
        crops=b.crops,
        segment=b.segment or {},
        available_languages=set(translations),
        original_language=b.original_language,
    )
    superseded = await session.get(GovtBulletin, b.supersedes_id) if b.supersedes_id else None
    exclude = {b.id} | ({superseded.id} if superseded else set())
    dupes = await _active_overlaps(session, b, [r.farmer_id for r in recipients], exclude, now)
    counts = PublishCounts(recipients=len(recipients))
    by_lang: dict[str, int] = {}
    for r in recipients:
        tr = translations.get(r.language) or translations.get(b.original_language)
        if tr is None:
            counts.failed += 1
            continue
        by_lang[tr.language] = by_lang.get(tr.language, 0) + 1
        delivery = BulletinDelivery(
            bulletin_id=b.id,
            farmer_id=r.farmer_id,
            language=tr.language,
            match_level=r.match_level,
            notification_status="deduplicated",
        )
        if r.farmer_id in dupes:
            counts.deduplicated += 1
        else:
            try:
                record = await notifier.dispatch_alert(
                    session,
                    r.farmer_id,
                    title=f"{b.authority}: {tr.title}"[:255],
                    message=tr.body,
                    alert_type=_alert_type(b),
                    topic_key=f"govt:{b.uuid}",
                    severity=RiskSeverity(b.severity),
                    priority=_priority(b.severity),
                )
                status = str(getattr(record.status, "value", record.status)).lower()
                note = (getattr(record, "review_note", None) or "").lower()
                if "suppress" in note or "disabled" in note:
                    delivery.notification_status = "suppressed"
                    counts.suppressed += 1
                elif status == "sent":
                    delivery.notification_status = "sent"
                    delivery.alert_uuid = record.uuid
                    counts.notified += 1
                else:
                    delivery.notification_status = "failed"
                    counts.failed += 1
            except Exception as exc:
                logger.warning(
                    "Bulletin notification failed for farmer {}: {}",
                    r.farmer_id,
                    type(exc).__name__,
                )
                delivery.notification_status = "failed"
                counts.failed += 1
        session.add(delivery)
    b.status, b.published_at = "published", now
    doc_id = await prepare_document(session, b, list(translations.values()))
    b.knowledge_document_id, b.index_state = doc_id, "pending"
    if superseded is not None and superseded.status == "published":
        superseded.status = "superseded"
        audit(session, superseded, actor, "superseded", by=str(b.uuid))
    detail = {
        "recipients": counts.recipients,
        "notified": counts.notified,
        "suppressed": counts.suppressed,
        "deduplicated": counts.deduplicated,
        "failed": counts.failed,
        "by_language": by_lang,
    }
    audit(session, b, actor, "published", **detail)
    await session.flush()
    return {"status": b.status, **detail}


async def withdraw(
    session: AsyncSession, b: GovtBulletin, reason: str, actor: str, indexer: BulletinIndexer
) -> GovtBulletin:
    if b.status not in WITHDRAWABLE:
        raise GovConnectError(409, f"A {b.status} bulletin cannot be withdrawn")
    if not reason.strip():
        raise GovConnectError(422, "A withdrawal reason is required")
    b.status, b.withdrawn_at, b.withdrawn_reason = "withdrawn", now_utc(), reason.strip()
    await expire_index(session, b, indexer)
    audit(session, b, actor, "withdrawn", reason=b.withdrawn_reason)
    await session.flush()
    return b


async def expire_index(session: AsyncSession, b: GovtBulletin, indexer: BulletinIndexer) -> None:
    if b.knowledge_document_id is None:
        b.index_state = "expired"
        return
    ok = await indexer.expire(session, b.knowledge_document_id, now_utc())
    b.index_state = "expired" if ok else "failed"


async def start_supersession(session: AsyncSession, b: GovtBulletin, actor: str) -> GovtBulletin:
    if b.status != "published":
        raise GovConnectError(409, "Only a published bulletin can be superseded")
    new = GovtBulletin(
        status="draft",
        source_type=b.source_type,
        source_name=b.source_name,
        source_url=b.source_url,
        file_path=b.file_path,
        file_sha256=b.file_sha256,
        **{
            k: getattr(b, k)
            for k in (
                "authority",
                "authority_level",
                "title",
                "body",
                "original_language",
                "issued_at",
                "valid_from",
                "valid_to",
                "hazard_type",
                "severity",
            )
        },
        district_codes=list(b.district_codes),
        block_codes=list(b.block_codes),
        crops=list(b.crops),
        recommended_actions=list(b.recommended_actions),
        target_languages=list(b.target_languages),
        segment=dict(b.segment or {}),
        provenance=dict(b.provenance or {}),
        extraction=dict(b.extraction or {}),
        supersedes_id=b.id,
        created_by=_uuid_or_none(actor),
    )
    session.add(new)
    await session.flush()
    audit(session, new, actor, "created", source_type="supersession", supersedes=str(b.uuid))
    audit(session, b, actor, "supersession_started", draft=str(new.uuid))
    return new


async def run_maintenance(
    session: AsyncSession,
    *,
    notifier: Notifier,
    indexer: BulletinIndexer,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Publish due scheduled bulletins, expire old ones, retry failed index expiry.
    Idempotent: each step only touches rows still in the triggering state."""
    now = now or now_utc()
    out = {"published": 0, "expired": 0, "index_expired": 0, "to_index": []}
    due = (
        await session.scalars(
            select(GovtBulletin).where(
                GovtBulletin.status == "scheduled", GovtBulletin.publish_at <= now
            )
        )
    ).all()
    for b in due:
        await publish(session, b, notifier=notifier, now=now)
        out["published"] += 1
        out["to_index"].append(b.id)
    old = (
        await session.scalars(
            select(GovtBulletin).where(
                GovtBulletin.status == "published", GovtBulletin.valid_to <= now
            )
        )
    ).all()
    for b in old:
        b.status = "expired"
        audit(session, b, "system", "expired")
        out["expired"] += 1
    stuck = (
        await session.scalars(
            select(GovtBulletin).where(
                GovtBulletin.status.in_(["withdrawn", "superseded"]),
                GovtBulletin.index_state.in_(["pending", "indexed", "failed"]),
            )
        )
    ).all()
    for b in stuck:
        await expire_index(session, b, indexer)
        out["index_expired"] += int(b.index_state == "expired")
    retry = (
        await session.scalars(
            select(GovtBulletin.id).where(
                GovtBulletin.status == "published", GovtBulletin.index_state == "failed"
            )
        )
    ).all()
    out["to_index"].extend(retry)
    await session.flush()
    return out


async def index_after_commit(bulletin_id: int, indexer: BulletinIndexer) -> bool:
    """Run RAG indexing for a committed, published bulletin (own session)."""
    from app.database.session import async_session_factory  # noqa: PLC0415

    async with async_session_factory() as session:
        b = await session.get(GovtBulletin, bulletin_id)
        if b is None or b.knowledge_document_id is None or b.status != "published":
            return False
        superseded = await session.get(GovtBulletin, b.supersedes_id) if b.supersedes_id else None
        metadata = chunk_metadata(b, str(superseded.uuid) if superseded else None)
        doc_id = b.knowledge_document_id
        await session.commit()
        ok = await indexer.index(doc_id, metadata)
        b = await session.get(GovtBulletin, bulletin_id)
        if b is not None:
            b.index_state = "indexed" if ok else "failed"
            audit(session, b, "system", "indexed" if ok else "index_failed")
            if superseded is not None:
                sup = await session.get(GovtBulletin, superseded.id)
                if sup is not None and sup.index_state not in {"expired"}:
                    await expire_index(session, sup, indexer)
            await session.commit()
        return ok
