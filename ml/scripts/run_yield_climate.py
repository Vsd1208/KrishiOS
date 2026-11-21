"""Phase 10: do large-scale and regional climate drivers improve yield forecasts? (no test years)

Global indices (El Nino, Indian Ocean Dipole, tropical cloud) plus drivers routed to the regions
they are expected to affect: upper-level westerlies over the Middle East and Central Asia for the
north-west and western Himalaya, Nepal rainfall for Uttar Pradesh and Bihar, and upper-Brahmaputra
rain and Tibetan heat for the north-east.

These inputs have one value per year, season and lead, so a few validation years prove little
and a flexible model can treat them as a year label. The experiment uses forward chaining over
three periods, always training on earlier years, and includes a placebo:

- B3: Phase 8 LightGBM;
- B3_climate: B3 plus global indices;
- B3_regional: B3 plus global indices and routed regional drivers;
- B3_regional_placebo: the same inputs taken from the wrong years.

A real signal should beat both B3 and the placebo, across periods and in its target regions.

Usage (from ml/)::

    uv run --no-sync python scripts/run_yield_climate.py
"""

from __future__ import annotations

import json

import _bootstrap  # noqa: F401
import numpy as np
import pandas as pd
from run_yield_baselines import FEATURES, LABELS, LEADS, SEEDS, SELECTION, mean_std, score
from run_yield_ndvi import paired

from krishios_ml.common.experiment_log import track_experiment
from krishios_ml.common.paths import DATA_DIR, REPORTS_DIR
from krishios_ml.yield_.baselines import LGBMModel
from krishios_ml.yield_.data import add_anomalies, build_frame, feature_sets, weather_normals
from krishios_ml.yield_features import climate

RAW = DATA_DIR / "raw" / "climate_indices"
DRIVERS = DATA_DIR / "processed" / "yield_features" / "v1" / "climate_drivers.parquet"
FOLDS = ((2010, 2012), (2013, 2015), (2016, 2018))
JOIN = ["crop_year", "season", "lead_days"]


def climate_table(feats: pd.DataFrame) -> pd.DataFrame:
    keys = feats[[*JOIN, "cutoff"]].drop_duplicates(JOIN)
    keys = keys.assign(cutoff=pd.to_datetime(keys["cutoff"]))
    glob = climate.features_at(climate.load_indices(RAW), keys["cutoff"])
    series = climate.standardize(pd.read_parquet(DRIVERS))
    regional = climate.driver_features(series, keys["cutoff"])
    return keys.merge(glob, on="cutoff", how="left").merge(regional, on="cutoff", how="left"
                                                           ).drop(columns="cutoff")


def with_climate(df: pd.DataFrame, table: pd.DataFrame, year_map: dict | None = None
                 ) -> pd.DataFrame:
    left = df.assign(_year=df["crop_year"].map(year_map) if year_map else df["crop_year"])
    right = table.rename(columns={"crop_year": "_year"})
    out = left.merge(right, on=["_year", "season", "lead_days"], how="left").drop(columns="_year")
    return climate.route_drivers(out)


def region_errors(va: pd.DataFrame, pred: np.ndarray) -> dict[str, float]:
    """Mean absolute error of the yield ratio on clean tier A/B rows, by target region."""
    keep = (va["tier"].isin(("A", "B")) & va["eval_clean"]).to_numpy()
    err = np.abs(va["ratio"].to_numpy() - pred)
    state = va["lgd_state_code"].astype(int)
    out = {"all_india": float(err[keep].mean())}
    for name, states in climate.REGIONS.items():
        m = keep & state.isin(states).to_numpy()
        out[name] = float(err[m].mean()) if m.any() else float("nan")
    return out


def main() -> None:
    labels, feats = pd.read_parquet(LABELS), pd.read_parquet(FEATURES)
    frozen = json.loads(SELECTION.read_text(encoding="utf-8"))
    table = climate_table(feats)
    frame = build_frame(labels, feats)
    frame = frame[frame["split"].isin(["train", "val"]) & frame["eval_ok"]]
    del labels, feats
    base = feature_sets()["full"]
    glob = [*base, *climate.FEATURES]
    regional = [*glob, *climate.DRIVER_FEATURES]
    config = {"folds": FOLDS, "leads": list(LEADS), "seeds": list(SEEDS),
              "selection_run": frozen["run_id"], "indices": list(climate.INDICES),
              "drivers": [d.name for d in climate.DRIVERS],
              "baseline_years": climate.BASELINE_YEARS,
              "models": ["B3", "B3_climate", "B3_regional", "B3_regional_placebo"]}
    results: dict = {}
    pooled: dict[str, list[dict]] = {}
    regions: dict[str, list[dict]] = {}
    with track_experiment("yield_climate", config, seed=None,
                          split_id="apy-tierv2-ee75501cc5ef") as rec:
        years = np.array(sorted(table["crop_year"].unique()))
        for lead in LEADS:
            params = frozen["selection"][str(lead)]["B3_lgbm"]
            for start, end in FOLDS:
                f = frame[(frame["lead_days"] == lead) & (frame["crop_year"] <= end)]
                f = add_anomalies(f, weather_normals(f[f["crop_year"] < start]))
                real = with_climate(f, table)
                fold = f"{start}-{end}"
                runs: dict[str, list[dict]] = {}
                for seed in SEEDS:
                    shuffled = np.random.default_rng(1000 + seed).permutation(years)
                    year_map = dict(zip(years.tolist(), shuffled.tolist(), strict=True))
                    for name, data, use in (
                            ("B3", real, base), ("B3_climate", real, glob),
                            ("B3_regional", real, regional),
                            ("B3_regional_placebo", with_climate(f, table, year_map), regional)):
                        tr = data[data["crop_year"] < start].reset_index(drop=True)
                        va = data[data["crop_year"] >= start].reset_index(drop=True)
                        m = LGBMModel(use, params, seed=seed, name=name).fit(tr, va)
                        pred = m.predict(va)
                        s = score(va, pred)
                        runs.setdefault(name, []).append(s)
                        pooled.setdefault(name, []).append(s)
                        regions.setdefault(name, []).append(region_errors(va, pred))
                        print(f"lead {lead} {fold} seed {seed} {name}: "
                              f"{s['A']['nmae_median']:.4f}", flush=True)
                results.setdefault(str(lead), {})[fold] = {
                    n: {"A": mean_std(r, "A"), "B": mean_std(r, "B")} for n, r in runs.items()}
        rec.metrics = {lead: {fold: {n: v["A"]["nmae_median"]["mean"] for n, v in m.items()}
                              for fold, m in by_fold.items()}
                       for lead, by_fold in results.items()}
        comparisons = {f"{n}_vs_B3": paired(pooled["B3"], pooled[n])
                       for n in ("B3_climate", "B3_regional", "B3_regional_placebo")}
        region_mean = {n: pd.DataFrame(r).mean().round(5).to_dict() for n, r in regions.items()}
        path = REPORTS_DIR / "data" / f"yield_climate_{rec.run_id}.json"
        path.write_text(json.dumps({"run_id": rec.run_id, "config": config, "results": results,
                                    "comparisons": comparisons, "region_ratio_mae": region_mean},
                                   indent=1, default=float), encoding="utf-8")
        rec.artifact_path = str(path.relative_to(REPORTS_DIR.parent))
    print(json.dumps({"comparisons": comparisons, "regions": region_mean}, indent=1,
                     default=float))
    print("run_id", rec.run_id)


if __name__ == "__main__":
    main()
