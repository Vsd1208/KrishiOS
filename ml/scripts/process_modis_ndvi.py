"""Turn the finished AppEEARS MOD13A3 request into monthly district NDVI (low disk use).

For each month: download the NDVI and pixel-reliability GeoTIFFs into a temporary folder, compute
the district mean over good/marginal pixels, append it to
``data/processed/yield_features/v1/district_ndvi_monthly.parquet``, then delete those two
temporary rasters (they can be fetched again from AppEEARS). Only about 14 MB of rasters exist
at a time. The run is resumable and stops if free disk falls below ``MIN_FREE_GB``.

Usage (from ml/)::

    uv run --no-sync python scripts/process_modis_ndvi.py
"""

from __future__ import annotations

import json
import shutil
import time
from pathlib import Path

import _bootstrap  # noqa: F401
import numpy as np
import pandas as pd

from krishios_ml.common.experiment_log import track_experiment
from krishios_ml.common.paths import DATA_DIR, ML_ROOT
from krishios_ml.yield_features import modis

modis.use_bundled_proj()  # before rasterio is first imported
RAW = DATA_DIR / "raw" / "modis" / "mod13a3"
TMP = RAW / "tmp"
OUT = DATA_DIR / "processed" / "yield_features" / "v1" / "district_ndvi_monthly.parquet"
DISTRICTS = DATA_DIR / "processed" / "boundaries" / "v1" / "districts.parquet"
NDVI, RELIABILITY = modis.LAYERS
MIN_FREE_GB = 3.0
SAVE_EVERY = 12
ATTEMPTS = 8


def month_pairs(files: list[dict]) -> dict:
    months: dict = {}
    for f in files:
        parsed = modis.parse_name(f["file_name"]) if f["file_name"].endswith(".tif") else None
        if parsed and parsed[0] in modis.LAYERS:
            months.setdefault(parsed[1], {})[parsed[0]] = f
    return {m: v for m, v in sorted(months.items()) if len(v) == len(modis.LAYERS)}


def process_month(ndvi_path: Path, reliability_path: Path, districts, index=None):
    """District table for one month, and the district raster index (built once)."""
    import rasterio

    with rasterio.open(ndvi_path) as src:
        ndvi, nodata, shape, transform, crs = (src.read(1), src.nodata, src.shape, src.transform,
                                               src.crs)
    with rasterio.open(reliability_path) as src:
        reliability = src.read(1)
        if src.shape != shape or src.transform != transform:
            raise ValueError(f"grid mismatch: {ndvi_path.name}")
    if index is None:
        index = modis.district_index(districts.to_crs(crs), shape, transform)
    return modis.aggregate_month(ndvi, reliability, index, nodata), index


def fetch(token: str, task_id: str, file: dict) -> Path:
    for attempt in range(1, ATTEMPTS + 1):
        try:
            return modis.download(token, task_id, file, TMP)
        except Exception as exc:  # flaky network: partial files are replaced on retry
            if attempt == ATTEMPTS:
                raise
            print(f"retry {attempt}: {type(exc).__name__}", flush=True)
            time.sleep(min(60, 5 * attempt))
    raise AssertionError("unreachable")


def main() -> None:
    import geopandas as gpd

    task_id = json.loads((RAW / "task.json").read_text())["task_id"]
    districts = gpd.read_parquet(DISTRICTS)
    done = pd.read_parquet(OUT) if OUT.exists() else pd.DataFrame()
    finished = set(pd.to_datetime(done["month_start"]).dt.date) if len(done) else set()
    frames = [done] if len(done) else []
    config = {"product": modis.PRODUCT, "layers": list(modis.LAYERS), "task_id": task_id,
              "good_reliability": list(modis.GOOD_RELIABILITY)}
    with track_experiment("modis_ndvi", config, seed=None, split_id=None) as rec, \
            modis.session(ML_ROOT / ".env") as token:
        months = month_pairs(modis.bundle(token, task_id))
        index, added = None, 0
        for month, pair in months.items():
            if month in finished:
                continue
            free = shutil.disk_usage(RAW).free / 1e9
            if free < MIN_FREE_GB:
                print(f"stopping: only {free:.1f} GB free", flush=True)
                break
            ndvi_path = fetch(token, task_id, pair[NDVI])
            rel_path = fetch(token, task_id, pair[RELIABILITY])
            table, index = process_month(ndvi_path, rel_path, districts, index)
            frames.append(table.assign(month_start=pd.Timestamp(month)))
            ndvi_path.unlink()
            rel_path.unlink()
            added += 1
            if added % SAVE_EVERY == 0:
                pd.concat(frames, ignore_index=True).to_parquet(OUT, index=False)
                print(f"{month}: {added} months added", flush=True)
        result = pd.concat(frames, ignore_index=True)
        result.to_parquet(OUT, index=False)
        rec.metrics = {
            "months_available": len(months), "months_done": int(result["month_start"].nunique()),
            "months_added_this_run": added,
            "districts": int(result["lgd_district_code"].nunique()),
            "rows": len(result),
            "ndvi_missing_share": round(float(result["ndvi"].isna().mean()), 4),
            "good_share_median": round(float(np.nanmedian(result["good_share"])), 4),
        }
        rec.artifact_path = str(OUT.relative_to(ML_ROOT))
    print(json.dumps(rec.metrics, indent=1), "\nrun_id", rec.run_id)


if __name__ == "__main__":
    main()
