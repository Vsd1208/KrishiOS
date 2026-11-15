"""Yield Intelligence (Sprint 11, Phase 8): imported district yield forecasts.

Forecasts are produced offline by the ml/ batch export (model artifacts never run inside the
API), shipped as a versioned file with a manifest, and imported by the ``forecast_import``
worker job. Each row follows the YieldForecast contract (``app/forecasting/schemas.py``).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class ForecastImport(Base):
    """One imported forecast artifact (idempotent by ``model_version`` + file hash)."""

    __tablename__ = "yield_forecast_import"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    model_name: Mapped[str] = mapped_column(String(80), nullable=False)
    model_version: Mapped[str] = mapped_column(String(80), nullable=False)
    file_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    rows: Mapped[int] = mapped_column(Integer, nullable=False)
    manifest: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("model_version", "file_sha256", name="uq_forecast_import_file"),
    )


class YieldForecastRecord(Base):
    """One district x crop x season x crop year x lead forecast (or an abstention)."""

    __tablename__ = "yield_forecast"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    import_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    lgd_district_code: Mapped[int] = mapped_column(Integer, nullable=False)
    crop_canonical: Mapped[str] = mapped_column(String(64), nullable=False)
    season: Mapped[str] = mapped_column(String(20), nullable=False)
    crop_year: Mapped[int] = mapped_column(Integer, nullable=False)
    crop_tier: Mapped[str] = mapped_column(String(4), nullable=False)
    forecast_lead: Mapped[int] = mapped_column(Integer, nullable=False)
    predicted_yield: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    interval_low: Mapped[float | None] = mapped_column(Float, nullable=True)
    interval_high: Mapped[float | None] = mapped_column(Float, nullable=True)
    normal_yield: Mapped[float | None] = mapped_column(Float, nullable=True)
    available_modalities: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    missing_modalities: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    in_distribution: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    requires_human_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    abstained: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    abstain_reason: Mapped[str | None] = mapped_column(String(200), nullable=True)
    model_name: Mapped[str] = mapped_column(String(80), nullable=False)
    model_version: Mapped[str] = mapped_column(String(80), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("model_version", "lgd_district_code", "crop_canonical", "season",
                         "crop_year", "forecast_lead", name="uq_yield_forecast_row"),
        Index("ix_yield_forecast_lookup", "lgd_district_code", "crop_canonical", "season",
              "crop_year"),
    )
