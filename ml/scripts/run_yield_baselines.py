"""Phase 8: yield baselines B1-B4 + per-crop LightGBM, per lead time.

Two phases, so the test sets are never used for choices:

- ``--phase val``: tune on validation (Ridge alpha, LightGBM grid), score every model on
  validation, calibrate conformal intervals, and freeze the chosen configuration in
  ``reports/data/yield_baselines_selection.json``.
- ``--phase test``: refit the frozen configuration and score **test** and **spatial_test**
  once. A second test run of the same configuration is refused.

LightGBM models are run with seeds 0, 1, 2 (mean +- std). Metrics are per crop in native
units (MAE, RMSE, R2), with nMAE = MAE / mean yield, summarised over tier-A crops as the
median and worst decile.

Usage (from ml/)::

    uv run --no-sync python scripts/run_yield_baselines.py --phase val
    uv run --no-sync python scripts/run_yield_baselines.py --phase test
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time

import _bootstrap  # noqa: F401
import numpy as np
import pandas as pd

from krishios_ml.common.experiment_log import read_records, track_experiment
from krishios_ml.common.paths import DATA_DIR, EXPERIMENTS_DIR, REPORTS_DIR
from krishios_ml.yield_.baselines import (
    HistMean,
    LGBMModel,
    PerCropLGBM,
    Persistence,
    RidgeModel,
    conformal_q,
    interval_coverage,
    per_crop,
    summarise,
)
from krishios_ml.yield_.data import (
    HISTORY_LAG,
    MAX_RATIO,
    MIN_HISTORY,
    TARGET_CLIP,
    add_anomalies,
    build_frame,
    feature_sets,
    weather_normals,
)

LABELS = DATA_DIR / "processed" / "yield_labels" / "v1" / "labels.parquet"
FEATURES = DATA_DIR / "processed" / "yield_features" / "v1" / "season_features.parquet"
SELECTION = REPORTS_DIR / "data" / "yield_baselines_selection.json"
SEEDS = (0, 1, 2)
LEADS = (0, 30, 60, 90)
RIDGE_ALPHAS = (0.1, 1.0, 10.0, 100.0)
LGBM_GRID = [{"num_leaves": nl, "min_child_samples": mc} for nl in (31, 127) for mc in (50, 300)]
EVAL_TIERS = ("A", "B")
COVERAGE = 0.8


def lead_frames(frame: pd.DataFrame, lead: int):
    f = frame[(frame["lead_days"] == lead) & frame["eval_ok"]]
    train = f[f["split"] == "train"]
    f = add_anomalies(f, weather_normals(train))
    return {s: f[f["split"] == s].reset_index(drop=True)
            for s in ("train", "val", "test", "spatial_test")}


def score(df: pd.DataFrame, ratio: np.ndarray) -> dict:
    """Primary: ``eval_clean`` rows. ``A_all``: tier A on every ``eval_ok`` row."""
    pred = ratio * df["hist_mean"].to_numpy()
    keep = (df["tier"].isin(EVAL_TIERS) & df["eval_clean"]).to_numpy()
    table = per_crop(df[keep], pred[keep])
    every = df["tier"].isin(EVAL_TIERS).to_numpy()
    table_all = per_crop(df[every], pred[every])
    return {"A": summarise(table, ("A",)), "B": summarise(table, ("B",)),
            "A_all": summarise(table_all, ("A",)),
            "per_crop": table.round(5).to_dict(orient="records")}


def mean_std(runs: list[dict], tier: str = "A") -> dict:
    out = {}
    for k in runs[0][tier]:
        v = np.array([r[tier][k] for r in runs], dtype=float)
        out[k] = {"mean": float(v.mean()), "std": float(v.std(ddof=1)) if len(v) > 1 else 0.0}
    return out


def build_models(sel: dict, seed: int):
    fs = feature_sets()
    return [
        HistMean(), Persistence(),
        RidgeModel(fs["full"], alpha=sel["B2_ridge"]["alpha"]),
        LGBMModel(fs["full"], sel["B3_lgbm"], seed=seed, name="B3_lgbm"),
        LGBMModel(fs["weather_only"], sel["B3_lgbm"], seed=seed, name="B4_lgbm_weather"),
        PerCropLGBM(fs["full"], {"num_leaves": sel["B3_lgbm"]["num_leaves"]}, seed=seed),
    ]


def run_val(frame: pd.DataFrame) -> dict:
    fs = feature_sets()
    result, selection = {}, {}
    for lead in LEADS:
        t0 = time.time()
        d = lead_frames(frame, lead)
        tr, va = d["train"], d["val"]
        tuning = {"B2_ridge": {}, "B3_lgbm": {}}
        for a in RIDGE_ALPHAS:
            m = RidgeModel(fs["full"], alpha=a).fit(tr, va)
            tuning["B2_ridge"][str(a)] = score(va, m.predict(va))["A"]["nmae_median"]
        for i, params in enumerate(LGBM_GRID):
            m = LGBMModel(fs["full"], params, seed=0).fit(tr, va)
            tuning["B3_lgbm"][json.dumps(params)] = score(va, m.predict(va))["A"]["nmae_median"]
            print(f"lead {lead} grid {i}: {tuning['B3_lgbm'][json.dumps(params)]:.4f}")
        best_a = float(min(tuning["B2_ridge"], key=tuning["B2_ridge"].get))
        best_p = json.loads(min(tuning["B3_lgbm"], key=tuning["B3_lgbm"].get))
        sel = {"B2_ridge": {"alpha": best_a}, "B3_lgbm": best_p}
        selection[str(lead)] = sel
        models_out, q = {}, None
        for seed in SEEDS:
            for m in build_models(sel, seed):
                if seed > 0 and m.name in ("B1_hist_mean", "B1p_persistence", "B2_ridge"):
                    continue  # deterministic
                m.fit(tr, va)
                pred = m.predict(va)
                models_out.setdefault(m.name, []).append(score(va, pred))
                if m.name == "B3_lgbm" and seed == 0:
                    clean = va["eval_clean"].to_numpy()
                    q = conformal_q(va[clean], pred[clean], COVERAGE)
        result[str(lead)] = {
            "rows": {k: len(v) for k, v in d.items()},
            "tuning": tuning, "selected": sel, "conformal_q": q,
            "models": {n: {"A": mean_std(r, "A"), "B": mean_std(r, "B"),
                           "A_all": mean_std(r, "A_all"), "seeds": len(r),
                           "per_crop_seed0": r[0]["per_crop"]} for n, r in models_out.items()},
            "seconds": round(time.time() - t0, 1),
        }
        print(f"lead {lead} done in {result[str(lead)]['seconds']} s")
    return {"results": result, "selection": selection}


def selection_hash(sel: dict) -> str:
    return hashlib.sha256(json.dumps(sel, sort_keys=True).encode()).hexdigest()[:12]


def run_test(frame: pd.DataFrame, frozen: dict) -> dict:
    """Each frozen model is fitted once per seed (train, early stopping on val) and scored on
    both held-out splits."""
    result = {}
    splits = ("test", "spatial_test")
    for lead in LEADS:
        d = lead_frames(frame, lead)
        sel = frozen["selection"][str(lead)]
        q = frozen["conformal_q"][str(lead)]
        runs = {s: {} for s in splits}
        coverage = {}
        for seed in SEEDS:
            for m in build_models(sel, seed):
                if seed > 0 and m.name in ("B1_hist_mean", "B1p_persistence", "B2_ridge"):
                    continue
                m.fit(d["train"], d["val"])
                for split in splits:
                    ev = d[split]
                    pred = m.predict(ev)
                    runs[split].setdefault(m.name, []).append(score(ev, pred))
                    if m.name == "B3_lgbm" and seed == 0:
                        clean = ev["eval_clean"].to_numpy()
                        coverage[split] = interval_coverage(ev[clean], pred[clean], q)
        out = {"rows": {k: len(v) for k, v in d.items()}}
        for split in splits:
            out[split] = {"models": {n: {"A": mean_std(r, "A"), "B": mean_std(r, "B"),
                                         "A_all": mean_std(r, "A_all"), "seeds": len(r),
                                         "per_crop_seed0": r[0]["per_crop"]}
                                     for n, r in runs[split].items()},
                          "b3_interval_coverage": coverage[split]}
        result[str(lead)] = out
        print(f"lead {lead} test done", flush=True)
    return result


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=["val", "test"], required=True)
    args = ap.parse_args()
    labels, feats = pd.read_parquet(LABELS), pd.read_parquet(FEATURES)
    frame = build_frame(labels, feats)
    config = {"phase": args.phase, "leads": list(LEADS), "seeds": list(SEEDS),
              "history_lag": HISTORY_LAG, "min_history": MIN_HISTORY,
              "target": "yield / hist_mean", "target_clip": list(TARGET_CLIP),
              "primary_rows": "eval_clean (drop flagged high-side outliers and ratio > "
                              f"{MAX_RATIO:g}; keep crop failures)",
              "eval_tiers": list(EVAL_TIERS), "conformal_coverage": COVERAGE,
              "ridge_alphas": list(RIDGE_ALPHAS), "lgbm_grid": LGBM_GRID,
              "primary_metric": "median nMAE over tier-A crops (validation)",
              "dataset_run": "99682d517b17"}
    if args.phase == "test":
        frozen = json.loads(SELECTION.read_text(encoding="utf-8"))
        config["selection_hash"] = selection_hash(frozen["selection"])
        config["selection_run"] = frozen["run_id"]
        log = EXPERIMENTS_DIR / "yield_baselines.jsonl"
        if log.exists() and any(r["config"].get("phase") == "test"
                                and r["config"].get("selection_hash") == config["selection_hash"]
                                for r in read_records(log)):
            raise SystemExit("test already scored for this frozen configuration; refusing")
    with track_experiment("yield_baselines", config, seed=None,
                          split_id="apy-tierv2-ee75501cc5ef") as rec:
        if args.phase == "val":
            out = run_val(frame)
            rec.metrics = {lead: {n: v["A"] for n, v in r["models"].items()}
                           for lead, r in out["results"].items()}
            SELECTION.write_text(json.dumps({
                "run_id": rec.run_id, "selection": out["selection"],
                "conformal_q": {lead: r["conformal_q"] for lead, r in out["results"].items()},
            }, indent=1), encoding="utf-8")
        else:
            out = run_test(frame, frozen)
            rec.metrics = {lead: {s: {n: v["A"] for n, v in r[s]["models"].items()}
                                  for s in ("test", "spatial_test")}
                           for lead, r in out.items()}
        path = REPORTS_DIR / "data" / f"yield_baselines_{args.phase}_{rec.run_id}.json"
        path.write_text(json.dumps({"run_id": rec.run_id, "config": config, "results": out},
                                   indent=1, default=str), encoding="utf-8")
        rec.artifact_path = str(path.relative_to(REPORTS_DIR.parent))
    print("run_id", rec.run_id)


if __name__ == "__main__":
    main()
