"""Phase 8 batch export: serving forecasts from the validated B3 multi-crop LightGBM.

- The model for each target lead uses the configuration frozen on validation
  (``reports/data/yield_baselines_selection.json``), refitted on every labelled row with the
  validated number of boosting rounds.
- Inputs come from the same sources as training: NASA POWER (recent cache, same grid and
  aggregation) and APY yield history with the same 2-year lag. Live Open-Meteo weather is never
  used (no train/serve skew).
- Tier C, too little history or no weather -> an abstention with no number. Tier B, missing
  weather or a stale series -> ``requires_human_review``.
- Intervals: split-conformal half-widths per tier from validation (80% nominal).
- ``normal_yield`` (shown to people and used for "% vs normal" and shortfalls) is the average
  of the series' 5 most recent reported years (still only years <= crop_year - 2). The model's
  own reference (the long-run mean) understates today's level for crops with a rising trend.

Writes ``ml/artifacts/forecasts/<model_version>/{forecasts.jsonl, manifest.json}`` for the
backend ``forecast_import`` job.

Usage (from ml/)::

    uv run --no-sync python scripts/export_yield_forecasts.py --crop-year 2026 \\
        --target Kharif:90 --target Rabi:30
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime

import _bootstrap  # noqa: F401
import numpy as np
import pandas as pd

from krishios_ml.common.experiment_log import track_experiment
from krishios_ml.common.paths import DATA_DIR, ML_ROOT, REPORTS_DIR
from krishios_ml.yield_.baselines import LGBMModel
from krishios_ml.yield_.data import (
    HISTORY_LAG,
    MIN_HISTORY,
    add_anomalies,
    build_frame,
    feature_sets,
    history_features,
    weather_normals,
)
from krishios_ml.yield_features.features import build as build_features
from krishios_ml.yield_features.power import PARAMETERS
from krishios_ml.yield_features.zonal import build_daily

LABELS = DATA_DIR / "processed" / "yield_labels" / "v1" / "labels.parquet"
FEATURES = DATA_DIR / "processed" / "yield_features" / "v1" / "season_features.parquet"
WEIGHTS = DATA_DIR / "processed" / "yield_features" / "v1" / "power_cell_weights.parquet"
RECENT = DATA_DIR / "raw" / "nasa_power" / "recent"
SELECTION = REPORTS_DIR / "data" / "yield_baselines_selection.json"
OUT = ML_ROOT / "artifacts" / "forecasts"
MODEL_NAME = "b3-lgbm-multicrop"
RECENT_NORMAL_YEARS = 5
STALE_BEFORE = 2018  # a series last reported before this is out of distribution
MIN_WEATHER_COVERAGE = 0.9


def recent_normal(labels: pd.DataFrame, crop_year: int) -> pd.DataFrame:
    keys = ["lgd_district_code", "crop_canonical", "season"]
    past = labels[labels["crop_year"] <= crop_year - HISTORY_LAG].sort_values("crop_year")
    return (past.groupby(keys).tail(RECENT_NORMAL_YEARS).groupby(keys)["yield"].mean()
            .rename("recent_normal").reset_index())


def serving_rows(labels: pd.DataFrame, crop_year: int, season: str) -> pd.DataFrame:
    """One row per series of ``season``, with history features for ``crop_year``."""
    series = labels[labels["season"] == season]
    last = series.groupby(["lgd_district_code", "crop_canonical", "season"]).agg(
        last_year=("crop_year", "max"), tier=("tier", "first"),
        yield_unit=("yield_unit", "first"), lgd_state_code=("lgd_state_code", "first"),
        outlier_flag=("outlier_flag", "first")).reset_index()
    future = last.assign(crop_year=crop_year, **{"yield": np.nan})
    both = pd.concat([series, future.drop(columns="last_year")], ignore_index=True)
    h = history_features(both, lag=HISTORY_LAG)
    rows = h[h["crop_year"] == crop_year].merge(
        last[["lgd_district_code", "crop_canonical", "season", "last_year"]],
        on=["lgd_district_code", "crop_canonical", "season"])
    return rows.merge(recent_normal(series, crop_year),
                      on=["lgd_district_code", "crop_canonical", "season"], how="left")


def recent_weather(crop_year: int, season: str, lead: int) -> pd.DataFrame:
    weights = pd.read_parquet(WEIGHTS)
    years = range(crop_year - 1, crop_year + 2)
    daily = build_daily(RECENT, weights, PARAMETERS, years)
    keys = pd.DataFrame({"lgd_district_code": sorted(weights["lgd_district_code"].unique())})
    keys = keys.assign(crop_year=crop_year, season=season)
    return build_features(daily, keys, leads=(lead,))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--crop-year", type=int, required=True)
    ap.add_argument("--target", action="append", required=True,
                    help="Season:lead, e.g. Rabi:30 (repeatable)")
    args = ap.parse_args()
    targets = [(t.split(":")[0], int(t.split(":")[1])) for t in args.target]
    frozen = json.loads(SELECTION.read_text(encoding="utf-8"))
    labels, feats = pd.read_parquet(LABELS), pd.read_parquet(FEATURES)
    frame = build_frame(labels, feats)
    generated = datetime.now(UTC)
    version = f"b3-{frozen['run_id']}-{args.crop_year}-{generated:%Y%m%d%H%M}"
    config = {"crop_year": args.crop_year, "targets": targets, "selection_run": frozen["run_id"],
              "model_version": version, "history_lag": HISTORY_LAG, "stale_before": STALE_BEFORE}
    with track_experiment("yield_export", config, seed=0,
                          split_id="serving-refit-all-labels") as rec:
        out_rows: list[dict] = []
        stats: dict = {}
        for season, lead in targets:
            f = frame[(frame["lead_days"] == lead) & frame["eval_ok"]]
            normals = weather_normals(f[f["split"] == "train"])
            f = add_anomalies(f, normals)
            sel = frozen["selection"][str(lead)]["B3_lgbm"]
            feats_full = feature_sets()["full"]
            probe = LGBMModel(feats_full, sel, seed=0).fit(f[f["split"] == "train"],
                                                          f[f["split"] == "val"])
            model = LGBMModel(feats_full, sel, seed=0).fit_full(f, probe.best_iteration)
            q = frozen["conformal_q"][str(lead)]
            rows = serving_rows(labels, args.crop_year, season)
            weather = recent_weather(args.crop_year, season, lead)
            rows = rows.merge(weather, on=["lgd_district_code", "crop_year", "season"],
                              how="left")
            rows["lead_days"] = lead
            rows = add_anomalies(rows, normals)
            rows["lgd_state_code"] = rows["lgd_state_code"].astype(int)
            ok = ((rows["tier"] != "C") & (rows["hist_n"] >= MIN_HISTORY)
                  & (rows["hist_mean"] > 0) & rows["has_weather"].fillna(False).astype(bool))
            ratio = np.full(len(rows), np.nan)
            if ok.any():
                ratio[ok.to_numpy()] = model.predict(rows[ok])
            counts = {"series": len(rows), "forecast": 0, "abstained": 0, "review": 0}
            for i, r in enumerate(rows.itertuples(index=False)):
                base = {"lgd_district_code": int(r.lgd_district_code),
                        "crop_canonical": r.crop_canonical, "season": season,
                        "crop_year": args.crop_year, "crop_tier": r.tier,
                        "forecast_lead": lead, "unit": r.yield_unit, "model_name": MODEL_NAME,
                        "model_version": version, "generated_at": generated.isoformat(),
                        "available_modalities": ["weather", "yield_history"],
                        "missing_modalities": [], "district_id": None}
                if not ok.iloc[i]:
                    reason = ("insufficient data (tier C)" if r.tier == "C"
                              else "no weather data for this district" if not r.has_weather
                              else "too little yield history")
                    out_rows.append({**base, "abstained": True, "abstain_reason": reason,
                                     "in_distribution": True, "requires_human_review": False})
                    counts["abstained"] += 1
                    continue
                half = q[r.tier]
                pred = float(ratio[i] * r.hist_mean)
                low = float(max(0.0, ratio[i] - half) * r.hist_mean)
                high = float((ratio[i] + half) * r.hist_mean)
                missing = [] if (r.rain_coverage >= MIN_WEATHER_COVERAGE
                                 and r.temp_coverage >= MIN_WEATHER_COVERAGE) else ["weather"]
                in_dist = int(r.last_year) >= STALE_BEFORE
                review = r.tier == "B" or bool(missing) or not in_dist
                out_rows.append({**base, "predicted_yield": round(pred, 4),
                                 "interval_low": round(low, 4), "interval_high": round(high, 4),
                                 "normal_yield": round(float(r.recent_normal), 4),
                                 "missing_modalities": missing, "in_distribution": in_dist,
                                 "requires_human_review": review, "abstained": False,
                                 "abstain_reason": None})
                counts["forecast"] += 1
                counts["review"] += int(review)
            stats[f"{season}:{lead}"] = {**counts, "rounds": probe.best_iteration,
                                         "districts_with_weather": int(
                                             weather["has_weather"].sum())}
            print(season, lead, stats[f"{season}:{lead}"], flush=True)
        dest = OUT / version
        dest.mkdir(parents=True, exist_ok=True)
        data = "\n".join(json.dumps(r, ensure_ascii=False) for r in out_rows).encode("utf-8")
        (dest / "forecasts.jsonl").write_bytes(data)
        manifest = {
            "model_name": MODEL_NAME, "model_version": version,
            "generated_at": generated.isoformat(), "file": "forecasts.jsonl",
            "sha256": hashlib.sha256(data).hexdigest(), "rows": len(out_rows),
            "target": [f"{s} {args.crop_year} lead {lead} d" for s, lead in targets],
            "validation": {"selection_run": frozen["run_id"], "export_run": rec.run_id,
                           "interval": "split-conformal 80% per tier (validation)",
                           "report": "ml/reports/08_yield_baselines.md"},
            "normal_yield": f"mean of the {RECENT_NORMAL_YEARS} most recent reported years",
            "inputs": {"weather": "NASA POWER daily regional (recent cache)",
                       "history": f"APY district yields, years <= crop_year - {HISTORY_LAG}"},
        }
        (dest / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
        rec.metrics = stats
        rec.artifact_path = str(dest.relative_to(ML_ROOT))
    print("wrote", dest, len(out_rows), "rows; run_id", rec.run_id)


if __name__ == "__main__":
    main()
