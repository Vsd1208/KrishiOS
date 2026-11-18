"""Phase 9: build the vision dataset (labels, cache, leakage-aware splits).

Sources: Hugging Face Parquet mirrors downloaded by ``scripts/download_vision_datasets.py``
into data/raw/vision/hf/ (git-ignored):

- plantvillage    DScomp380/plant_village (lab leaf photos; CC0 tag. Per the user's decision
                  models trained on it are treated as CC BY-SA 3.0, the paper's licence)
- plantdoc        agyaatcoder/PlantDoc (CC BY 4.0; web "in the wild" photos; each labelled
                  leaf box is cropped into a sample; official train/test kept)
- agml_rice_india Project-AgML/rice_leaf_disease_classification_india (CC BY 4.0; Sethy et
                  al., field photos from Odisha; 4 disease classes, no healthy class)

Each sample's class is mapped through reference/vision_label_map.csv; an unmapped class stops
the build. Near-duplicates (dHash <= 6 bits) are grouped across all sources; splits are drawn
per group, PlantDoc keeps its official test split, and any test image that is a near-duplicate
of a train/val image is dropped (counted). All crops of one PlantDoc photo share a group.

The India rice set is made of augmented copies (every image has a flipped/rotated twin), so its
groups are original photos: same class and file number (``BLAST3_007`` = ``BLAST8_007``), or
pixel correlation >= 0.95 under any flip / 90-degree rotation (identical photos also appear
under different numbers). Its split is stratified by disease, and test rows whose colours still
match a same-class train/val image almost exactly are dropped (counted).

Usage (from ml/)::

    uv run --no-sync python scripts/build_vision_dataset.py
"""

from __future__ import annotations

import argparse
import json
from collections import Counter

import _bootstrap  # noqa: F401
import numpy as np
import pandas as pd

from krishios_ml.common.experiment_log import track_experiment
from krishios_ml.common.paths import DATA_DIR, ML_ROOT, REPORTS_DIR
from krishios_ml.vision.data import (
    augmented_family_groups,
    cache_name,
    colour_histogram,
    connected_groups,
    dhash,
    grey_thumbnail,
    iter_parquet_samples,
    near_duplicate_groups,
    save_cached,
    split_groups,
    stratified_group_split,
    test_rows_matching_training,
)

HF = DATA_DIR / "raw" / "vision" / "hf"
OUT = DATA_DIR / "processed" / "vision" / "v1"
CACHE = OUT / "cache"
LABEL_MAP = ML_ROOT / "reference" / "vision_label_map.csv"
CATALOG = ML_ROOT / "reference" / "crop_catalog.csv"
SOURCES = {  # source -> (hf folder, parquet kind, setting)
    "plantvillage": ("DScomp380__plant_village", "classification", "lab"),
    "plantdoc": ("agyaatcoder__PlantDoc", "boxes", "field"),
    "agml_rice_india": ("Project-AgML__rice_leaf_disease_classification_india",
                        "classification", "field"),
}
AUGMENTED = "agml_rice_india"
SPLIT = {"val": 0.15, "test": 0.15, "seed": "krishios-vision-v1"}


def assign_groups(df: pd.DataFrame) -> np.ndarray:
    """Leakage groups: original photos for the augmented rice set; near-duplicates plus shared
    source photo for everything else."""
    groups = np.zeros(len(df), dtype=np.int64)
    rice = (df["source"] == AUGMENTED).to_numpy()
    other = np.flatnonzero(~rice)
    if len(other):
        near = near_duplicate_groups(df["dhash"].to_numpy(dtype=np.uint64)[other])
        origin = df["origin"].to_numpy(dtype=str)[other]
        groups[other] = connected_groups(len(other), [near, origin])
    idx = np.flatnonzero(rice)
    if len(idx):
        sub = df.iloc[idx]
        fam = augmented_family_groups(sub["origin"].tolist(), sub["raw_class"].tolist(),
                                      np.stack(sub["thumb"].to_numpy()))
        groups[idx] = fam + int(groups.max()) + 1
    return groups


def collect(limit_per_class: int, log=print) -> pd.DataFrame:
    from PIL import Image

    rows = []
    for source, (folder, kind, setting) in SOURCES.items():
        files = sorted((HF / folder).rglob("*.parquet"))
        if not files:
            log(f"{source}: no parquet files yet, skipped")
            continue
        seen: Counter = Counter()
        for f in files:
            official = "test" if f.name.startswith("test") else "train"
            for n, (member, raw, img, origin) in enumerate(iter_parquet_samples(f, kind)):
                if limit_per_class and seen[raw] >= limit_per_class:
                    continue
                seen[raw] += 1
                dest = CACHE / cache_name(source, member)
                if not dest.exists():
                    save_cached(img, dest)
                cached = Image.open(dest)
                rows.append({"source": source, "setting": setting, "member": member,
                             "origin": origin, "raw_class": raw, "official_split": official,
                             "cache": str(dest.relative_to(CACHE)), "dhash": dhash(cached),
                             "hist": colour_histogram(cached) if source == AUGMENTED else None,
                             "thumb": grey_thumbnail(cached) if source == AUGMENTED else None})
                if n and n % 5000 == 0:
                    log(f"{source} {f.name}: {n}")
        log(f"{source}: {sum(seen.values())} samples, {len(seen)} classes")
    return pd.DataFrame(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit-per-class", type=int, default=0, help="dev smoke runs only")
    args = ap.parse_args()
    config = {"sources": {k: v[0] for k, v in SOURCES.items()}, "split": SPLIT,
              "dup_bits": 6, "cache_px": 256, "limit_per_class": args.limit_per_class}
    with track_experiment("vision_dataset", config, seed=None, split_id=SPLIT["seed"]) as rec:
        df = collect(args.limit_per_class)
        if df.empty:
            raise SystemExit("no vision data found under data/raw/vision/hf")
        lm = pd.read_csv(LABEL_MAP, keep_default_na=False)
        df = df.merge(lm[["source", "raw_class", "crop_label", "condition"]],
                      on=["source", "raw_class"], how="left")
        unmapped = df[df["crop_label"].isna()].groupby(["source", "raw_class"]).size()
        if len(unmapped):
            raise SystemExit(f"unmapped classes (add them to {LABEL_MAP.name}):\n{unmapped}")
        keys = set(pd.read_csv(CATALOG, keep_default_na=False)["crop_canonical"])
        df["crop_canonical"] = df["crop_label"].where(df["crop_label"].isin(keys), "")
        df["group"] = assign_groups(df)
        drawn = split_groups(df["group"].to_numpy(), SPLIT["val"], SPLIT["test"], SPLIT["seed"])
        rice = (df["source"] == AUGMENTED).to_numpy()
        if rice.any():
            drawn = drawn.astype(object)
            drawn[rice] = stratified_group_split(df["group"].to_numpy()[rice],
                                                 df["raw_class"].to_numpy(dtype=str)[rice],
                                                 SPLIT["val"], SPLIT["test"], SPLIT["seed"])
            drawn = drawn.astype(str)
        is_pd = (df["source"] == "plantdoc").to_numpy()
        df["split"] = np.where(is_pd & (df["official_split"] == "test"), "test",
                               np.where(is_pd & (drawn == "test"), "train", drawn))
        g_splits = df.groupby("group")["split"].agg(set)
        straddle = set(g_splits[g_splits.map(lambda s: "test" in s and len(s) > 1)].index)
        leak = df["group"].isin(straddle) & (df["split"] == "test")
        dropped = df[leak].groupby("source").size().to_dict()
        df = df[~leak].reset_index(drop=True)
        rice_idx = np.flatnonzero((df["source"] == AUGMENTED).to_numpy())
        rice_match = 0
        if len(rice_idx):
            sub = df.iloc[rice_idx]
            hit = test_rows_matching_training(np.stack(sub["hist"].to_numpy()),
                                              sub["raw_class"].to_numpy(dtype=str),
                                              sub["split"].to_numpy(dtype=str))
            rice_match = int(hit.sum())
            df = df.drop(index=df.index[rice_idx[hit]]).reset_index(drop=True)
        df = df.drop(columns=["hist", "thumb"])
        OUT.mkdir(parents=True, exist_ok=True)
        df.to_parquet(OUT / "images.parquet", index=False)
        rec.metrics = {
            "images": len(df), "by_source": df["source"].value_counts().to_dict(),
            "by_source_split": {f"{s}:{p}": int(n) for (s, p), n in
                                df.groupby(["source", "split"]).size().items()},
            "crops": int(df["crop_label"].nunique()),
            "catalog_crops": sorted(df.loc[df["crop_canonical"] != "", "crop_label"].unique()),
            "conditions": int((df["crop_label"] + "|" + df["condition"]).nunique()),
            "near_duplicate_groups_multi": int((df.groupby("group").size() > 1).sum()),
            "groups_by_source": df.groupby("source")["group"].nunique().to_dict(),
            "largest_group_by_source": {s: int(g.groupby("group").size().max())
                                        for s, g in df.groupby("source")},
            "rice_original_groups_by_class": df[df["source"] == AUGMENTED].groupby(
                "raw_class")["group"].nunique().to_dict(),
            "test_rows_by_class_field": df[(df["split"] == "test")
                                           & (df["setting"] == "field")].groupby(
                ["source", "condition"]).size().rename("n").reset_index().to_dict("records"),
            "test_dropped_as_duplicates": dropped,
            "rice_test_dropped_as_colour_matches": rice_match,
            "per_class_counts": {f"{c}|{d}": int(n) for (c, d), n in Counter(
                zip(df["crop_label"], df["condition"], strict=True)).items()},
        }
        path = REPORTS_DIR / "data" / f"vision_dataset_{rec.run_id}.json"
        path.write_text(json.dumps({"run_id": rec.run_id, "config": config,
                                    "metrics": rec.metrics}, indent=1), encoding="utf-8")
        rec.artifact_path = str(path.relative_to(REPORTS_DIR.parent))
    print(json.dumps({k: v for k, v in rec.metrics.items() if k != "per_class_counts"},
                     indent=1))
    print("run_id", rec.run_id)


if __name__ == "__main__":
    main()
