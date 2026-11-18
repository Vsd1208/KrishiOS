"""Fetch monthly regional climate drivers from NOAA PSL (OPeNDAP subsets only).

Each driver in ``krishios_ml.yield_features.climate.DRIVERS`` is one small box request, averaged
by area and stored in ``data/processed/yield_features/v1/climate_drivers.parquet``. Requests are
spaced out because the service limits request rates. Finished drivers are kept, so a run resumes.

Sources: NCEP/NCAR Reanalysis 1 (winds, height, temperature), GPCP v2.3 (satellite and gauge
precipitation), NOAA interpolated OLR (satellite), NOAA OI SST v2 (satellite and in situ).

Usage (from ml/)::

    uv run --no-sync python scripts/download_climate_grids.py
"""

from __future__ import annotations

import http.client
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

import _bootstrap  # noqa: F401
import numpy as np
import pandas as pd

from krishios_ml.common.paths import DATA_DIR
from krishios_ml.yield_features import climate

BASE = "https://psl.noaa.gov/thredds/dodsC/Datasets"
OUT = DATA_DIR / "processed" / "yield_features" / "v1" / "climate_drivers.parquet"
FIRST_YEAR = 1982
PAUSE_SECONDS = 6
HEADERS = {"User-Agent": "climate-index-fetch/1.0"}


def get(url: str) -> str:
    for attempt in range(1, 9):
        time.sleep(PAUSE_SECONDS)
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS),
                                        timeout=180) as r:
                return r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == 8:
                raise
        except (OSError, http.client.HTTPException):
            if attempt == 8:
                raise
        print(f"retry {attempt}", flush=True)
        time.sleep(min(300, 30 * attempt))
    raise AssertionError("unreachable")


def months_from(values: np.ndarray, units: str) -> pd.DatetimeIndex:
    m = re.match(r"(days|hours) since (\d+)-(\d+)-(\d+)", units)
    if not m:
        raise ValueError(f"unexpected time units: {units}")
    origin = datetime(int(m[2]), int(m[3]), int(m[4]))
    hours = 24 if m[1] == "days" else 1
    return pd.DatetimeIndex([origin + timedelta(hours=float(v) * hours) for v in values]
                            ).to_period("M").to_timestamp()


def attribute(das: str, variable: str, name: str) -> float | None:
    block = re.search(rf"(?ms)^\s*{variable} \{{(.*?)^\s*\}}", das)
    m = re.search(rf"{name}\s+([-\d.eE+]+);", block.group(1)) if block else None
    return float(m.group(1)) if m else None


def fetch(d: climate.Driver) -> pd.DataFrame:
    root = f"{BASE}/{d.dataset}"
    das = get(f"{root}.das")
    units = re.search(r'(?ms)^\s*time \{.*?units "([^"]+)"', das).group(1)
    names = "time,lat,lon" + (",level" if d.level is not None else "")
    axes = get(f"{root}.ascii?{names}")
    time_v, lat, lon = (climate.parse_dods_vector(axes, n) for n in ("time", "lat", "lon"))
    months = months_from(time_v, units)
    t = np.flatnonzero(months.year >= FIRST_YEAR)
    la = np.flatnonzero((lat >= d.lat[0]) & (lat <= d.lat[1]))
    lo = np.flatnonzero((lon >= d.lon[0]) & (lon <= d.lon[1]))
    if not len(t) or not len(la) or not len(lo):
        raise ValueError(f"{d.name}: empty selection")
    parts = [f"[{t[0]}:{t[-1]}]"]
    if d.level is not None:
        level = climate.parse_dods_vector(axes, "level")
        k = int(np.flatnonzero(level == d.level)[0])
        parts.append(f"[{k}]")
    parts += [f"[{la[0]}:{la[-1]}]", f"[{lo[0]}:{lo[-1]}]"]
    query = urllib.parse.quote(f"{d.variable}{''.join(parts)}", safe="")
    text = get(f"{root}.ascii?{query}")
    grid = climate.parse_dods_grid(text, d.variable)
    if d.level is not None:
        grid = grid.squeeze(1)
    missing = attribute(das, d.variable, "missing_value")
    grid = grid * (attribute(das, d.variable, "scale_factor") or 1.0) + (
        attribute(das, d.variable, "add_offset") or 0.0)
    values = climate.box_mean(grid, lat[la], missing)
    return pd.DataFrame({"driver": d.name, "month_start": months[t], "value": values,
                         "cells": len(la) * len(lo)})


def main() -> None:
    frames = [pd.read_parquet(OUT)] if OUT.exists() else []
    done = set(frames[0]["driver"]) if frames else set()
    for d in climate.DRIVERS:
        if d.name in done:
            continue
        f = fetch(d)
        frames.append(f)
        pd.concat(frames, ignore_index=True).to_parquet(OUT, index=False)
        print(f"{d.name}: {len(f)} months, {f['month_start'].min():%Y-%m} to "
              f"{f['month_start'].max():%Y-%m}, {int(f['cells'].iloc[0])} cells, mean "
              f"{f['value'].mean():.2f}, missing {f['value'].isna().mean():.3f}", flush=True)
    print("done")


if __name__ == "__main__":
    main()
