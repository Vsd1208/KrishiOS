"""Area-weighted zonal aggregation of POWER grid cells to LGD district polygons.

A POWER cell is a 0.625° (lon) x 0.5° (lat) rectangle around its centre. Each district gets
the cells it overlaps, weighted by the overlap area in an equal-area projection (EPSG:6933).
District daily value = sum(w * v) / sum(w) over cells with a value that day; if no
overlapping cell has a value, the district-day is missing (never filled).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

HALF_LON, HALF_LAT = 0.3125, 0.25
EQUAL_AREA = 6933


def cell_weights(districts, centres: pd.DataFrame) -> pd.DataFrame:
    """``centres``: unique (lon, lat). Returns (lgd_district_code, lon, lat, weight)."""
    import geopandas as gpd
    from shapely.geometry import box

    cells = gpd.GeoDataFrame(
        centres[["lon", "lat"]].reset_index(drop=True),
        geometry=[
            box(x - HALF_LON, y - HALF_LAT, x + HALF_LON, y + HALF_LAT)
            for x, y in zip(centres["lon"], centres["lat"], strict=True)
        ],
        crs=4326,
    )
    d = districts[["lgd_district_code", "geometry"]].to_crs(EQUAL_AREA)
    pieces = gpd.overlay(d, cells.to_crs(EQUAL_AREA), how="intersection", keep_geom_type=True)
    pieces["area"] = pieces.geometry.area
    w = pieces.groupby(["lgd_district_code", "lon", "lat"], as_index=False)["area"].sum()
    w["weight"] = w["area"] / w.groupby("lgd_district_code")["area"].transform("sum")
    return w[["lgd_district_code", "lon", "lat", "weight"]]


def aggregate(values: pd.DataFrame, weights: pd.DataFrame) -> pd.DataFrame:
    """``values``: (lon, lat, date, value) for one parameter. Returns (lgd, date, value)."""
    v = values.dropna(subset=["value"]).merge(weights, on=["lon", "lat"], how="inner")
    v["wv"] = v["value"].astype("float64") * v["weight"]
    g = v.groupby(["lgd_district_code", "date"], as_index=False).agg(
        wv=("wv", "sum"), w=("weight", "sum")
    )
    g["value"] = (g["wv"] / g["w"]).astype("float32")
    return g[["lgd_district_code", "date", "value"]]


def build_daily(
    cache: Path, weights: pd.DataFrame, parameters: tuple[str, ...], years: range
) -> pd.DataFrame:
    """District-day table with one column per parameter (missing stays NaN)."""
    frames = []
    for year in years:
        per_param = []
        for p in parameters:
            files = sorted(cache.glob(f"{p}_{year}_*.parquet"))
            if not files:
                continue
            vals = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
            vals = vals.drop_duplicates(["lon", "lat", "date"])  # box edges overlap
            per_param.append(aggregate(vals, weights).rename(columns={"value": p}))
        if per_param:
            merged = per_param[0]
            for extra in per_param[1:]:
                merged = merged.merge(extra, on=["lgd_district_code", "date"], how="outer")
            frames.append(merged)
    out = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    return (
        out.sort_values(["lgd_district_code", "date"]).reset_index(drop=True) if len(out) else out
    )


def coverage(weights: pd.DataFrame) -> pd.Series:
    return weights.groupby("lgd_district_code")["weight"].count().rename("cells")


def _isfinite(x: np.ndarray) -> np.ndarray:
    return np.isfinite(x)
