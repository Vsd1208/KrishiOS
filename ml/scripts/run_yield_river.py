"""Phase 10: does upstream river flow add yield skill beyond global climate? (no test years)

Monthly modelled discharge (mean and highest day, as anomalies) is routed to the regions each
river may affect. The model with real river inputs is compared with the same model when only the
river inputs come from the wrong years; the global climate indices stay real. A month is used
only if it ended at least 30 days before the forecast cutoff.

Usage (from ml/)::

    uv run --no-sync python scripts/run_yield_river.py --placebos 20
"""

from __future__ import annotations

import argparse
import json

import _bootstrap  # noqa: F401
import numpy as np
import pandas as pd
from run_yield_baselines import FEATURES, LABELS, LEADS, SEEDS, SELECTION
from run_yield_climate import FOLDS, climate_table, region_errors, with_climate
from run_yield_climate_tests import REGION_NAMES, p_value

from krishios_ml.common.experiment_log import track_experiment
from krishios_ml.common.paths import DATA_DIR, REPORTS_DIR
from krishios_ml.yield_.baselines import LGBMModel
from krishios_ml.yield_.data import add_anomalies, build_frame, feature_sets, weather_normals
from krishios_ml.yield_features import climate

DAILY = DATA_DIR / "processed" / "yield_features" / "v1" / "river_discharge_daily.parquet"
JOIN = ["crop_year", "season", "lead_days"]


def river_table(feats: pd.DataFrame) -> pd.DataFrame:
    keys = feats[[*JOIN, "cutoff"]].drop_duplicates(JOIN)
    keys = keys.assign(cutoff=pd.to_datetime(keys["cutoff"]))
    series = climate.standardize(climate.river_monthly(pd.read_parquet(DAILY)))
    values = climate.driver_features(series, keys["cutoff"], climate.RIVER_DRIVERS)
    return keys.merge(values, on="cutoff", how="left").drop(columns="cutoff")


def add_rivers(df: pd.DataFrame, rivers: pd.DataFrame, year_map: dict | None = None
               ) -> pd.DataFrame:
    left = df.assign(_year=df["crop_year"].map(year_map) if year_map else df["crop_year"])
    right = rivers.rename(columns={"crop_year": "_year"})
    out = left.merge(right, on=["_year", "season", "lead_days"], how="left").drop(columns="_year")
    return climate.route_drivers(out, climate.RIVER_DRIVERS)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--placebos", type=int, default=20)
    args = ap.parse_args()
    labels, feats = pd.read_parquet(LABELS), pd.read_parquet(FEATURES)
    frozen = json.loads(SELECTION.read_text(encoding="utf-8"))
    table, rivers = climate_table(feats), river_table(feats)
    frame = build_frame(labels, feats)
    frame = frame[frame["split"].isin(["train", "val"]) & frame["eval_ok"]]
    del labels, feats
    glob = [*feature_sets()["full"], *climate.FEATURES]
    with_rivers = [*glob, *climate.RIVER_FEATURES]
    years = np.array(sorted(rivers["crop_year"].unique()))
    maps = [dict(zip(years.tolist(), np.random.default_rng(7000 + k).permutation(years).tolist(),
                     strict=True)) for k in range(args.placebos)]
    config = {"folds": FOLDS, "leads": list(LEADS), "seeds": list(SEEDS),
              "placebos": args.placebos, "rivers": list(climate.RIVER_POINTS),
              "selection_run": frozen["run_id"], "source": "GloFAS via Open-Meteo Flood API"}
    errors: dict[str, list[list[dict]]] = {}

    def add(name: str, run: int, value: dict) -> None:
        store = errors.setdefault(name, [])
        while len(store) <= run:
            store.append([])
        store[run].append(value)

    with track_experiment("yield_river", config, seed=None,
                          split_id="apy-tierv2-ee75501cc5ef") as rec:
        for lead in LEADS:
            params = frozen["selection"][str(lead)]["B3_lgbm"]
            for start, end in FOLDS:
                f = frame[(frame["lead_days"] == lead) & (frame["crop_year"] <= end)]
                f = add_anomalies(f, weather_normals(f[f["crop_year"] < start]))
                base = with_climate(f, table)
                real = add_rivers(base, rivers)

                def fit(name: str, run: int, data: pd.DataFrame, cols: list[str], seed: int,
                        start: int = start, params: dict = params):
                    tr = data[data["crop_year"] < start].reset_index(drop=True)
                    va = data[data["crop_year"] >= start].reset_index(drop=True)
                    m = LGBMModel(cols, params, seed=seed, name=name).fit(tr, va)
                    add(name, run, region_errors(va, m.predict(va)))

                for i, seed in enumerate(SEEDS):
                    fit("global", i, real, glob, seed)
                    fit("global_rivers", i, real, with_rivers, seed)
                for k, year_map in enumerate(maps):
                    fit("placebo_rivers", k, add_rivers(base, rivers, year_map), with_rivers,
                        SEEDS[k % len(SEEDS)])
                print(f"lead {lead} {start}-{end} done", flush=True)
        means = {n: pd.DataFrame([pd.DataFrame(r).mean() for r in runs])
                 for n, runs in errors.items()}
        out = {}
        for g in REGION_NAMES:
            placebo = means["placebo_rivers"][g].to_numpy()
            real_error = float(means["global_rivers"][g].mean())
            out[g] = {"global": float(means["global"][g].mean()), "global_rivers": real_error,
                      "placebo_mean": float(placebo.mean()), "placebo_best": float(placebo.min()),
                      "p_rivers_vs_placebo": p_value(real_error, placebo)}
        rec.metrics = out
        path = REPORTS_DIR / "data" / f"yield_river_{rec.run_id}.json"
        path.write_text(json.dumps({"run_id": rec.run_id, "config": config, "regions": out},
                                   indent=1, default=float), encoding="utf-8")
        rec.artifact_path = str(path.relative_to(REPORTS_DIR.parent))
    print(json.dumps(out, indent=1, default=float))
    print("run_id", rec.run_id)


if __name__ == "__main__":
    main()
