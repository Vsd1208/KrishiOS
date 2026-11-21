"""Phase 10, step 1: does MODIS NDVI improve the yield baseline? (validation only)

Builds leakage-safe season NDVI features (a month counts only if it was published before the
forecast cutoff), then compares on the validation years, with the frozen Phase 8 settings:

- B3: the Phase 8 multi-crop LightGBM (history + weather);
- B3_ndvi: B3 plus NDVI;
- B4_ndvi: NDVI only, with no yield history or weather.

The test splits are not read for any score here. Paired differences are per crop, so a change
is not hidden by the median.

Usage (from ml/)::

    uv run --no-sync python scripts/run_yield_ndvi.py
"""

from __future__ import annotations

import json

import _bootstrap  # noqa: F401
import pandas as pd
from run_yield_baselines import FEATURES, LABELS, LEADS, SEEDS, SELECTION, mean_std, score

from krishios_ml.common.experiment_log import track_experiment
from krishios_ml.common.paths import DATA_DIR, REPORTS_DIR
from krishios_ml.yield_.baselines import LGBMModel
from krishios_ml.yield_.data import (
    KEYS,
    add_anomalies,
    add_ndvi,
    build_frame,
    feature_sets,
    weather_normals,
)
from krishios_ml.yield_features import modis

MONTHLY = DATA_DIR / "processed" / "yield_features" / "v1" / "district_ndvi_monthly.parquet"
SEASON = DATA_DIR / "processed" / "yield_features" / "v1" / "season_ndvi.parquet"


def season_ndvi(features: pd.DataFrame) -> pd.DataFrame:
    keys = features[[*KEYS, "lead_days", "window_start", "cutoff"]].drop_duplicates()
    out = modis.ndvi_features(pd.read_parquet(MONTHLY), keys)
    out.to_parquet(SEASON, index=False)
    return out


def paired(base: list[dict], other: list[dict]) -> dict:
    """Mean per-crop change in nMAE across seeds (negative means ``other`` is better)."""
    def table(runs):
        t = pd.concat([pd.DataFrame(r["per_crop"]) for r in runs])
        return t[t["tier"] == "A"].groupby("crop")["nmae"].mean()

    d = (table(other) - table(base)).dropna()
    return {"crops": len(d), "median_change": float(d.median()),
            "crops_improved": int((d < 0).sum()), "crops_worse": int((d > 0).sum()),
            "best_crops": d.nsmallest(5).round(4).to_dict(),
            "worst_crops": d.nlargest(5).round(4).to_dict()}


def main() -> None:
    labels, feats = pd.read_parquet(LABELS), pd.read_parquet(FEATURES)
    frozen = json.loads(SELECTION.read_text(encoding="utf-8"))
    frame = build_frame(labels, feats)
    fs = feature_sets()
    config = {"phase": "val", "leads": list(LEADS), "seeds": list(SEEDS),
              "selection_run": frozen["run_id"], "publication_lag_days":
              modis.PUBLICATION_LAG_DAYS, "models": ["B3", "B3_ndvi", "B4_ndvi"]}
    with track_experiment("yield_ndvi", config, seed=None,
                          split_id="apy-tierv2-ee75501cc5ef") as rec:
        ndvi = season_ndvi(feats)
        results = {}
        for lead in LEADS:
            f = frame[(frame["lead_days"] == lead) & frame["eval_ok"]]
            f = f[f["split"].isin(["train", "val"])]
            f = add_anomalies(f, weather_normals(f[f["split"] == "train"]))
            f = add_ndvi(f, ndvi)
            tr = f[f["split"] == "train"].reset_index(drop=True)
            va = f[f["split"] == "val"].reset_index(drop=True)
            params = frozen["selection"][str(lead)]["B3_lgbm"]
            runs: dict[str, list[dict]] = {}
            for seed in SEEDS:
                for name, cols in (("B3", fs["full"]), ("B3_ndvi", fs["full_ndvi"]),
                                   ("B4_ndvi", fs["ndvi_only"])):
                    m = LGBMModel(cols, params, seed=seed, name=name).fit(tr, va)
                    runs.setdefault(name, []).append(score(va, m.predict(va)))
                    print(f"lead {lead} seed {seed} {name}: "
                          f"{runs[name][-1]['A']['nmae_median']:.4f}", flush=True)
            results[str(lead)] = {
                "rows": {"train": len(tr), "val": len(va)},
                "ndvi_coverage": {"train": float(tr["ndvi_last"].notna().mean()),
                                  "val": float(va["ndvi_last"].notna().mean())},
                "models": {n: {"A": mean_std(r, "A"), "B": mean_std(r, "B")}
                           for n, r in runs.items()},
                "paired_vs_B3": {n: paired(runs["B3"], runs[n]) for n in ("B3_ndvi",)},
            }
        rec.metrics = {k: {n: m["A"]["nmae_median"]["mean"] for n, m in v["models"].items()}
                       for k, v in results.items()}
        path = REPORTS_DIR / "data" / f"yield_ndvi_val_{rec.run_id}.json"
        path.write_text(json.dumps({"run_id": rec.run_id, "config": config, "results": results},
                                   indent=1, default=float), encoding="utf-8")
        rec.artifact_path = str(path.relative_to(REPORTS_DIR.parent))
    print(json.dumps(rec.metrics, indent=1, default=float))
    print("run_id", rec.run_id)


if __name__ == "__main__":
    main()
