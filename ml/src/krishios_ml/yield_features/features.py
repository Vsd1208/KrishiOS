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


COLUMNS = ("PRECTOTCORR", "T2M_MAX", "T2M_MIN", "RH2M", "ALLSKY_SFC_SW_DWN")


def _max_run(mask: np.ndarray) -> int:
    if not mask.any():
        return 0
    m = np.concatenate(([0], mask.astype(np.int8), [0]))
    edges = np.flatnonzero(np.diff(m))
    return int((edges[1::2] - edges[::2]).max())


def _mean(v: np.ndarray) -> float:
    ok = np.isfinite(v)
    return float(v[ok].mean()) if ok.any() else np.nan


def summarise_arrays(cols: dict[str, np.ndarray], expected_days: int) -> dict[str, float]:
    """``cols``: one district's window, column name -> float64 array (NaN = missing)."""
    empty = np.array([], dtype="float64")
    rain, tmax, tmin = (cols.get(c, empty) for c in ("PRECTOTCORR", "T2M_MAX", "T2M_MIN"))
    n = expected_days or np.nan
    out: dict[str, float] = {}
    ok = np.isfinite(rain)
    has = bool(ok.any())
    out["rain_sum"] = float(rain[ok].sum()) if has else np.nan
    out["rain_days"] = float((rain[ok] >= RAIN_DAY_MM).sum()) if has else np.nan
    out["max_dry_spell"] = float(_max_run(ok & (np.nan_to_num(rain) < 1.0))) if has else np.nan
    out["rain_coverage"] = float(ok.sum() / n)
    hot = np.isfinite(tmax)
    t_ok = hot & np.isfinite(tmin)
    out["tmax_mean"] = _mean(tmax)
    out["tmin_mean"] = _mean(tmin)
    out["heat_days"] = float((tmax[hot] >= HEAT_C).sum()) if hot.any() else np.nan
    if t_ok.any():
        tmean = (np.clip(tmax[t_ok], None, GDD_CAP) + tmin[t_ok]) / 2
        out["gdd"] = float(np.clip(tmean - GDD_BASE, 0, None).sum())
    else:
        out["gdd"] = np.nan
    out["temp_coverage"] = float(t_ok.sum() / n)
    for col, name in (("RH2M", "rh_mean"), ("ALLSKY_SFC_SW_DWN", "srad_mean")):
        v = cols.get(col, empty)
        out[name] = _mean(v)
        out[f"{name}_coverage"] = float(np.isfinite(v).sum() / n)
    return out


def summarise(days: pd.DataFrame, expected_days: int) -> dict[str, float]:
    """``days``: one district's rows inside the window (date, PRECTOTCORR, T2M_MAX, ...)."""
    cols = {c: days[c].to_numpy(dtype="float64") for c in COLUMNS if c in days}
    return summarise_arrays(cols, expected_days)


def build(daily: pd.DataFrame, labels: pd.DataFrame, leads=LEADS) -> pd.DataFrame:
    """One row per (district, crop_year, season, lead). ``labels`` supplies the keys only.
    Windows are sliced from each district's sorted dates with ``searchsorted``: the slice
    ``[start, cutoff)`` excludes the cutoff day by construction."""
    keys = labels[["lgd_district_code", "crop_year", "season"]].drop_duplicates()
    daily = daily.assign(date=pd.to_datetime(daily["date"]).values.astype("datetime64[D]"))
    cols = [c for c in COLUMNS if c in daily]
    by_district = {}
    for k, g in daily.groupby("lgd_district_code"):
        g = g.sort_values("date")
        by_district[int(k)] = (g["date"].to_numpy(),
                               {c: g[c].to_numpy(dtype="float64") for c in cols})
    rows = []
    for d_code, year, season in keys.itertuples(index=False):
        hit = by_district.get(int(d_code))
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
            if hit is None:
                row["has_weather"] = False
            else:
                dates, arrays = hit
                lo = int(np.searchsorted(dates, np.datetime64(w.start, "D"), side="left"))
                hi = int(np.searchsorted(dates, np.datetime64(w.cutoff, "D"), side="left"))
                row.update(summarise_arrays({c: a[lo:hi] for c, a in arrays.items()},
                                            (w.cutoff - w.start).days))
                row["has_weather"] = hi > lo
                row["last_input_date"] = dates[hi - 1].astype(date) if hi > lo else None
            rows.append(row)
    out = pd.DataFrame(rows)
    for c in ("window_start", "cutoff", "last_input_date"):
        if c in out:
            out[c] = pd.to_datetime(out[c])
    return out
