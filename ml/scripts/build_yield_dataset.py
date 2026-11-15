"""Phase 7: build the yield modelling dataset (labels, district daily weather, season features).

Stages (each writes versioned Parquet keyed by LGD district code; the run is logged):

- ``boundaries`` -> reference/district_polygon_crosswalk.csv (+ unmatched LGD list) and
  data/processed/boundaries/v1/districts.parquet (geoBoundaries ADM2 polygons with LGD codes)
- ``weights``  -> data/processed/yield_features/v1/power_cell_weights.parquet (one table per
  POWER grid: MERRA-2 0.5x0.625 for meteorology, CERES 1x1 for solar radiation)
- ``labels``   -> data/processed/yield_labels/v1/labels.parquet (tier v2, splits, flags)
- ``daily``    -> data/processed/yield_features/v1/district_daily/<year>.parquet
- ``features`` -> data/processed/yield_features/v1/season_features.parquet (one row per
  district x crop_year x season x lead; weather only, nothing after the cutoff)

Usage (from ml/)::

    uv run --no-sync python scripts/build_yield_dataset.py --stage all
"""

from __future__ import annotations

import argparse
import json

import _bootstrap  # noqa: F401
import pandas as pd

from krishios_ml.common.experiment_log import track_experiment
from krishios_ml.common.paths import DATA_DIR, ML_ROOT, REPORTS_DIR
from krishios_ml.yield_features.boundaries import load_polygons, match_lgd
from krishios_ml.yield_features.features import LEADS, PRE_DAYS, build
from krishios_ml.yield_features.power import BOXES, PARAMETERS
from krishios_ml.yield_features.zonal import GRIDS, build_daily, cell_weights, grid_of
from krishios_ml.yield_labels.dataset import EAST_RICE_STATES, build_labels

AUDIT_RUN = "ee75501cc5ef"  # Phase 6 run of record (tier v2)
SPLIT = {"val_from": 2016, "test_from": 2019, "spatial_share": 0.10}
LABELS = DATA_DIR / "processed" / "yield_labels" / "v1"
FEATS = DATA_DIR / "processed" / "yield_features" / "v1"
CACHE = DATA_DIR / "raw" / "nasa_power" / "daily_regional"
BOUNDARIES_RAW = DATA_DIR / "raw" / "boundaries" / "20261114"
REF = ML_ROOT / "reference"


def stage_boundaries() -> dict:
    polys = load_polygons(BOUNDARIES_RAW / "geoBoundaries-IND-ADM2.geojson",
                          BOUNDARIES_RAW / "geoBoundaries-IND-ADM1.geojson")
    matches, unmatched = match_lgd(polys, REF / "lgd_districts.csv",
                                   REF / "district_aliases.csv",
                                   REF / "district_polygon_overrides.csv")
    names = pd.read_csv(REF / "lgd_districts.csv").set_index("lgd_district_code")["district_name"]
    matches["lgd_name"] = matches["lgd_district_code"].map(names)
    matches["review"] = ~matches["match"].isin(["name", "alias"])
    matches.to_csv(REF / "district_polygon_crosswalk.csv", index=False)
    unmatched.to_csv(REF / "district_polygon_unmatched_lgd.csv", index=False)
    coded = polys.merge(matches[["shapeID", "lgd_district_code", "match"]], on="shapeID")
    coded = coded.dropna(subset=["lgd_district_code"]).astype({"lgd_district_code": "int64"})
    out = DATA_DIR / "processed" / "boundaries" / "v1"
    out.mkdir(parents=True, exist_ok=True)
    coded.to_parquet(out / "districts.parquet", index=False)
    shared = coded.groupby("lgd_district_code").size()
    return {"polygons": len(polys), "coded_polygons": len(coded),
            "lgd_codes_with_polygon": int(shared.size),
            "codes_with_several_polygons": {int(k): int(v) for k, v in shared[shared > 1].items()},
            "match_methods": matches["match"].str.split(":").str[0].value_counts().to_dict(),
            "override_relations": matches.loc[matches["match"].str.startswith("override"),
                                              "match"].value_counts().to_dict(),
            "unmatched_lgd": len(unmatched)}


def stage_weights(year: int = 2010) -> dict:
    import geopandas as gpd

    districts = gpd.read_parquet(DATA_DIR / "processed" / "boundaries" / "v1" / "districts.parquet")
    districts = districts.dropna(subset=["lgd_district_code"])
    tables, stats = [], {}
    for grid in GRIDS:
        param = next(p for p in PARAMETERS if grid_of(p) == grid)
        centres = pd.concat([pd.read_parquet(f, columns=["lon", "lat"])
                             for f in CACHE.glob(f"{param}_{year}_*.parquet")]).drop_duplicates()
        w = cell_weights(districts, centres, grid)
        tables.append(w)
        per = w.groupby("lgd_district_code").size()
        stats[grid] = {"centres": len(centres), "districts": int(per.size),
                       "cells_per_district_median": float(per.median()),
                       "single_cell_districts": int((per == 1).sum())}
    pd.concat(tables, ignore_index=True).to_parquet(FEATS / "power_cell_weights.parquet",
                                                    index=False)
    return stats


def stage_labels() -> dict:
    audit = json.loads((REPORTS_DIR / "data" / f"yield_label_audit_{AUDIT_RUN}.json")
                       .read_text(encoding="utf-8"))
    tiers = {f"{s['crop']}|{s['season']}": s["tier"] for s in audit["series"]}
    labels = build_labels(pd.read_parquet(LABELS / "apy.parquet"), tiers, SPLIT)
    labels.to_parquet(LABELS / "labels.parquet", index=False)
    return {
        "rows": len(labels),
        "series": int(labels.groupby(["crop_canonical", "season"]).ngroups),
        "crops": int(labels["crop_canonical"].nunique()),
        "districts": int(labels["lgd_district_code"].nunique()),
        "years": [int(labels["crop_year"].min()), int(labels["crop_year"].max())],
        "by_split": labels["split"].value_counts().to_dict(),
        "by_tier": labels["tier"].value_counts().to_dict(),
        "by_season": labels["season"].value_counts().to_dict(),
        "outlier_rate": round(float(labels["outlier_flag"].mean()), 4),
        "east_rice_annual_rows": int(((labels["crop_canonical"] == "paddy")
                                      & labels["state_name"].isin(EAST_RICE_STATES)).sum()),
    }


def stage_daily(years: range) -> dict:
    weights = pd.read_parquet(FEATS / "power_cell_weights.parquet")
    out = FEATS / "district_daily"
    out.mkdir(parents=True, exist_ok=True)
    done, coverage = [], {}
    for year in years:
        if len(list(CACHE.glob(f"*_{year}_*.parquet"))) < len(PARAMETERS) * len(BOXES):
            print(f"{year}: POWER cache incomplete, skipped")
            continue
        d = build_daily(CACHE, weights, PARAMETERS, range(year, year + 1))
        d.to_parquet(out / f"{year}.parquet", index=False)
        done.append(year)
        coverage[year] = {p: round(float(d[p].notna().mean()), 4) for p in PARAMETERS}
        print(year, len(d), coverage[year])
    return {"years": done, "districts": int(weights["lgd_district_code"].nunique()),
            "non_missing_share": coverage}


def stage_features() -> dict:
    labels = pd.read_parquet(LABELS / "labels.parquet")
    files = sorted((FEATS / "district_daily").glob("*.parquet"))
    daily = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
    have = set(int(f.stem) for f in files)
    feats = build(daily, labels)
    feats.to_parquet(FEATS / "season_features.parquet", index=False)
    joined = labels.merge(feats[feats["lead_days"] == 0], how="left",
                          on=["lgd_district_code", "crop_year", "season"])
    with_weather = joined["has_weather"].fillna(False).astype(bool)
    return {
        "daily_years": sorted(have), "feature_rows": len(feats),
        "keys": int(feats.drop_duplicates(["lgd_district_code", "crop_year", "season"]).shape[0]),
        "label_rows_with_weather": round(float(with_weather.mean()), 4),
        "label_rows_with_weather_by_split": joined.assign(w=with_weather)
        .groupby("split")["w"].mean().round(4).to_dict(),
        "coverage_median_by_lead": feats.groupby("lead_days")[
            ["rain_coverage", "temp_coverage", "srad_mean_coverage"]].median().round(4)
        .to_dict(orient="index"),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="all",
                    choices=["boundaries", "weights", "labels", "daily", "features", "all"])
    ap.add_argument("--start", type=int, default=1997)
    ap.add_argument("--end", type=int, default=2024)
    args = ap.parse_args()
    config = {"stage": args.stage, "audit_run": AUDIT_RUN, "split": SPLIT,
              "east_rice_annual": list(EAST_RICE_STATES), "parameters": list(PARAMETERS),
              "leads": list(LEADS), "pre_days": PRE_DAYS, "years": [args.start, args.end],
              "weather_source": "NASA POWER daily regional, area-weighted (MERRA-2 0.5x0.625 "
                                "meteorology; CERES 1x1 solar radiation)",
              "boxes": len(BOXES)}
    with track_experiment("yield_dataset", config, seed=None,
                          split_id=f"apy-tierv2-{AUDIT_RUN}") as rec:
        metrics: dict = {}
        if args.stage in ("boundaries", "all"):
            metrics["boundaries"] = stage_boundaries()
        if args.stage in ("weights", "all"):
            metrics["weights"] = stage_weights()
        if args.stage in ("labels", "all"):
            metrics["labels"] = stage_labels()
        if args.stage in ("daily", "all"):
            metrics["daily"] = stage_daily(range(args.start, args.end + 1))
        if args.stage in ("features", "all"):
            metrics["features"] = stage_features()
        rec.metrics = metrics
        out = REPORTS_DIR / "data" / f"yield_dataset_{rec.run_id}.json"
        out.write_text(json.dumps({"run_id": rec.run_id, "config": config, "metrics": metrics},
                                  indent=1, default=str), encoding="utf-8")
        rec.artifact_path = str(out.relative_to(REPORTS_DIR.parent))
    print(json.dumps(metrics, indent=1, default=str)[:4000])
    print("run_id", rec.run_id)


if __name__ == "__main__":
    main()
