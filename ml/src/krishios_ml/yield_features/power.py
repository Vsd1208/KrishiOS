"""NASA POWER daily regional grids for India (yield predictors, Phase 7).

The regional endpoint returns one parameter for a box of at most 10°x10° and at most 366 days
on the POWER 0.5° x 0.625° grid. Each (box, parameter, year) is cached once as Parquet
(``lon, lat, date, value``), so re-runs only fetch what is missing. ``-999`` fill values are
stored as missing, never as numbers. Requests are sequential with a pause (polite use).
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

BASE = "https://power.larc.nasa.gov/api/temporal/daily/regional"
USER_AGENT = "KrishiOS-yield/1.0"
FILL = -999.0
# Daily predictors: precipitation, temperature extremes and mean, humidity, solar radiation.
PARAMETERS = ("PRECTOTCORR", "T2M_MAX", "T2M_MIN", "RH2M", "ALLSKY_SFC_SW_DWN")
# India land boxes (lat_min, lat_max, lon_min, lon_max), each within the 10°x10° limit.
BOXES = [
    (6.0, 16.0, 68.0, 78.0),
    (6.0, 16.0, 78.0, 88.0),
    (16.0, 26.0, 68.0, 78.0),
    (16.0, 26.0, 78.0, 88.0),
    (16.0, 26.0, 88.0, 98.0),
    (26.0, 36.0, 68.0, 78.0),
    (26.0, 36.0, 78.0, 88.0),
    (26.0, 36.0, 88.0, 98.0),
    (36.0, 38.0, 72.0, 80.0),
]


@dataclass(frozen=True, slots=True)
class Chunk:
    box: tuple[float, float, float, float]
    parameter: str
    year: int

    @property
    def name(self) -> str:
        la0, la1, lo0, lo1 = self.box
        return f"{self.parameter}_{self.year}_{la0:g}_{la1:g}_{lo0:g}_{lo1:g}.parquet"


def fetch(chunk: Chunk, timeout: int = 300) -> pd.DataFrame:
    la0, la1, lo0, lo1 = chunk.box
    query = urllib.parse.urlencode(
        {
            "parameters": chunk.parameter,
            "community": "AG",
            "format": "JSON",
            "latitude-min": la0,
            "latitude-max": la1,
            "longitude-min": lo0,
            "longitude-max": lo1,
            "start": f"{chunk.year}0101",
            "end": f"{chunk.year}1231",
        }
    )
    req = urllib.request.Request(f"{BASE}?{query}", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.load(r)
    rows = []
    for feat in data.get("features", []):
        lon, lat = feat["geometry"]["coordinates"][:2]
        for day, value in feat["properties"]["parameter"][chunk.parameter].items():
            rows.append((lon, lat, day, None if value is None or value <= FILL else value))
    df = pd.DataFrame(rows, columns=["lon", "lat", "date", "value"])
    df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")
    df["lon"], df["lat"] = df["lon"].astype("float32"), df["lat"].astype("float32")
    df["value"] = df["value"].astype("float32")
    return df


def download(
    cache: Path,
    years: range,
    parameters=PARAMETERS,
    boxes=BOXES,
    pause: float = 1.0,
    retries: int = 3,
    log=print,
) -> dict[str, int]:
    cache.mkdir(parents=True, exist_ok=True)
    stats = {"cached": 0, "fetched": 0, "failed": 0}
    for year in years:
        for parameter in parameters:
            for box in boxes:
                chunk = Chunk(box, parameter, year)
                path = cache / chunk.name
                if path.exists():
                    stats["cached"] += 1
                    continue
                for attempt in range(1, retries + 1):
                    try:
                        df = fetch(chunk)
                        df.to_parquet(path, index=False)
                        stats["fetched"] += 1
                        break
                    except Exception as exc:  # network: retry, then record and move on
                        if attempt == retries:
                            stats["failed"] += 1
                            log(f"failed {chunk.name}: {type(exc).__name__}")
                        time.sleep(10 * attempt)
                time.sleep(pause)
        log(f"{year}: {stats}")
    return stats
