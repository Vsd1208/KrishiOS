"""Phase 10: permutation tests for the climate drivers (no test years).

Two questions, over the same forward-chaining periods and leads as ``run_yield_climate.py``:

1. Do the global and regional drivers beat the same inputs taken from the wrong years?
2. Does Nepal rainfall add anything for Uttar Pradesh and Bihar beyond the global indices? Here
   only the Nepal inputs are moved to the wrong years, and the global indices stay real.

The statistic is the ratio error averaged over all period x lead combinations. The one-sided
p-value is (1 + placebos at least as good as the real model) / (1 + placebos). Five regions are
examined, so a Bonferroni threshold of 0.01 corresponds to a 0.05 family-wise level.

Usage (from ml/)::

    uv run --no-sync python scripts/run_yield_climate_tests.py --placebos 20
"""

from __future__ import annotations

import argparse
import json

import _bootstrap  # noqa: F401
import numpy as np
import pandas as pd
from run_yield_baselines import FEATURES, LABELS, LEADS, SEEDS, SELECTION
from run_yield_climate import FOLDS, climate_table, region_errors, with_climate

from krishios_ml.common.experiment_log import track_experiment
from krishios_ml.common.paths import REPORTS_DIR
from krishios_ml.yield_.baselines import LGBMModel
from krishios_ml.yield_.data import add_anomalies, build_frame, feature_sets, weather_normals
from krishios_ml.yield_features import climate

NEPAL = ["drv_rain_nepal_last", "drv_rain_nepal_mean3"]
REGION_NAMES = ["all_india", *climate.REGIONS]


def p_value(real: float, placebo: np.ndarray) -> float:
    """Lower error is better."""
    return float((1 + int((placebo <= real).sum())) / (1 + len(placebo)))


def move_nepal(df: pd.DataFrame, table: pd.DataFrame, year_map: dict) -> pd.DataFrame:
    keys = ["crop_year", "season", "lead_days"]
    left = df.drop(columns=NEPAL).assign(_year=df["crop_year"].map(year_map))
    right = table[keys + NEPAL].rename(columns={"crop_year": "_year"})
    out = left.merge(right, on=["_year", "season", "lead_days"], how="left").drop(columns="_year")
    outside = ~out["lgd_state_code"].astype(int).isin(climate.GANGA_EAST)
    out.loc[outside, NEPAL] = np.nan
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--placebos", type=int, default=20)
    ap.add_argument("--nepal-only", action="store_true",
                    help="only the Nepal question: global vs global+Nepal and Nepal placebos")
    args = ap.parse_args()
    labels, feats = pd.read_parquet(LABELS), pd.read_parquet(FEATURES)
    frozen = json.loads(SELECTION.read_text(encoding="utf-8"))
    table = climate_table(feats)
    frame = build_frame(labels, feats)
    frame = frame[frame["split"].isin(["train", "val"]) & frame["eval_ok"]]
    del labels, feats
    base = feature_sets()["full"]
    glob = [*base, *climate.FEATURES]
    regional = [*glob, *climate.DRIVER_FEATURES]
    with_nepal = [*glob, *NEPAL]
    years = np.array(sorted(table["crop_year"].unique()))
    maps = [dict(zip(years.tolist(), np.random.default_rng(5000 + k).permutation(years).tolist(),
                     strict=True)) for k in range(args.placebos)]
    config = {"folds": FOLDS, "leads": list(LEADS), "seeds": list(SEEDS),
              "placebos": args.placebos, "nepal_only": args.nepal_only,
              "selection_run": frozen["run_id"],
              "statistic": "ratio MAE on clean tier A/B rows, mean over period x lead"}
    errors: dict[str, list[list[dict]]] = {}

    def add(name: str, run: int, value: dict) -> None:
        store = errors.setdefault(name, [])
        while len(store) <= run:
            store.append([])
        store[run].append(value)

    with track_experiment("yield_climate_tests", config, seed=None,
                          split_id="apy-tierv2-ee75501cc5ef") as rec:
        for lead in LEADS:
            params = frozen["selection"][str(lead)]["B3_lgbm"]
            for start, end in FOLDS:
                f = frame[(frame["lead_days"] == lead) & (frame["crop_year"] <= end)]
                f = add_anomalies(f, weather_normals(f[f["crop_year"] < start]))
                real = with_climate(f, table)

                def fit(name: str, run: int, data: pd.DataFrame, cols: list[str], seed: int,
                        start: int = start, params: dict = params):
                    tr = data[data["crop_year"] < start].reset_index(drop=True)
                    va = data[data["crop_year"] >= start].reset_index(drop=True)
                    m = LGBMModel(cols, params, seed=seed, name=name).fit(tr, va)
                    add(name, run, region_errors(va, m.predict(va)))

                models = (("global", glob), ("global_nepal", with_nepal))
                if not args.nepal_only:
                    models = (("base", base), *models, ("regional", regional))
                for i, seed in enumerate(SEEDS):
                    for name, cols in models:
                        fit(name, i, real, cols, seed)
                for k, year_map in enumerate(maps):
                    seed = SEEDS[k % len(SEEDS)]
                    if not args.nepal_only:
                        fit("placebo_all", k, with_climate(f, table, year_map), regional, seed)
                    fit("placebo_nepal", k, move_nepal(real, table, year_map), with_nepal, seed)
                print(f"lead {lead} {start}-{end} done", flush=True)
        run_means = {n: pd.DataFrame([pd.DataFrame(r).mean() for r in runs])
                     for n, runs in errors.items()}
        mean = {n: t.mean() for n, t in run_means.items()}
        out: dict = {"regions": {}}
        for g in REGION_NAMES:
            pn = run_means["placebo_nepal"][g].to_numpy()
            row = {n: float(mean[n][g]) for n in ("base", "global", "global_nepal", "regional")
                   if n in mean}
            row.update(placebo_nepal_mean=float(pn.mean()), placebo_nepal_best=float(pn.min()),
                       p_nepal_vs_placebo=p_value(mean["global_nepal"][g], pn))
            if "placebo_all" in run_means:
                pa = run_means["placebo_all"][g].to_numpy()
                row.update(placebo_all_mean=float(pa.mean()), placebo_all_best=float(pa.min()),
                           p_regional_vs_placebo=p_value(mean["regional"][g], pa))
            out["regions"][g] = row
        by_fold = {}
        for name in [n for n in ("base", "global", "global_nepal", "regional") if n in errors]:
            rows = errors[name]
            keys = [f"{lead}:{s}-{e}" for lead in LEADS for s, e in FOLDS]
            by_fold[name] = {k: float(np.mean([r[j]["ganga_east"] for r in rows]))
                             for j, k in enumerate(keys)}
        out["ganga_east_by_period"] = by_fold
        rec.metrics = out["regions"]
        path = REPORTS_DIR / "data" / f"yield_climate_tests_{rec.run_id}.json"
        path.write_text(json.dumps({"run_id": rec.run_id, "config": config, **out}, indent=1,
                                   default=float), encoding="utf-8")
        rec.artifact_path = str(path.relative_to(REPORTS_DIR.parent))
    print(json.dumps(out["regions"], indent=1, default=float))
    print("run_id", rec.run_id)


if __name__ == "__main__":
    main()
