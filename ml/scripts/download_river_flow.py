"""Fetch modelled daily river discharge (Copernicus GloFAS, through the Open-Meteo Flood API).

Used for non-commercial academic research under Open-Meteo's free tier (CC BY 4.0 attribution).
One request per river point in ``climate.RIVER_POINTS``; finished points are kept, so a run
resumes. These are model estimates, not gauge observations.

Usage (from ml/)::

    uv run --no-sync python scripts/download_river_flow.py
"""

from __future__ import annotations

import http.client
import json
import time
import urllib.error
import urllib.parse
import urllib.request

import _bootstrap  # noqa: F401
import pandas as pd

from krishios_ml.common.paths import DATA_DIR
from krishios_ml.yield_features import climate

API = "https://flood-api.open-meteo.com/v1/flood"
OUT = DATA_DIR / "processed" / "yield_features" / "v1" / "river_discharge_daily.parquet"
START, END = "1990-01-01", "2024-12-31"
HEADERS = {"User-Agent": "academic-research-client/1.0"}


def fetch(name: str, lat: float, lon: float) -> pd.DataFrame:
    query = urllib.parse.urlencode({"latitude": lat, "longitude": lon,
                                    "daily": "river_discharge", "start_date": START,
                                    "end_date": END})
    for attempt in range(1, 7):
        time.sleep(2)
        try:
            req = urllib.request.Request(f"{API}?{query}", headers=HEADERS)
            with urllib.request.urlopen(req, timeout=120) as r:
                d = json.load(r)
            break
        except (OSError, urllib.error.URLError, http.client.HTTPException, ValueError):
            if attempt == 6:
                raise
            print(f"{name}: retry {attempt}", flush=True)
            time.sleep(20 * attempt)
    return pd.DataFrame({"river": name, "date": pd.to_datetime(d["daily"]["time"]),
                         "discharge": pd.to_numeric(d["daily"]["river_discharge"],
                                                    errors="coerce"),
                         "grid_lat": d["latitude"], "grid_lon": d["longitude"]})


def main() -> None:
    frames = [pd.read_parquet(OUT)] if OUT.exists() else []
    done = set(frames[0]["river"]) if frames else set()
    for name, (lat, lon, _) in climate.RIVER_POINTS.items():
        if name in done:
            continue
        f = fetch(name, lat, lon)
        frames.append(f)
        pd.concat(frames, ignore_index=True).to_parquet(OUT, index=False)
        q = f["discharge"]
        print(f"{name}: grid ({f['grid_lat'].iloc[0]:.2f}, {f['grid_lon'].iloc[0]:.2f}) days "
              f"{q.notna().sum()} mean {q.mean():.0f} p99 {q.quantile(.99):.0f} max {q.max():.0f}",
              flush=True)
    print("done")


if __name__ == "__main__":
    main()
