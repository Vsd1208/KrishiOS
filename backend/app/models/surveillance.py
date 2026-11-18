"""F8 crowdsourced outbreak surveillance (Sprint 11, Phase 9).

One row per photo diagnosis that has a district. Privacy by design (DPDP): no image, no GPS,
no user id; the reporter is a salted hash so one farmer counts once per district x crop x
condition x week. Rows are model findings (possibilities), never confirmed diagnoses.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class DiagnosisReport(Base):
    __tablename__ = "diagnosis_report"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    reported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    week_start: Mapped[date] = mapped_column(Date, nullable=False)
    lgd_district_code: Mapped[int] = mapped_column(Integer, nullable=False)
    crop_canonical: Mapped[str] = mapped_column(String(64), nullable=False)
    condition: Mapped[str] = mapped_column(String(80), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    crop_confirmed_by_farmer: Mapped[bool] = mapped_column(Boolean, nullable=False)
    model_version: Mapped[str] = mapped_column(String(80), nullable=False)
    reporter_hash: Mapped[str] = mapped_column(String(32), nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="photo_turn")

    __table_args__ = (
        UniqueConstraint("week_start", "lgd_district_code", "crop_canonical", "condition",
                         "reporter_hash", name="uq_diagnosis_report_weekly"),
        Index("ix_diagnosis_report_week_district", "week_start", "lgd_district_code"),
    )
