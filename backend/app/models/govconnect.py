"""Govt–Farmer Connect (Sprint 11, Phase 4): bulletins, translations, delivery, audit,
saved farmer locations (F2), grievance tickets and the scheme catalog (F4)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.base import TimestampMixin


class GovtBulletin(TimestampMixin, Base):
    """An official instruction or warning, from officer upload, composition or (Phase 5) a feed.

    ``body`` is the official text in ``original_language`` (NFC-normalised so provenance
    character offsets stay valid). ``provenance`` maps each extracted field to the source
    spans it came from. Lifecycle: draft → needs_review → approved → scheduled → published →
    (withdrawn | superseded | expired).
    """

    __tablename__ = "govt_bulletin"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    uuid: Mapped[UUID] = mapped_column(default=uuid4, unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft", index=True)
    source_type: Mapped[str] = mapped_column(String(16), nullable=False)  # upload|composed|feed
    source_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    authority: Mapped[str] = mapped_column(String(200), nullable=False)
    authority_level: Mapped[str] = mapped_column(String(16), nullable=False)  # national..block
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    original_language: Mapped[str] = mapped_column(String(8), nullable=False)
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True,
                                                      index=True)
    hazard_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    severity: Mapped[str] = mapped_column(String(10), nullable=False, default="LOW")
    district_codes: Mapped[list[int]] = mapped_column(JSON, nullable=False, default=list)
    block_codes: Mapped[list[int]] = mapped_column(JSON, nullable=False, default=list)
    crops: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    recommended_actions: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    target_languages: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    segment: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    provenance: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    extraction: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    supersedes_id: Mapped[int | None] = mapped_column(
        ForeignKey("govt_bulletin.id", ondelete="SET NULL"), nullable=True)
    knowledge_document_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # RAG state: pending | indexed | expired | failed (the maintenance job retries failures)
    index_state: Mapped[str | None] = mapped_column(String(10), nullable=True)
    created_by: Mapped[UUID | None] = mapped_column(nullable=True)
    approved_by: Mapped[UUID | None] = mapped_column(nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    publish_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    withdrawn_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class BulletinTranslation(TimestampMixin, Base):
    """The bulletin text in one target language. ``status`` is the translation-policy outcome
    (passthrough | auto_approved | pending_review | blocked | approved); delivery needs
    passthrough, auto_approved or approved."""

    __tablename__ = "govt_bulletin_translation"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    bulletin_id: Mapped[int] = mapped_column(
        ForeignKey("govt_bulletin.id", ondelete="CASCADE"), nullable=False)
    language: Mapped[str] = mapped_column(String(8), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    check_issues: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    back_translation: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_by: Mapped[UUID | None] = mapped_column(nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (UniqueConstraint("bulletin_id", "language", name="uq_bulletin_language"),)


class BulletinDelivery(TimestampMixin, Base):
    """One farmer's copy of a published bulletin (the inbox row)."""

    __tablename__ = "govt_bulletin_delivery"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    bulletin_id: Mapped[int] = mapped_column(
        ForeignKey("govt_bulletin.id", ondelete="CASCADE"), nullable=False)
    farmer_id: Mapped[int] = mapped_column(ForeignKey("farmer.id", ondelete="CASCADE"),
                                           nullable=False)
    language: Mapped[str] = mapped_column(String(8), nullable=False)
    match_level: Mapped[str] = mapped_column(String(10), nullable=False)  # block|district|all
    notification_status: Mapped[str] = mapped_column(String(16), nullable=False)
    alert_uuid: Mapped[UUID | None] = mapped_column(nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True),
                                                             nullable=True)
    flag_reason: Mapped[str | None] = mapped_column(String(32), nullable=True)
    flag_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    flagged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    flag_status: Mapped[str | None] = mapped_column(String(16), nullable=True)

    __table_args__ = (
        UniqueConstraint("bulletin_id", "farmer_id", name="uq_delivery_bulletin_farmer"),
        Index("ix_delivery_farmer", "farmer_id"),
    )


class GovConnectAudit(Base):
    """Append-only audit trail of every officer and system action on a bulletin."""

    __tablename__ = "govconnect_audit"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    bulletin_id: Mapped[int] = mapped_column(
        ForeignKey("govt_bulletin.id", ondelete="CASCADE"), nullable=False, index=True)
    actor: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    detail: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class FarmerLocation(TimestampMixin, Base):
    """A saved place (field, village) with LGD district and, when known, block (F2)."""

    __tablename__ = "farmer_location"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    farmer_id: Mapped[int] = mapped_column(ForeignKey("farmer.id", ondelete="CASCADE"),
                                           nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    lgd_district_code: Mapped[int] = mapped_column(Integer, nullable=False)
    lgd_block_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    village: Mapped[str | None] = mapped_column(String(150), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_primary: Mapped[bool] = mapped_column(default=False, nullable=False)


class GrievanceTicket(TimestampMixin, Base):
    """A farmer grievance (F4): open → assigned → in_progress → resolved | rejected → closed."""

    __tablename__ = "grievance_ticket"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    uuid: Mapped[UUID] = mapped_column(default=uuid4, unique=True, nullable=False)
    farmer_id: Mapped[int] = mapped_column(ForeignKey("farmer.id", ondelete="CASCADE"),
                                           nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(8), nullable=False)
    lgd_district_code: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    scheme_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="open", index=True)
    priority: Mapped[str] = mapped_column(String(8), nullable=False, default="normal")
    assigned_to: Mapped[UUID | None] = mapped_column(nullable=True)
    sla_due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    first_response_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True),
                                                               nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class GrievanceEvent(Base):
    """Status change or note on a ticket; ``public`` notes are shown to the farmer."""

    __tablename__ = "grievance_event"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(
        ForeignKey("grievance_ticket.id", ondelete="CASCADE"), nullable=False, index=True)
    actor: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    public: Mapped[bool] = mapped_column(default=True, nullable=False)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SchemeEntry(TimestampMixin, Base):
    """Officer-maintained scheme catalog entry (F4). Only ``verified`` entries are shown to
    farmers or used by the bot. ``criteria`` are machine-checkable eligibility rules, each with
    a question (en/hi/te) and the source it comes from; nothing is scraped."""

    __tablename__ = "scheme_entry"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    names: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False)  # {en, hi, te}
    authority: Mapped[str] = mapped_column(String(200), nullable=False)
    scope: Mapped[str] = mapped_column(String(16), nullable=False)  # central | state
    state_codes: Mapped[list[int]] = mapped_column(JSON, nullable=False, default=list)
    summary: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False)
    benefits: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False, default=dict)
    criteria: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    status_lookup_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    verified_by: Mapped[UUID | None] = mapped_column(nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DistrictWeatherSnapshot(Base):
    """One run of the district weather feed (Phase 5): the forecast, the cross-check against an
    independent source, and which providers answered. The latest row per district backs the
    dashboard weather feed; the history gives freshness and job-reliability numbers."""

    __tablename__ = "district_weather_snapshot"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    lgd_district_code: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False,
                                                 index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)  # ok | partial | failed
    forecast: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    crosscheck: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    spray: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    providers: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    events_emitted: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False,
                                                                 default=list)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class PushSubscription(TimestampMixin, Base):
    """A browser Web Push subscription for a farmer (Phase 5). Payloads are end-to-end
    encrypted to the browser's keys; the push service cannot read them."""

    __tablename__ = "push_subscription"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    farmer_id: Mapped[int] = mapped_column(ForeignKey("farmer.id", ondelete="CASCADE"),
                                           nullable=False, index=True)
    endpoint: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    p256dh: Mapped[str] = mapped_column(String(255), nullable=False)
    auth: Mapped[str] = mapped_column(String(255), nullable=False)
    failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True),
                                                             nullable=True)
