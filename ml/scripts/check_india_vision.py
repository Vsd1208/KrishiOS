"""Quality check for the downloaded Indian field photos (no network, no training).

Looks for:
1. exact copies (same SHA-256) and whether any copy carries a different label;
2. near copies inside the Indian set (difference hash within ``DUP_BITS``), across classes;
3. near copies of Phase 9 training images, which would make an "independent" test unfair;
4. photo sizes per class, since a class that differs only in camera or resolution can be
   learned from the size alone.

The result is written next to the photos as ``quality.json`` (git-ignored with them).

Usage (from ml/)::

    python -I scripts/check_india_vision.py
"""

from __future__ import annotations

import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

import _bootstrap  # noqa: F401
import numpy as np
import pandas as pd
from PIL import Image

from krishios_ml.common.paths import DATA_DIR
from krishios_ml.vision.data import DUP_BITS, _popcount64, dhash, near_duplicate_groups

ROOT = DATA_DIR / "raw" / "vision" / "india"
TRAIN_DIR = DATA_DIR / "processed" / "vision" / "v1"
TRAIN_INDEX = TRAIN_DIR / "images.parquet"
Image.MAX_IMAGE_PIXELS = 80_000_000
# The 64-bit hash groups photos that merely share a layout (one leaf on black, wide black
# borders), so matches are confirmed with a 256-bit hash of the photo with dark borders trimmed.
FINE_SIZE = 16
FINE_BITS = 20  # of 256 (about 8%, close to the 6 of 64 used for training data)


def load(path) -> Image.Image:
    with Image.open(path) as im:
        im.draft("RGB", (512, 512))  # fast JPEG decode at reduced size; hashes are size-robust
        im = im.convert("RGB")
        im.thumbnail((512, 512))
        return im


def fine_hash(im: Image.Image) -> np.ndarray:
    """256-bit difference hash after trimming near-black borders, as four uint64 words."""
    g = im.convert("L")
    box = g.point(lambda v: 255 if v > 24 else 0).getbbox()
    if box and (box[2] - box[0]) * (box[3] - box[1]) > 0.05 * g.width * g.height:
        g = g.crop(box)
    a = np.asarray(g.resize((FINE_SIZE + 1, FINE_SIZE), resample=1), dtype=np.int16)
    return np.packbits((a[:, 1:] > a[:, :-1]).flatten()).view(">u8").astype(np.uint64)


def fine_distance(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Hamming distance between one hash ``a`` (4,) and many ``b`` (n, 4)."""
    return _popcount64(b ^ a).sum(axis=-1)


def photo_hashes(rel: str) -> tuple[int, np.ndarray]:
    im = load(ROOT / rel)
    return dhash(im), fine_hash(im)


def fine_groups(h: np.ndarray) -> np.ndarray:
    parent = np.arange(len(h))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(len(h)):
        for j in np.nonzero(fine_distance(h[i], h[i + 1:]) <= FINE_BITS)[0] + i + 1:
            ri, rj = find(i), find(int(j))
            if ri != rj:
                parent[rj] = ri
    return np.array([find(i) for i in range(len(h))])


def main() -> None:
    lines = (ROOT / "manifest.jsonl").read_text(encoding="utf-8").splitlines()
    m = pd.DataFrame([json.loads(x) for x in lines])
    m["label"] = m["crop"] + "/" + m["raw_class"]
    out: dict = {"photos": len(m), "files": int(m["sha256"].nunique())}

    # 1. exact copies
    by_hash = m.groupby("sha256")["label"].agg(lambda s: sorted(set(s)))
    counts = m.groupby("sha256").size()
    out["exact_copy_rows"] = int((counts[counts > 1] - 1).sum())
    conflicts = by_hash[by_hash.map(len) > 1]
    out["exact_label_conflicts"] = {h[:12]: v for h, v in conflicts.items()}
    out["exact_copies_by_label"] = dict(Counter(m[m.duplicated("sha256", keep="first")]["label"]))

    # 2. near copies inside the Indian set (one row per file)
    files = m.drop_duplicates("sha256").reset_index(drop=True)
    with ThreadPoolExecutor(6) as pool:
        both = list(pool.map(photo_hashes, files["file"]))
    files["dhash"] = [b[0] for b in both]
    fine = np.stack([b[1] for b in both])
    hashes = files["dhash"].to_numpy(dtype=np.uint64)
    coarse = near_duplicate_groups(hashes)
    out["coarse_groups_extra_files"] = int(len(files) - len(set(coarse.tolist())))
    files["group"] = fine_groups(fine)
    sizes = files.groupby("group").size()
    multi = files[files["group"].isin(sizes[sizes > 1].index)]
    out["near_copy_groups"] = int((sizes > 1).sum())
    out["near_copy_extra_files"] = int((sizes[sizes > 1] - 1).sum())
    mixed = multi.groupby("group")["label"].agg(lambda s: sorted(set(s)))
    mixed = mixed[mixed.map(len) > 1]
    out["near_copy_label_conflicts"] = len(mixed)
    out["near_copy_conflict_examples"] = [v for v in mixed.head(15)]
    out["near_copy_extra_by_label"] = dict(Counter(
        multi[multi.duplicated("group", keep="first")]["label"]))

    # 3. overlap with Phase 9 training images
    train = pd.read_parquet(TRAIN_INDEX, columns=["cache", "crop_label", "dhash"])
    th = train["dhash"].to_numpy(dtype=np.uint64)
    candidates = {i: np.nonzero(_popcount64(th ^ h) <= DUP_BITS)[0] for i, h in enumerate(hashes)}
    candidates = {i: c for i, c in candidates.items() if len(c)}
    out["coarse_training_matches"] = dict(Counter(files.loc[list(candidates), "label"]))
    train_fine: dict[int, np.ndarray] = {}
    near_train = np.zeros(len(files), dtype=bool)
    for i, cand in candidates.items():
        for j in cand:
            if j not in train_fine:
                train_fine[j] = fine_hash(load(TRAIN_DIR / "cache" / train.at[j, "cache"]))
        near_train[i] = bool((fine_distance(fine[i], np.stack([train_fine[j] for j in cand]))
                              <= FINE_BITS).any())
    files["near_train"] = near_train
    out["near_training_images"] = dict(Counter(files.loc[near_train, "label"]))

    # 4. sizes per class
    m["pixels_mp"] = m["width"] * m["height"] / 1e6
    shape = m.groupby("label").agg(
        photos=("sha256", "size"),
        median_mp=("pixels_mp", "median"),
        distinct_sizes=("pixels_mp", lambda s: int(s.round(2).nunique())))
    wh = m["width"].astype(str) + "x" + m["height"].astype(str)
    shape["common_size"] = wh.groupby(m["label"]).agg(
        lambda s: f"{s.value_counts().index[0]} ({s.value_counts().iloc[0]})")
    out["per_class"] = json.loads(shape.round(2).to_json(orient="index"))

    # one file per near-copy group, none close to a training image
    clean = files[~near_train & ~files["group"].duplicated(keep="first")]
    out["usable_files"] = len(clean)
    out["usable_by_label"] = dict(Counter(clean["label"]))
    (ROOT / "quality.json").write_text(json.dumps(out, indent=1, default=int), encoding="utf-8")
    files[["sha256", "file", "label", "dhash", "group", "near_train"]].to_parquet(
        ROOT / "quality_files.parquet", index=False)
    print(json.dumps({k: v for k, v in out.items() if k != "per_class"}, indent=1, default=int))
    print(pd.DataFrame(out["per_class"]).T.to_string())


if __name__ == "__main__":
    main()
