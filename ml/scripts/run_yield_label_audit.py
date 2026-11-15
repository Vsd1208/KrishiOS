"""Phase 6 yield label audit: APY (primary) + UPAg (cross-check / recent years).

Both are Ministry of Agriculture & Farmers Welfare district statistics, downloaded from the
India Data Portal mirror (ODC-By). Outputs (versioned, keyed by LGD district code):

- ``data/processed/yield_labels/v1/apy.parquet`` and ``upag.parquet`` (normalised)
- ``reports/data/yield_label_audit_<run_id>.json`` (per crop-season metrics, tiers, splits,
  APY-vs-UPAg agreement); logged in ``experiments/yield_label_audit.jsonl``

Usage (from ml/)::

    uv run python scripts/run_yield_label_audit.py --snapshot 20261114
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict

import _bootstrap  # noqa: F401
import pandas as pd

from krishios_ml.common.experiment_log import track_experiment
from krishios_ml.common.paths import DATA_DIR, ML_ROOT, REPORTS_DIR
from krishios_ml.yield_labels.apy import (
    BALE_TONNES,
    SEASON_MAP,
    apy_crop_map,
    combine_seasons,
    load_apy,
)
from krishios_ml.yield_labels.audit import (
    TierRule,
    assign_tier,
    audit,
    split_of,
    to_records,
    usable,
)

CATALOG = ML_ROOT / "reference" / "crop_catalog.csv"
# Proposed before looking at per-tier counts; derived from what a per-crop model needs:
# enough districts for spatial generalisation and enough years for a time split.
TIERS = [
    TierRule("A", min_district_years=2000, min_years=18, min_districts=150,
             max_outlier_rate=0.03, max_missing_rate=0.05),
    TierRule("B", min_district_years=500, min_years=12, min_districts=40,
             max_outlier_rate=0.05, max_missing_rate=0.10),
    TierRule("C", min_district_years=100, min_years=8, min_districts=10,
             max_outlier_rate=0.08, max_missing_rate=0.20),
]
# v2 (after reviewing the v1 counts, before any model): the outlier rate mostly reflects real
# crop failures (droughts, zero-yield years) in rainfed crops, not label errors, so it is a
# reported quality flag with a looser cap; tiers are gated on coverage. v1 stays on record.
TIERS_V2 = [
    TierRule("A", min_district_years=2000, min_years=18, min_districts=150,
             max_outlier_rate=0.10, max_missing_rate=0.05),
    TierRule("B", min_district_years=500, min_years=12, min_districts=40,
             max_outlier_rate=0.10, max_missing_rate=0.10),
    TierRule("C", min_district_years=100, min_years=8, min_districts=10,
             max_outlier_rate=0.12, max_missing_rate=0.20),
]
SPLIT = {"val_from": 2016, "test_from": 2019, "spatial_share": 0.10}
AGREE_TOL = 0.05


def load_upag(path, crop_map):
    u = pd.read_csv(path, dtype=str, keep_default_na=False)
    season = u["season"].str.strip().str.lower().map(SEASON_MAP)
    num = lambda c: pd.to_numeric(u[c].str.replace(",", "", regex=False), errors="coerce")  # noqa: E731
    frame = pd.DataFrame({
        "lgd_district_code": pd.to_numeric(u["district_code"], errors="coerce").astype("Int64"),
        "district_name": u["district_name"].str.strip(),
        "lgd_state_code": pd.to_numeric(u["state_code"], errors="coerce").astype("Int64"),
        "state_name": u["state_name"].str.strip(),
        "crop_year": pd.to_numeric(u["year"].str[:4], errors="coerce").astype("Int64"),
        "crop_raw": u["crop_name"].str.strip(), "apy_crop_code": u["crop_code"].str.strip(),
        "crop_type": u["crop_category"].str.strip(),
        "crop_canonical": u["crop_name"].str.strip().str.lower().map(crop_map),
        "season_raw": u["season"].str.strip(), "season": season,
        "area_ha": num("area"), "production": num("production"),
        "production_unit": "Tonnes",
        "yield_reported": num("yield") / 1000.0,  # UPAg publishes kg/ha
        "yield_unit": "Tonnes/Hectare (from kg/ha)",
    })[lambda d: d["season"].notna()].reset_index(drop=True)
    return combine_seasons(frame)[0]


def agreement(apy: pd.DataFrame, upag: pd.DataFrame) -> dict:
    keys = ["lgd_district_code", "crop_canonical", "season", "crop_year"]
    a = usable(apy).dropna(subset=["crop_canonical", "yield"])
    factor = a["yield_unit"].map(BALE_TONNES).fillna(1.0)
    a = a.assign(**{"yield": a["yield"] * factor})
    b = usable(upag).dropna(subset=["crop_canonical", "yield"])
    a = a[a["area_ha"] > 0].groupby(keys, as_index=False)["yield"].mean()
    b = b[b["area_ha"] > 0].groupby(keys, as_index=False)["yield"].mean()
    m = a.merge(b, on=keys, suffixes=("_apy", "_upag"))
    if m.empty:
        return {"overlap": 0}
    rel = (m["yield_apy"] - m["yield_upag"]).abs() / m["yield_upag"].where(m["yield_upag"] > 0)
    by_crop = (m.assign(ok=rel <= AGREE_TOL).groupby("crop_canonical")["ok"]
               .agg(["mean", "size"]).sort_values("size", ascending=False).head(15))
    return {"overlap": len(m), "years": sorted(int(y) for y in m["crop_year"].unique()),
            "agree_within_5pct": round(float((rel <= AGREE_TOL).mean()), 4),
            "median_rel_diff": round(float(rel.median()), 4),
            "by_crop": {k: {"agree": round(float(v["mean"]), 3), "n": int(v["size"])}
                        for k, v in by_crop.iterrows()}}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", default="20261114")
    args = ap.parse_args()
    raw = DATA_DIR / "raw" / "apy" / args.snapshot
    apy, stats = load_apy(raw / "crop-wise-area-production-yield.csv", CATALOG)
    upag = load_upag(raw / "cropwise-area-production-yield-upag.csv", apy_crop_map(CATALOG))
    out_dir = DATA_DIR / "processed" / "yield_labels" / "v1"
    out_dir.mkdir(parents=True, exist_ok=True)
    apy.to_parquet(out_dir / "apy.parquet", index=False)
    upag.to_parquet(out_dir / "upag.parquet", index=False)

    config = {"snapshot": args.snapshot,
              "sources": ["APY (IDP mirror, ODC-By)", "UPAg (IDP mirror, ODC-By)"],
              "tiers_v1": [asdict(t) for t in TIERS], "tiers": [asdict(t) for t in TIERS_V2],
              "split": SPLIT,
              "agreement_tolerance": AGREE_TOL}
    with track_experiment("yield_label_audit", config, seed=None,
                          split_id=f"apy-{args.snapshot}") as rec:
        series = audit(apy)
        tiers_v1 = {f"{s.crop}|{s.season}": assign_tier(s, TIERS) for s in series}
        tiers = {f"{s.crop}|{s.season}": assign_tier(s, TIERS_V2) for s in series}
        tier_counts = Counter(tiers.values())
        labelled = usable(apy).dropna(subset=["crop_canonical", "yield"])
        labelled = labelled[labelled["area_ha"] > 0]
        kept = labelled[[tiers.get(f"{c}|{s}", "").startswith(("A", "B", "C"))
                         for c, s in zip(labelled["crop_canonical"], labelled["season"],
                                         strict=True)]]
        dy = kept.drop_duplicates(["lgd_district_code", "crop_year"])
        splits = Counter(split_of(int(d), int(y), **SPLIT)
                         for d, y in zip(dy["lgd_district_code"], dy["crop_year"], strict=True))
        rows_by_split = Counter(split_of(int(d), int(y), **SPLIT)
                                for d, y in zip(kept["lgd_district_code"], kept["crop_year"],
                                                strict=True))
        unmapped = (apy[apy["crop_canonical"].isna()].groupby("crop_raw").size()
                    .sort_values(ascending=False))
        rec.metrics = {
            "ingest": stats, "upag_rows": len(upag),
            "apy_years": [int(apy["crop_year"].min()), int(apy["crop_year"].max())],
            "upag_years": [int(upag["crop_year"].min()), int(upag["crop_year"].max())],
            "series_total": len(series), "tier_counts_v1": dict(Counter(tiers_v1.values())),
            "tier_counts": dict(tier_counts),
            "crops_tiered": len({k.split("|")[0] for k, v in tiers.items()
                                 if v in ("A", "B", "C")}),
            "split_district_years": dict(splits), "split_label_rows": dict(rows_by_split),
            "unmapped_crops_top": {k: int(v) for k, v in unmapped.head(20).items()},
            "apy_vs_upag": agreement(apy, upag),
        }
        payload = {"run_id": rec.run_id, "config": config, "metrics": rec.metrics,
                   "series": [{**r, "tier": tiers[f"{r['crop']}|{r['season']}"],
                               "tier_v1": tiers_v1[f"{r['crop']}|{r['season']}"]}
                              for r in to_records(series)]}
        out = REPORTS_DIR / "data" / f"yield_label_audit_{rec.run_id}.json"
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=1, default=str),
                       encoding="utf-8")
        rec.artifact_path = str(out.relative_to(REPORTS_DIR.parent))
    print(json.dumps({k: v for k, v in rec.metrics.items() if k != "apy_vs_upag"}, indent=1))
    print("apy_vs_upag:", json.dumps(rec.metrics["apy_vs_upag"])[:900])
    print("run_id", rec.run_id)


if __name__ == "__main__":
    main()
