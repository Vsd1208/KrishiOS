"""MODIS vegetation index (MOD13A3.061, monthly 1 km NDVI) via NASA AppEEARS (Phase 7).

One area request covers India (a simplified union of the state polygons). Credentials come
from ``ml/.env`` (EARTHDATA_USERNAME / EARTHDATA_PASSWORD), are sent only to AppEEARS over
HTTPS, and are never logged. Tokens last 48 h and are logged out after use.

Leakage rule (enforced in features): a monthly composite may enter a forecast only if its
whole month ended at least ``PUBLICATION_LAG_DAYS`` before the cutoff, i.e. it would have been
published by then. NDVI pixels with reliability other than 0 (good) or 1 (marginal) are
masked; fill values stay missing.
"""

from __future__ import annotations

import base64
import json
import urllib.request
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

API = "https://appeears.earthdatacloud.nasa.gov/api"
PRODUCT = "MOD13A3.061"
LAYERS = ("_1_km_monthly_NDVI", "_1_km_monthly_pixel_reliability")
NDVI_FILL, NDVI_SCALE = -3000, 0.0001
GOOD_RELIABILITY = (0, 1)
PUBLICATION_LAG_DAYS = 15


def read_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def _call(method: str, url: str, token: str | None = None, body: dict | None = None,
          headers: dict | None = None, timeout: int = 120):
    data = json.dumps(body).encode() if body is not None else b""
    h = {"Content-Type": "application/json", **(headers or {})}
    if token:
        h["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, method=method, data=data if method != "GET" else None,
                                 headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
    return json.loads(raw) if raw else None


@contextmanager
def session(env_path: Path) -> Iterator[str]:
    env = read_env(env_path)
    user, pwd = env.get("EARTHDATA_USERNAME"), env.get("EARTHDATA_PASSWORD")
    if not user or not pwd:
        raise RuntimeError("EARTHDATA_USERNAME / EARTHDATA_PASSWORD missing in ml/.env")
    basic = base64.b64encode(f"{user}:{pwd}".encode()).decode()
    token = _call("POST", f"{API}/login", headers={"Authorization": f"Basic {basic}"})["token"]
    try:
        yield token
    finally:
        with suppress(Exception):  # the token expires on its own in 48 h
            _call("POST", f"{API}/logout", token=token)


def india_aoi(states, tolerance: float = 0.02, min_area_deg2: float = 0.0005) -> dict:
    """Simplified union of the state polygons as a GeoJSON FeatureCollection."""
    from shapely.geometry import MultiPolygon, mapping

    geom = states.union_all().buffer(0.02).simplify(tolerance)
    parts = list(geom.geoms) if hasattr(geom, "geoms") else [geom]
    keep = MultiPolygon([p for p in parts if p.area >= min_area_deg2])
    return {"type": "FeatureCollection",
            "features": [{"type": "Feature", "properties": {}, "geometry": mapping(keep)}]}


def task_body(name: str, aoi: dict, start: str, end: str) -> dict:
    """``start``/``end`` as MM-DD-YYYY (AppEEARS format)."""
    return {
        "task_type": "area",
        "task_name": name,
        "params": {
            "dates": [{"startDate": start, "endDate": end}],
            "layers": [{"product": PRODUCT, "layer": layer} for layer in LAYERS],
            "output": {"format": {"type": "geotiff"}, "projection": "geographic"},
            "geo": aoi,
        },
    }


def submit(token: str, body: dict) -> str:
    return _call("POST", f"{API}/task", token=token, body=body)["task_id"]


def status(token: str, task_id: str) -> dict:
    return _call("GET", f"{API}/task/{task_id}", token=token)


def bundle(token: str, task_id: str) -> list[dict]:
    """Files of a finished task: file_id, file_name, file_size (bytes), file_type."""
    return _call("GET", f"{API}/bundle/{task_id}", token=token)["files"]


def download(token: str, task_id: str, file: dict, out_dir: Path) -> Path:
    path = out_dir / file["file_name"]
    if path.exists() and path.stat().st_size == file["file_size"]:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(f"{API}/bundle/{task_id}/{file['file_id']}",
                                 headers={"Authorization": f"Bearer {token}"})
    tmp = path.with_suffix(path.suffix + ".part")
    with urllib.request.urlopen(req, timeout=600) as r, tmp.open("wb") as fh:
        while chunk := r.read(1 << 20):
            fh.write(chunk)
    tmp.replace(path)
    return path


# --- processing -------------------------------------------------------------------------------

def parse_name(name: str) -> tuple[str, date] | None:
    """``MOD13A3.061__1_km_monthly_NDVI_doy2000032_aid0001.tif`` -> (layer, month start)."""
    import re

    m = re.search(r"(_1_km_monthly_[A-Za-z_]+?)_doy(\d{4})(\d{3})", name)
    if not m:
        return None
    year, doy = int(m.group(2)), int(m.group(3))
    return m.group(1), date(year, 1, 1) + timedelta(days=doy - 1)


def district_index(districts, shape: tuple[int, int], transform) -> np.ndarray:
    """Raster of LGD codes (0 = none) on the MODIS grid. A district too small to own a pixel
    centre gets the pixels it touches, so every district has at least one pixel."""
    from rasterio.features import rasterize

    pairs = list(zip(districts.geometry, districts["lgd_district_code"].astype(int), strict=True))
    idx = rasterize(pairs, out_shape=shape, transform=transform, fill=0, dtype="int32")
    present = set(np.unique(idx))
    for geom, code in pairs:
        if code not in present:
            touched = rasterize([(geom, 1)], out_shape=shape, transform=transform, fill=0,
                                all_touched=True, dtype="uint8")
            idx[(touched == 1) & (idx == 0)] = code
    return idx


def aggregate_month(ndvi: np.ndarray, reliability: np.ndarray, index: np.ndarray,
                    nodata: float | None) -> pd.DataFrame:
    """District mean NDVI over good pixels, and the share of the district's pixels that are
    good. Values stored unscaled (|v| > 1.5) are scaled by NDVI_SCALE."""

    v = ndvi.astype("float64")
    bad = ~np.isfinite(v) | (v == NDVI_FILL)
    if nodata is not None:
        bad |= v == nodata
    if np.nanmax(np.abs(np.where(bad, 0, v))) > 1.5:
        v = v * NDVI_SCALE
    good = ~bad & np.isin(reliability, GOOD_RELIABILITY) & (index > 0)
    size = int(index.max()) + 1
    n_all = np.bincount(index[index > 0], minlength=size)
    n_good = np.bincount(index[good], minlength=size)
    s_good = np.bincount(index[good], weights=v[good], minlength=size)
    codes = np.flatnonzero(n_all)
    with np.errstate(invalid="ignore", divide="ignore"):
        mean = np.where(n_good[codes] > 0, s_good[codes] / n_good[codes], np.nan)
    return pd.DataFrame({"lgd_district_code": codes, "ndvi": mean.astype("float32"),
                         "good_share": (n_good[codes] / n_all[codes]).astype("float32")})


def ndvi_features(monthly: pd.DataFrame, keys: pd.DataFrame) -> pd.DataFrame:
    """``monthly``: (lgd_district_code, month_start, ndvi). ``keys``: (lgd_district_code,
    crop_year, season, lead_days, window_start, cutoff), e.g. the weather feature rows.

    A month is usable only if it ended inside the window and was published (month end +
    PUBLICATION_LAG_DAYS) strictly before the cutoff."""

    m = monthly.dropna(subset=["ndvi"]).copy()
    m["month_end"] = (pd.to_datetime(m["month_start"]) + pd.offsets.MonthEnd(0))
    m["published"] = m["month_end"] + pd.Timedelta(days=PUBLICATION_LAG_DAYS)
    by_d = {int(k): g.sort_values("month_end") for k, g in m.groupby("lgd_district_code")}
    rows = []
    for r in keys.itertuples(index=False):
        g = by_d.get(int(r.lgd_district_code))
        out = {"ndvi_last": np.nan, "ndvi_mean": np.nan, "ndvi_max": np.nan,
               "ndvi_months": 0, "ndvi_last_month_end": pd.NaT}
        if g is not None:
            start, cutoff = pd.Timestamp(r.window_start), pd.Timestamp(r.cutoff)
            ok = g[(g["month_end"] >= start) & (g["published"] < cutoff)]
            if len(ok):
                out.update(ndvi_last=float(ok["ndvi"].iloc[-1]),
                           ndvi_mean=float(ok["ndvi"].mean()),
                           ndvi_max=float(ok["ndvi"].max()), ndvi_months=len(ok),
                           ndvi_last_month_end=ok["month_end"].iloc[-1])
        rows.append(out)
    return pd.concat([keys.reset_index(drop=True), pd.DataFrame(rows)], axis=1)
