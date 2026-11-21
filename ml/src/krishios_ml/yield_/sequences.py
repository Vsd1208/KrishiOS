"""Dekad (10-day) input sequences for the shared yield model (Phase 10).

One record per district x crop year x season covers the longest forecast window: 60 days before
the season anchor to 90 days after it, as 15 dekads. Records hold every value for that window;
the view for a forecast at lead L comes from :func:`krishios_ml.yield_.model.assemble`, which
hides anything not available at the cutoff (``anchor + L``):

- weather: only dekads that ended by the cutoff;
- NDVI: a monthly composite sits in the dekad of its month end and is visible only if its
  publication day (month end + ``PUBLICATION_LAG_DAYS``) is strictly before the cutoff.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from krishios_ml.yield_features.features import PRE_DAYS, window
from krishios_ml.yield_features.modis import PUBLICATION_LAG_DAYS

DEKADS = 15
DEKAD_DAYS = 10
MAX_LEAD = 90
WEATHER_COLS = ("PRECTOTCORR", "T2M_MAX", "T2M_MIN", "RH2M", "ALLSKY_SFC_SW_DWN")
NOT_AVAILABLE = 32_000  # publication day of an empty NDVI slot


def daily_tensor(folder: Path, districts: np.ndarray) -> tuple[np.ndarray, np.datetime64]:
    """(district, day, variable) float32 array, NaN where missing, and its first date."""
    files = sorted(folder.glob("*.parquet"))
    first = np.datetime64(f"{files[0].stem}-01-01", "D")
    last = np.datetime64(f"{int(files[-1].stem) + 1}-01-01", "D")
    days = int((last - first) / np.timedelta64(1, "D"))
    out = np.full((len(districts), days, len(WEATHER_COLS)), np.nan, dtype="float32")
    for f in files:
        d = pd.read_parquet(f, columns=["lgd_district_code", "date", *WEATHER_COLS])
        i = np.searchsorted(districts, d["lgd_district_code"].to_numpy())
        i = np.clip(i, 0, len(districts) - 1)
        ok = districts[i] == d["lgd_district_code"].to_numpy()
        j = ((d["date"].to_numpy("datetime64[D]") - first) / np.timedelta64(1, "D")).astype(int)
        out[i[ok], j[ok]] = d.loc[ok, list(WEATHER_COLS)].to_numpy("float32")
    return out, first


def _dekads(block: np.ndarray) -> np.ndarray:
    """(district, DEKADS * 10, variable) -> (district, DEKADS, variable). Rain is summed, the
    rest averaged; a dekad with any missing day stays missing."""
    n, _, v = block.shape
    x = block.reshape(n, DEKADS, DEKAD_DAYS, v)
    out = x.mean(axis=2)
    out[:, :, 0] = x[:, :, :, 0].sum(axis=2)
    return out


def build(keys: pd.DataFrame, daily_dir: Path, monthly: pd.DataFrame) -> dict[str, np.ndarray]:
    """``keys``: unique (lgd_district_code, crop_year, season)."""
    keys = keys.sort_values(["crop_year", "season", "lgd_district_code"]).reset_index(drop=True)
    districts = np.array(sorted({*keys["lgd_district_code"].astype(int),
                                 *monthly["lgd_district_code"].astype(int)}), dtype="int64")
    daily, first = daily_tensor(daily_dir, districts)
    n = len(keys)
    weather = np.full((n, DEKADS, len(WEATHER_COLS)), np.nan, dtype="float32")
    ndvi = np.full((n, DEKADS, 2), np.nan, dtype="float32")
    pub = np.full((n, DEKADS), NOT_AVAILABLE, dtype="int16")
    m = monthly.assign(month_start=pd.to_datetime(monthly["month_start"]))
    months = np.sort(m["month_start"].unique())
    month_ends = (pd.DatetimeIndex(months) + pd.offsets.MonthEnd(0)).to_numpy("datetime64[D]")
    grid = np.full((len(districts), len(months), 2), np.nan, dtype="float32")
    di = np.searchsorted(districts, m["lgd_district_code"].astype(int).to_numpy())
    mi = np.searchsorted(months, m["month_start"].to_numpy())
    grid[di, mi, 0] = m["ndvi"].to_numpy("float32")
    grid[di, mi, 1] = m["good_share"].to_numpy("float32")
    span = DEKADS * DEKAD_DAYS
    for (year, season), idx in keys.groupby(["crop_year", "season"]).indices.items():
        start = np.datetime64(window(season, int(year), MAX_LEAD).start, "D")
        rows = np.searchsorted(districts, keys["lgd_district_code"].to_numpy("int64")[idx])
        s = int((start - first) / np.timedelta64(1, "D"))
        lo, hi = max(s, 0), min(s + span, daily.shape[1])
        if hi > lo:
            block = np.full((len(idx), span, len(WEATHER_COLS)), np.nan, dtype="float32")
            block[:, lo - s:hi - s] = daily[rows, lo:hi]
            weather[idx] = _dekads(block)
        offsets = ((month_ends - start) / np.timedelta64(1, "D")).astype(int)
        for k in np.flatnonzero((offsets >= 0) & (offsets < span)):
            slot = offsets[k] // DEKAD_DAYS
            ndvi[idx, slot] = grid[rows, k]
            pub[idx, slot] = offsets[k] + PUBLICATION_LAG_DAYS
    return {"lgd_district_code": keys["lgd_district_code"].to_numpy("int32"),
            "crop_year": keys["crop_year"].to_numpy("int16"),
            "season": keys["season"].to_numpy(dtype="U12"),
            "weather": weather, "ndvi": ndvi, "ndvi_pub": pub}


def cutoff_day(lead_days: int) -> int:
    """Days from the record's first day to the forecast cutoff (exclusive)."""
    return PRE_DAYS + lead_days
