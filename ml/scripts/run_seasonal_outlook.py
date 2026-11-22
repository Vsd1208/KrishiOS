"""Phase 10d: hindcast of the district seasonal outlook (El Nino / IOD analog years).

Every target year is forecast from earlier years only. Settings are chosen on the development
years (1981-2005) by mean RPSS over seasons and variables; the test years (2006-2024) are scored
once with the chosen settings (``--stage test`` refuses to run twice for the same settings).

Usage (from ml/)::

    python scripts/run_seasonal_outlook.py --stage dev
    python scripts/run_seasonal_outlook.py --stage test   # once, after dev
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json

import _bootstrap  # noqa: F401
import pandas as pd

from krishios_ml.common.experiment_log import read_records, track_experiment
from krishios_ml.common.paths import DATA_DIR, EXPERIMENTS_DIR, REPORTS_DIR
from krishios_ml.seasonal.outlook import (
    Config,
    hindcast_year,
    predictor_states,
    reliability,
    score,
)
from krishios_ml.yield_features.climate import parse_year_table

TABLE = DATA_DIR / "processed" / "seasonal" / "v1" / "district_seasons.parquet"
INDICES = DATA_DIR / "raw" / "climate_indices"
DEV, TEST = range(1981, 2006), range(2006, 2025)
SEASONS = ("JJAS", "OND", "JF", "MAM")
VARIABLES = ("rain", "tmax", "tmin")
GRID = {"k": (3.0, 6.0, 12.0), "lam": (0.0, 0.5, 1.0), "detrend": (False, True),
        "use_iod": (False, True)}
# Revision 2 (after dev run c9c6c9d5f781 found no analog skill): add optimal climate normals
# (recent-years category frequencies) and a blend; still chosen on the development years only.
GRID_V2 = [dict(method=m, n_recent=n, k=k, lam=lam)
           for m in ("analog", "ocn", "blend") for n in (10, 15) for k in (3.0, 6.0, 12.0)
           for lam in (0.0, 1.0) if not (m == "analog" and n == 15)]


def load_indices() -> pd.DataFrame:
    return pd.concat([parse_year_table((INDICES / f"{n}.txt").read_text(encoding="utf-8",
                                                                         errors="replace"), n)
                      for n in ("oni", "dmi")], ignore_index=True)


def run(table: pd.DataFrame, indices: pd.DataFrame, years: range, cfg: Config,
        variables=VARIABLES, seasons=SEASONS) -> pd.DataFrame:
    frames = []
    for season in seasons:
        states = predictor_states(indices, season, range(1951, years.stop))
        sub = table[table["season"] == season]
        regions = sub.drop_duplicates("lgd_district_code").set_index("lgd_district_code")["state"]
        for variable in variables:
            values = sub.pivot(index="lgd_district_code", columns="year", values=variable)
            values = values.dropna(how="all")
            reg = regions.reindex(values.index).fillna("unknown").to_numpy()
            for y in years:
                f = hindcast_year(values, states, reg, y, cfg)
                if f is not None:
                    f["season"], f["variable"] = season, variable
                    frames.append(f)
    return pd.concat(frames, ignore_index=True)


def summary(frame: pd.DataFrame) -> dict:
    out = {"all": score(frame)}
    for (season, variable), g in frame.groupby(["season", "variable"]):
        out[f"{season}/{variable}"] = score(g)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["dev", "test"], required=True)
    ap.add_argument("--grid", choices=["v1", "v2"], default="v2")
    args = ap.parse_args()
    table = pd.read_parquet(TABLE)
    indices = load_indices()
    log = EXPERIMENTS_DIR / "seasonal_outlook.jsonl"

    if args.stage == "dev":
        grid = (GRID_V2 if args.grid == "v2" else
                [dict(k=k, lam=lam, detrend=d, use_iod=i)
                 for k, lam, d, i in itertools.product(*GRID.values())])
        config = {"stage": "dev", "years": [DEV.start, DEV.stop - 1], "grid": grid,
                  "selection": "mean RPSS over the 12 season x variable cells"}
        with track_experiment("seasonal_outlook", config, seed=None,
                              split_id="hindcast-expanding") as rec:
            results = []
            for settings in grid:
                s = summary(run(table, indices, DEV, Config(**settings)))
                cells = [v["rpss"] for key, v in s.items() if key != "all"]
                results.append({"config": settings,
                                "mean_cell_rpss": round(sum(cells) / len(cells), 4),
                                "pooled": s["all"], "cells": s})
                print(settings, results[-1]["mean_cell_rpss"], flush=True)
            best = max(results, key=lambda r: r["mean_cell_rpss"])
            rec.metrics = {"best": best["config"], "best_mean_cell_rpss": best["mean_cell_rpss"],
                           "best_cells": {k: v["rpss"] for k, v in best["cells"].items()}}
            path = REPORTS_DIR / "data" / f"seasonal_outlook_dev_{rec.run_id}.json"
            path.write_text(json.dumps({"run_id": rec.run_id, "config": config,
                                        "results": results, "best": best}, indent=1),
                            encoding="utf-8")
            rec.artifact_path = str(path.relative_to(REPORTS_DIR.parent))
        print(json.dumps(rec.metrics, indent=1))
        print("run_id", rec.run_id)
        return

    dev = [r for r in read_records(log) if r["config"].get("stage") == "dev"]
    if not dev:
        raise SystemExit("run --stage dev first")
    chosen = dev[-1]["metrics"]["best"]
    config = {"stage": "test", "years": [TEST.start, TEST.stop - 1], "settings": chosen,
              "chosen_by_run": dev[-1]["run_id"]}
    config["config_hash"] = hashlib.sha256(json.dumps(config, sort_keys=True).encode()
                                           ).hexdigest()[:12]
    if any(r["config"].get("config_hash") == config["config_hash"] for r in read_records(log)):
        raise SystemExit("the test years were already scored with these settings")
    with track_experiment("seasonal_outlook", config, seed=None,
                          split_id="hindcast-expanding") as rec:
        frame = run(table, indices, TEST, Config(**chosen))
        s = summary(frame)
        rel = {f"{season}/{variable}": reliability(g)
               for (season, variable), g in frame.groupby(["season", "variable"])}
        rec.metrics = {k: v["rpss"] for k, v in s.items()}
        path = REPORTS_DIR / "data" / f"seasonal_outlook_test_{rec.run_id}.json"
        path.write_text(json.dumps({"run_id": rec.run_id, "config": config, "scores": s,
                                    "reliability_above": rel}, indent=1), encoding="utf-8")
        rec.artifact_path = str(path.relative_to(REPORTS_DIR.parent))
    print(json.dumps(s, indent=1))
    print("run_id", rec.run_id)


if __name__ == "__main__":
    main()
