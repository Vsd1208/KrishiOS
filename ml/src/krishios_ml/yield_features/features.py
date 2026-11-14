"""Season-window weather features with forecast lead times (Phase 7).

For an APY crop_year Y and a season, the window starts at the season anchor (draft calendar,
``reference/crop_calendar.csv``): Kharif 1 Jun Y, Rabi 1 Oct Y, Zaid 1 Mar Y+1, Whole Year
1 Jun Y. A forecast at lead L days uses only days in ``[anchor - PRE_DAYS, anchor + L)``:
nothing on or after the cutoff can enter a feature (tested in tests/test_yield_features.py).

Features are raw district values (no anomalies, no scaling): climatologies, scalers and
imputers are fitted on the training split only, at model time (Phase 8), to avoid leakage.
Missing inputs stay missing; ``*_coverage`` columns record the share of days with data.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np
import pandas as pd

PRE_DAYS = 60
LEADS = (0, 30, 60, 90)
ANCHORS = {"Kharif": (6, 1, 0), "Rabi": (10, 1, 0), "Zaid": (3, 1, 1), "Whole Year": (6, 1, 0)}
RAIN_DAY_MM = 2.5
HEAT_C = 35.0
GDD_BASE, GDD_CAP = 10.0, 35.0


def anchor(season: str, crop_year: int) -> date:
    month, day, offset = ANCHORS[season]
    return date(crop_year + offset, month, day)


@dataclass(frozen=True, slots=True)
class Window:
    start: date
    cutoff: date  # exclusive


def window(season: str, crop_year: int, lead_days: int) -> Window:
    a = anchor(season, crop_year)
    return Window(a - timedelta(days=PRE_DAYS), a + timedelta(days=lead_days))


def _max_run(mask: np.ndarray) -> int:
    best = run = 0
    for v in mask:
        run = run + 1 if v else 0
        best = max(best, run)
    return best


def summarise(days: pd.DataFrame, expected_days: int) -> dict[str, float]:
    """``days``: one district's rows inside the window (date, PRECTOTCORR, T2M_MAX, ...)."""
    rain = days["PRECTOTCORR"].to_numpy(dtype="float64")
    tmax = days["T2M_MAX"].to_numpy(dtype="float64")
    tmin = days["T2M_MIN"].to_numpy(dtype="float64")
    out: dict[str, float] = {}
    ok = np.isfinite(rain)
    out["rain_sum"] = float(np.nansum(rain)) if ok.any() else np.nan
    out["rain_days"] = float((rain[ok] >= RAIN_DAY_MM).sum()) if ok.any() else np.nan
    out["max_dry_spell"] = float(_max_run(ok & (np.nan_to_num(rain) < 1.0))) if ok.any() else np.nan
    out["rain_coverage"] = float(ok.sum() / expected_days) if expected_days else np.nan
    t_ok = np.isfinite(tmax) & np.isfinite(tmin)
    out["tmax_mean"] = float(np.nanmean(tmax)) if np.isfinite(tmax).any() else np.nan
    out["tmin_mean"] = float(np.nanmean(tmin)) if np.isfinite(tmin).any() else np.nan
    out["heat_days"] = (
        float((tmax[np.isfinite(tmax)] >= HEAT_C).sum()) if np.isfinite(tmax).any() else np.nan
    )
    if t_ok.any():
        tmean = (np.clip(tmax[t_ok], None, GDD_CAP) + tmin[t_ok]) / 2
        out["gdd"] = float(np.clip(tmean - GDD_BASE, 0, None).sum())
    else:
        out["gdd"] = np.nan
    out["temp_coverage"] = float(t_ok.sum() / expected_days) if expected_days else np.nan
    for col, name in (("RH2M", "rh_mean"), ("ALLSKY_SFC_SW_DWN", "srad_mean")):
        v = days[col].to_numpy(dtype="float64") if col in days else np.array([])
        out[name] = float(np.nanmean(v)) if np.isfinite(v).any() else np.nan
        out[f"{name}_coverage"] = (
            float(np.isfinite(v).sum() / expected_days) if expected_days else np.nan
        )
    return out


def build(daily: pd.DataFrame, labels: pd.DataFrame, leads=LEADS) -> pd.DataFrame:
    """One row per (district, crop_year, season, lead). ``labels`` supplies the keys only."""
    keys = labels[["lgd_district_code", "crop_year", "season"]].drop_duplicates()
    daily = daily.copy()
    daily["date"] = pd.to_datetime(daily["date"]).dt.date
    by_district = {
        k: g.set_index("date").sort_index() for k, g in daily.groupby("lgd_district_code")
    }
    rows = []
    for d_code, year, season in keys.itertuples(index=False):
        g = by_district.get(int(d_code))
        for lead in leads:
            w = window(season, int(year), lead)
            row = {
                "lgd_district_code": int(d_code),
                "crop_year": int(year),
                "season": season,
                "lead_days": lead,
                "window_start": w.start,
                "cutoff": w.cutoff,
            }
            if g is None:
                row["has_weather"] = False
            else:
                part = g.loc[(g.index >= w.start) & (g.index < w.cutoff)]
                row.update(summarise(part.reset_index(), (w.cutoff - w.start).days))
                row["has_weather"] = len(part) > 0
                row["last_input_date"] = max(part.index) if len(part) else None
            rows.append(row)
    return pd.DataFrame(rows)
