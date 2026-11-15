"""Yield label audit (Phase 6): per crop-season coverage and quality, tiers, splits.

Definitions (fixed before looking at tier counts):
- **district-year**: one (LGD district, crop_year) row for a crop-season with area > 0 and a
  usable yield (reported, or production / area when only that is present).
- **missingness**: share of rows with area > 0 but no usable yield.
- **consistency failure**: reported yield differs from production / area by more than 5 %.
- **outlier**: within a district's own series (≥ 5 usable years), |robust z| of log-yield > 3.5
  (median / 1.4826·MAD), or a non-positive yield.
Tiers and splits are *proposals* for the scope freeze; thresholds come from this audit's
distributions and are never tuned on model test results (brief rule 6).
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

CONSISTENCY_TOL = 0.05
OUTLIER_Z = 3.5
MIN_SERIES_FOR_OUTLIERS = 5


def usable(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    calc = out["production"] / out["area_ha"].where(out["area_ha"] > 0)
    out["yield_calc"] = calc.replace([np.inf, -np.inf], np.nan)
    out["yield"] = out["yield_reported"].where(out["yield_reported"].notna(), out["yield_calc"])
    return out


def _robust_outliers(g: pd.DataFrame) -> pd.Series:
    y = g["yield"]
    flags = pd.Series(False, index=g.index)
    flags |= y <= 0
    pos = y[y > 0]
    if len(pos) >= MIN_SERIES_FOR_OUTLIERS:
        ly = np.log(pos)
        med = ly.median()
        dev = (ly - med).abs()
        scale = dev.median() * 1.4826
        if scale == 0:  # most years identical: fall back to the mean absolute deviation
            scale = dev.mean() * 1.2533
        if scale > 0:
            flags.loc[pos.index] |= (dev / scale) > OUTLIER_Z
    return flags


@dataclass(slots=True)
class SeriesAudit:
    crop: str
    season: str
    mapped: bool
    rows: int
    district_years: int
    years: int
    year_min: int
    year_max: int
    districts: int
    states: int
    units: str
    missing_rate: float
    consistency_fail_rate: float | None
    outlier_rate: float
    median_yield: float | None
    p05_yield: float | None
    p95_yield: float | None
    median_years_per_district: float


def audit(df: pd.DataFrame) -> list[SeriesAudit]:
    df = usable(df)
    df["crop_key"] = df["crop_canonical"].fillna("raw:" + df["crop_raw"])
    out: list[SeriesAudit] = []
    for (crop, season), g in df.groupby(["crop_key", "season"], sort=True):
        planted = g[g["area_ha"] > 0]
        ok = planted[planted["yield"].notna()]
        both = ok[ok["yield_reported"].notna() & ok["yield_calc"].notna()
                  & (ok["yield_reported"] > 0)]
        cons = None
        if len(both):
            rel = (both["yield_reported"] - both["yield_calc"]).abs() / both["yield_reported"]
            cons = round(float((rel > CONSISTENCY_TOL).mean()), 4)
        parts = [_robust_outliers(grp) for _, grp in ok.groupby("lgd_district_code")]
        flags = pd.concat(parts) if parts else pd.Series(dtype=bool)
        dy = ok.drop_duplicates(["lgd_district_code", "crop_year"])
        per_d = dy.groupby("lgd_district_code")["crop_year"].nunique()
        units = sorted({f"{p}|{y}" for p, y in zip(g["production_unit"], g["yield_unit"],
                                                   strict=False)})
        q = ok["yield"].quantile([0.05, 0.5, 0.95]) if len(ok) else None
        out.append(SeriesAudit(
            crop=crop, season=season, mapped=not crop.startswith("raw:"), rows=len(g),
            district_years=len(dy), years=int(dy["crop_year"].nunique()),
            year_min=int(dy["crop_year"].min()) if len(dy) else 0,
            year_max=int(dy["crop_year"].max()) if len(dy) else 0,
            districts=int(dy["lgd_district_code"].nunique()),
            states=int(dy["lgd_state_code"].nunique()), units="; ".join(units),
            missing_rate=round(1 - len(ok) / len(planted), 4) if len(planted) else 1.0,
            consistency_fail_rate=cons,
            outlier_rate=round(float(flags.mean()), 4) if len(flags) else 0.0,
            median_yield=round(float(q.loc[0.5]), 3) if q is not None else None,
            p05_yield=round(float(q.loc[0.05]), 3) if q is not None else None,
            p95_yield=round(float(q.loc[0.95]), 3) if q is not None else None,
            median_years_per_district=float(per_d.median()) if len(per_d) else 0.0))
    return out


@dataclass(frozen=True, slots=True)
class TierRule:
    name: str
    min_district_years: int
    min_years: int
    min_districts: int
    max_outlier_rate: float
    max_missing_rate: float


def assign_tier(s: SeriesAudit, rules: list[TierRule]) -> str:
    if not s.mapped:
        return "excluded:unmapped_crop"
    for r in rules:
        if (s.district_years >= r.min_district_years and s.years >= r.min_years
                and s.districts >= r.min_districts and s.outlier_rate <= r.max_outlier_rate
                and s.missing_rate <= r.max_missing_rate):
            return r.name
    return "excluded:insufficient"


def split_of(lgd_district_code: int, crop_year: int, *, val_from: int, test_from: int,
             spatial_share: float, seed: str = "krishios-yield-v1") -> str:
    """Time split by crop_year, plus a fixed spatial hold-out of whole districts (all crops of a
    district-year always share one split). Hash-based so it is stable and reproducible."""
    h = int(hashlib.sha256(f"{seed}:{lgd_district_code}".encode()).hexdigest()[:8], 16)
    if (h % 10_000) / 10_000 < spatial_share:
        return "spatial_test"
    if crop_year >= test_from:
        return "test"
    if crop_year >= val_from:
        return "val"
    return "train"


def to_records(items: list[SeriesAudit]) -> list[dict]:
    return [asdict(i) for i in items]
