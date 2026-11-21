"""Vision retraining: add the checked Indian field photos to the training data (``india_field``).

Input: the photos from ``download_india_vision.py`` after ``check_india_vision.py`` (its
``quality_files.parquet`` gives each file's label, near-copy group and training overlap).

- One row per photo (exact copies collapsed); photos filed under two labels are dropped.
- Labels go through ``reference/vision_label_map.csv``; a label mapped to an empty crop is
  excluded (counted), and an unmapped label stops the script.
- Each photo is made upright from its EXIF data and saved to the shared training cache
  (``processed/vision/v1/cache/india_field/``) at the cache size, like every other source.
- Splits: whole near-copy groups go to one split, stratified by label (15% validation, 15% test,
  the same rule and seed as the India rice set). The test photos must never be used for training,
  tuning or model choice; they are scored once, by the retraining run.

The result is ``processed/vision/india_v1/images.parquet`` with the same columns as
``processed/vision/v1/images.parquet``. Cached files that already exist are kept, so the script
can be stopped and run again.

Usage (from ml/)::

    uv run --no-sync python scripts/prepare_india_vision.py
"""

from __future__ import annotations

import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

import _bootstrap  # noqa: F401
import numpy as np
import pandas as pd
from PIL import Image, ImageOps

from krishios_ml.common.experiment_log import track_experiment
from krishios_ml.common.paths import DATA_DIR, ML_ROOT
from krishios_ml.vision.data import CACHE_SIZE, save_cached, stratified_group_split

RAW = DATA_DIR / "raw" / "vision" / "india"
CACHE = DATA_DIR / "processed" / "vision" / "v1" / "cache"
OUT = DATA_DIR / "processed" / "vision" / "india_v1"
LABEL_MAP = ML_ROOT / "reference" / "vision_label_map.csv"
CATALOG = ML_ROOT / "reference" / "crop_catalog.csv"
SOURCE = "india_field"
SPLIT = {"val": 0.15, "test": 0.15, "seed": "krishios-vision-india-v1"}
WORKERS = 3  # half of what the CPU studies leave free
GROUP_OFFSET = 10_000_000  # keeps these group ids apart from the v1 groups
Image.MAX_IMAGE_PIXELS = 80_000_000


def load_rows() -> tuple[pd.DataFrame, Counter]:
    q = pd.read_parquet(RAW / "quality_files.parquet")
    quality = json.loads((RAW / "quality.json").read_text(encoding="utf-8"))
    conflicts = set(quality.get("exact_label_conflicts", {}))
    dropped: Counter = Counter()
    q = q.drop_duplicates("sha256")
    bad = q["sha256"].str[:12].isin(conflicts)
    dropped["filed under two labels"] = int(bad.sum())
    q = q[~bad]
    lm = pd.read_csv(LABEL_MAP, keep_default_na=False)
    lm = lm[lm["source"] == SOURCE].rename(columns={"raw_class": "label"})
    q = q.merge(lm[["label", "crop_label", "condition"]], on="label", how="left")
    unmapped = sorted(q.loc[q["crop_label"].isna(), "label"].unique())
    if unmapped:
        raise SystemExit(f"unmapped labels (add them to {LABEL_MAP.name}): {unmapped}")
    excluded = q["crop_label"] == ""
    for label, n in q.loc[excluded, "label"].value_counts().items():
        dropped[f"excluded label {label}"] = int(n)
    return q[~excluded].reset_index(drop=True), dropped


def cache_one(row: pd.Series) -> str:
    rel = f"{SOURCE}/{row['sha256'][:16]}.jpg"
    dest = CACHE / rel
    if not dest.exists():
        with Image.open(RAW / row["file"]) as img:
            img.draft("RGB", (CACHE_SIZE * 2, CACHE_SIZE * 2))  # fast JPEG decode at reduced size
            save_cached(ImageOps.exif_transpose(img).convert("RGB"), dest)
    return rel  # forward slashes work on Windows and on Colab (Linux)


def main() -> None:
    rows, dropped = load_rows()
    keys = set(pd.read_csv(CATALOG, keep_default_na=False)["crop_canonical"])
    config = {"source": SOURCE, "split": SPLIT, "cache_size": CACHE_SIZE,
              "label_map_rows": int((pd.read_csv(LABEL_MAP)["source"] == SOURCE).sum())}
    with track_experiment("vision_india_prepare", config, seed=None,
                          split_id=SPLIT["seed"]) as rec:
        # Decoding 30-megapixel photos dominates; Pillow releases the GIL, so a few threads help.
        with ThreadPoolExecutor(WORKERS) as pool:
            cached = []
            for i, rel in enumerate(pool.map(cache_one, (r for _, r in rows.iterrows()))):
                cached.append(rel)
                if (i + 1) % 250 == 0:
                    print(f"{i + 1} of {len(rows)} cached", flush=True)
        groups = rows["group"].to_numpy() + GROUP_OFFSET
        split = stratified_group_split(groups, rows["label"].to_numpy(dtype=str),
                                       SPLIT["val"], SPLIT["test"], SPLIT["seed"])
        out = pd.DataFrame({
            "source": SOURCE, "setting": "field", "member": rows["file"],
            "origin": rows["file"], "raw_class": rows["label"], "official_split": "",
            "cache": cached, "dhash": rows["dhash"].astype("int64"),
            "crop_label": rows["crop_label"], "condition": rows["condition"],
            "crop_canonical": rows["crop_label"].where(rows["crop_label"].isin(keys), ""),
            "group": groups, "split": np.asarray(split, dtype=str),
        })
        OUT.mkdir(parents=True, exist_ok=True)
        out.to_parquet(OUT / "images.parquet", index=False)
        counts = out.groupby(["crop_label", "condition", "split"]).size().unstack(fill_value=0)
        rec.metrics = {"rows": len(out), "dropped": dict(dropped),
                       "by_split": out["split"].value_counts().to_dict()}
        print(counts.to_string())
        print(json.dumps(rec.metrics, indent=1))
    print("run_id", rec.run_id)


if __name__ == "__main__":
    main()
