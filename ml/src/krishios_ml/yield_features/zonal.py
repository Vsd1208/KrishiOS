"""Area-weighted zonal aggregation of POWER grid cells to LGD district polygons.

POWER serves meteorology on the MERRA-2 grid (0.625° lon x 0.5° lat) but solar radiation on
the CERES 1° x 1° grid, so each parameter uses the weights of its own grid (``GRID_OF``).
A cell is the rectangle of its grid's size around its centre. Each district gets
the cells it overlaps, weighted by the overlap area in an equal-area projection (EPSG:6933).
District daily value = sum(w * v) / sum(w) over cells with a value that day; if no
overlapping cell has a value, the district-day is missing (never filled).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

EQUAL_AREA = 6933
GRIDS = {"merra2": (0.3125, 0.25), "ceres1deg": (0.5, 0.5)}  # half-sizes (lon, lat)
GRID_OF = {"ALLSKY_SFC_SW_DWN": "ceres1deg"}  # every other parameter: merra2


def grid_of(parameter: str) -> str:
    return GRID_OF.get(parameter, "merra2")


def cell_weights(districts, centres: pd.DataFrame, grid: str = "merra2") -> pd.DataFrame:
    """``centres``: unique (lon, lat). Returns (lgd_district_code, lon, lat, weight)."""
    import geopandas as gpd
    from shapely.geometry import box

    half_lon, half_lat = GRIDS[grid]
    cells = gpd.GeoDataFrame(
        centres[["lon", "lat"]].reset_index(drop=True),
        geometry=[
            box(x - half_lon, y - half_lat, x + half_lon, y + half_lat)
            for x, y in zip(centres["lon"], centres["lat"], strict=True)
        ],
        crs=4326,
    )
    d = districts[["lgd_district_code", "geometry"]].to_crs(EQUAL_AREA)
    pieces = gpd.overlay(d, cells.to_crs(EQUAL_AREA), how="intersection", keep_geom_type=True)
    pieces["area"] = pieces.geometry.area
    w = pieces.groupby(["lgd_district_code", "lon", "lat"], as_index=False)["area"].sum()
    w["weight"] = w["area"] / w.groupby("lgd_district_code")["area"].transform("sum")
    w["grid"] = grid
    return w[["grid", "lgd_district_code", "lon", "lat", "weight"]]


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
    """District-day table with one column per parameter (missing stays NaN). ``weights`` has a
    ``grid`` column; each parameter is aggregated with its own grid's weights."""
    by_grid = {g: w.drop(columns="grid") for g, w in weights.groupby("grid")}
    frames = []
    for year in years:
        per_param = []
        for p in parameters:
            files = sorted(cache.glob(f"{p}_{year}_*.parquet"))
            if not files:
                continue
            vals = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
            vals = vals.drop_duplicates(["lon", "lat", "date"])  # box edges overlap
            w = by_grid[grid_of(p)]
            wanted = set(zip(w["lon"], w["lat"], strict=True))
            have = set(zip(vals["lon"], vals["lat"], strict=True))
            if wanted - have:  # a weighted cell absent from the data = wrong grid
                raise ValueError(
                    f"{p} {year}: {len(wanted - have)} of {len(wanted)} {grid_of(p)} cells "
                    "have no data"
                )
            per_param.append(aggregate(vals, w).rename(columns={"value": p}))
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

