"""Phase 10: are B3's forecast ranges calibrated per tier? (validation years only)

Out-of-time check: interval widths are fitted on 2013-15 forecasts from a model trained up to
2010 (early stopping on 2011-12), then coverage is measured on 2016-18 forecasts from a model
trained up to 2013 (early stopping on 2014-15). The 2016-18 rows are never used to set widths.

Three split-conformal variants (absolute error of the yield ratio):
- ``tier``: one half-width per tier, as served since Phase 8.
- ``crop``: one per crop (Mondrian), falling back to the tier width below ``MIN_CROP_ROWS``.
- ``scaled``: per tier, on errors divided by the district's historical variability (hist_cv),
  so steady districts get narrower ranges and erratic ones wider.

Reported per tier and level: coverage, mean width (in ratio units) and, per crop, the share of
crops within 10 points of the target and the worst crop.

Usage (from ml/)::

    uv run --no-sync python scripts/run_yield_uncertainty.py
"""

from __future__ import annotations

import json

import _bootstrap  # noqa: F401
import numpy as np
import pandas as pd
from run_yield_baselines import FEATURES, LABELS, LEADS, SELECTION
from run_yield_generalisation import b3_fit, b3_frames, stats

from krishios_ml.common.experiment_log import track_experiment
from krishios_ml.common.paths import REPORTS_DIR
from krishios_ml.yield_.data import build_frame

SPLIT_ID = "apy-tierv2-ee75501cc5ef"
SEEDS = (0, 1, 2)
LEVELS = (0.5, 0.8, 0.9)
MIN_CROP_ROWS = 50
TIERS = ("A", "B")
CAL, EVAL = (2013, 2015), (2016, 2018)


def quantile(res: np.ndarray, level: float) -> float:
    r = np.sort(res)
    n = len(r)
    return float(r[min(n - 1, int(np.ceil((n + 1) * level)) - 1)])


def scale(df: pd.DataFrame, fill: float) -> np.ndarray:
    return df["hist_cv"].fillna(fill).clip(0.02, None).to_numpy()


def half_widths(cal: pd.DataFrame, res: np.ndarray, ev: pd.DataFrame, level: float,
                fill: float) -> dict[str, np.ndarray]:
    tier_q = {t: quantile(res[(cal["tier"] == t).to_numpy()], level) for t in TIERS}
    by_tier = ev["tier"].map(tier_q).to_numpy()
    crop_q = {}
    for crop, idx in cal.groupby("crop_canonical").indices.items():
        if len(idx) >= MIN_CROP_ROWS:
            crop_q[crop] = quantile(res[idx], level)
    by_crop = ev["crop_canonical"].map(crop_q).to_numpy(dtype=float)
    by_crop = np.where(np.isfinite(by_crop), by_crop, by_tier)
    norm = res / scale(cal, fill)
    scaled_q = {t: quantile(norm[(cal["tier"] == t).to_numpy()], level) for t in TIERS}
    by_scaled = ev["tier"].map(scaled_q).to_numpy() * scale(ev, fill)
    return {"tier": by_tier, "crop": by_crop, "scaled": by_scaled}


def check(ev: pd.DataFrame, pred: np.ndarray, half: np.ndarray, level: float) -> dict:
    inside = np.abs(ev["ratio"].to_numpy() - pred) <= half
    out = {}
    for t in TIERS:
        m = (ev["tier"] == t).to_numpy()
        crops = pd.Series(inside[m]).groupby(ev.loc[m, "crop_canonical"].to_numpy()).mean()
        out[t] = {"coverage": float(inside[m].mean()), "width": float(2 * half[m].mean()),
                  "crops_within_10pts": float((np.abs(crops - level) <= 0.10).mean()),
                  "worst_crop": float(crops.min()), "worst_crop_name": str(crops.idxmin())}
    return out


def main() -> None:
    labels, feats = pd.read_parquet(LABELS), pd.read_parquet(FEATURES)
    frame = build_frame(labels, feats)
    frame = frame[frame["split"].isin(["train", "val"]) & frame["eval_ok"]]
    del labels, feats
    sel = json.loads(SELECTION.read_text(encoding="utf-8"))["selection"]
    config = {"phase": "val", "model": "B3", "seeds": list(SEEDS), "levels": list(LEVELS),
              "calibration_years": CAL, "evaluation_years": EVAL,
              "min_crop_rows": MIN_CROP_ROWS, "rows": "clean tier A/B rows"}
    runs: list[dict] = []
    with track_experiment("yield_uncertainty", config, seed=None, split_id=SPLIT_ID) as rec:
        for seed in SEEDS:
            for lead in LEADS:
                fits = {}
                for name, (start, end) in (("cal", CAL), ("eval", EVAL)):
                    f = b3_frames(frame, lead, normals_until=start - 3)
                    model = b3_fit(f[f["crop_year"] <= start - 3],
                                   f[f["crop_year"].between(start - 2, start - 1)],
                                   lead, seed, sel)
                    ev = f[f["crop_year"].between(start, end) & f["tier"].isin(TIERS)
                           & f["eval_clean"]].reset_index(drop=True)
                    fits[name] = (ev, model.predict(ev))
                cal, p_cal = fits["cal"]
                ev, p_ev = fits["eval"]
                res = np.abs(cal["ratio"].to_numpy() - p_cal)
                fill = float(cal["hist_cv"].median())
                for level in LEVELS:
                    for variant, half in half_widths(cal, res, ev, level, fill).items():
                        runs.append({"seed": seed, "lead": lead, "level": level,
                                     "variant": variant, **check(ev, p_ev, half, level)})
                print(f"seed {seed} lead {lead} done", flush=True)
        table: dict = {}
        for level in LEVELS:
            for variant in ("tier", "crop", "scaled"):
                rows = [r for r in runs if r["level"] == level and r["variant"] == variant]
                table.setdefault(str(level), {})[variant] = {
                    t: {k: stats([r[t][k] for r in rows])
                        for k in ("coverage", "width", "crops_within_10pts", "worst_crop")}
                    for t in TIERS}
        rec.metrics = {lvl: {v: {t: round(x[t]["coverage"]["mean"], 4) for t in TIERS}
                             for v, x in vs.items()} for lvl, vs in table.items()}
        path = REPORTS_DIR / "data" / f"yield_uncertainty_{rec.run_id}.json"
        path.write_text(json.dumps({"run_id": rec.run_id, "config": config, "table": table,
                                    "runs": runs}, indent=1, default=float), encoding="utf-8")
        rec.artifact_path = str(path.relative_to(REPORTS_DIR.parent))
    for level, vs in table.items():
        for v, x in vs.items():
            print(level, v, {t: (round(x[t]["coverage"]["mean"], 3),
                                 round(x[t]["width"]["mean"], 3),
                                 round(x[t]["crops_within_10pts"]["mean"], 2)) for t in TIERS})
    print("run_id", rec.run_id)


if __name__ == "__main__":
    main()
