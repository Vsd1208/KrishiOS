"""Phase 10d: district seasonal rainfall and temperature from IMD gridded data, 1951-2024.

For every LGD district, year and IMD season (JJAS, OND, JF, MAM): total rainfall (mm) and mean
daily Tmax / Tmin (deg C). Grid cells are weighted to districts by overlap area (equal-area
projection), as for the yield features; a district-season uses only cells with complete data
for that season. Input: ``data/raw/imd`` (download_imd_gridded.py). Output:
``data/processed/seasonal/v1/district_seasons.parquet``.

Usage (from ml/)::

    python scripts/build_imd_district_seasons.py
"""

from __future__ import annotations

import json

import _bootstrap  # noqa: F401
import numpy as np
import pandas as pd

from krishios_ml.common.experiment_log import track_experiment
from krishios_ml.common.paths import DATA_DIR, REPORTS_DIR
from krishios_ml.seasonal.imd import GRID_OF, SEASONS, read_year, season_cells
from krishios_ml.yield_features.zonal import GRIDS, cell_weights

RAW = DATA_DIR / "raw" / "imd"
DISTRICTS = DATA_DIR / "processed" / "boundaries" / "v1" / "districts.parquet"
OUT = DATA_DIR / "processed" / "seasonal" / "v1"
YEARS = range(1951, 2025)
VARIABLES = ("rain", "tmax", "tmin")


def weights_for(variable: str, districts) -> tuple[pd.DataFrame, np.ndarray]:
    """District weights of the land cells of this variable's grid, and those cells' (i, j)."""
    grid = GRID_OF[variable]
    GRIDS.setdefault(f"imd_{grid.step}", (grid.step / 2, grid.step / 2))
    sample = season_cells(read_year(RAW / variable / "2000.grd", grid, 2000), 2000, variable)
    land = np.argwhere(~np.isnan(sample["JJAS"]))
    centres = pd.DataFrame({"lon": grid.lons[land[:, 1]], "lat": grid.lats[land[:, 0]]})
    w = cell_weights(districts, centres, f"imd_{grid.step}")
    index = {(round(lon, 3), round(lat, 3)): k for k, (lon, lat) in
             enumerate(zip(centres["lon"], centres["lat"], strict=True))}
    w["cell"] = [index[(round(x, 3), round(y, 3))] for x, y in zip(w["lon"], w["lat"],
                                                                   strict=True)]
    return w, land


def district_values(cells: np.ndarray, land: np.ndarray, w: pd.DataFrame) -> pd.Series:
    """Weighted mean over a district's cells that have a value (renormalised weights)."""
    v = cells[land[:, 0], land[:, 1]][w["cell"].to_numpy()]
    ok = ~np.isnan(v)
    df = pd.DataFrame({"d": w["lgd_district_code"].to_numpy()[ok],
                       "wv": (w["weight"].to_numpy() * v)[ok], "w": w["weight"].to_numpy()[ok]})
    g = df.groupby("d").sum()
    return g["wv"] / g["w"]


def main() -> None:
    import geopandas as gpd

    districts = gpd.read_parquet(DISTRICTS).dissolve(by="lgd_district_code",
                                                     aggfunc="first").reset_index()
    config = {"years": [YEARS.start, YEARS.stop - 1], "seasons": SEASONS,
              "variables": VARIABLES, "aggregation": "area-weighted cells, complete seasons only"}
    with track_experiment("seasonal_district_build", config, seed=None,
                          split_id="imd-1951-2024") as rec:
        frames = []
        coverage = {}
        for variable in VARIABLES:
            w, land = weights_for(variable, districts)
            coverage[variable] = int(w["lgd_district_code"].nunique())
            grid = GRID_OF[variable]
            for year in YEARS:
                cells = season_cells(read_year(RAW / variable / f"{year}.grd", grid, year),
                                     year, variable)
                for season, grid_values in cells.items():
                    s = district_values(grid_values, land, w)
                    frames.append(pd.DataFrame({"lgd_district_code": s.index.astype("int64"),
                                                "year": year, "season": season,
                                                "variable": variable,
                                                "value": s.to_numpy().astype("float32")}))
            print(variable, "done", flush=True)
        long = pd.concat(frames, ignore_index=True)
        table = long.pivot_table(index=["lgd_district_code", "year", "season"],
                                 columns="variable", values="value").reset_index()
        states = districts.set_index("lgd_district_code")["state_2011"]
        table["state"] = table["lgd_district_code"].map(states)
        OUT.mkdir(parents=True, exist_ok=True)
        table.to_parquet(OUT / "district_seasons.parquet", index=False)
        jjas = table[table["season"] == "JJAS"].groupby("year")["rain"].mean()
        rec.metrics = {"rows": len(table), "districts": coverage,
                       "jjas_mean_rain_mm_by_decade": {
                           f"{d}s": round(float(jjas[(jjas.index >= d) & (jjas.index < d + 10)]
                                                .mean()), 1) for d in range(1950, 2030, 10)}}
        path = REPORTS_DIR / "data" / f"seasonal_district_build_{rec.run_id}.json"
        path.write_text(json.dumps({"run_id": rec.run_id, "config": config, **rec.metrics},
                                   indent=1), encoding="utf-8")
        rec.artifact_path = str(path.relative_to(REPORTS_DIR.parent))
    print(json.dumps(rec.metrics, indent=1))
    print("run_id", rec.run_id)


if __name__ == "__main__":
    main()
