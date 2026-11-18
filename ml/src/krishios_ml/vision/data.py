"""Vision datasets for crop identification and disease (Phase 9).

Images are read straight from the downloaded zips (no extraction, to spare disk) and cached
once as 256-px JPEGs. Splits are leakage-aware: near-duplicate images (64-bit difference hash
within ``DUP_BITS`` bits) are grouped with union-find and a whole group always lands in one
split. PlantDoc's own test split is kept as its field-proxy test set, minus any image that is
a near-duplicate of a training image (counted and reported).

Every image row carries ``source`` (plantvillage | plantdoc | paddy_doctor) and ``setting``
(lab | field) so lab-vs-field accuracy can be reported separately.
"""

from __future__ import annotations

import hashlib
import io
import zipfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

IMAGE_EXT = (".jpg", ".jpeg", ".png", ".bmp")
CACHE_SIZE = 256
DUP_BITS = 6


def dhash(img, size: int = 8) -> int:
    """64-bit difference hash of a PIL image (robust to resizing and recompression)."""
    g = np.asarray(img.convert("L").resize((size + 1, size), resample=1), dtype=np.int16)
    bits = (g[:, 1:] > g[:, :-1]).flatten()
    return int(np.packbits(bits).view(">u8")[0])


def _popcount64(x: np.ndarray) -> np.ndarray:
    x = x - ((x >> np.uint64(1)) & np.uint64(0x5555555555555555))
    x = (x & np.uint64(0x3333333333333333)) + ((x >> np.uint64(2)) & np.uint64(0x3333333333333333))
    x = (x + (x >> np.uint64(4))) & np.uint64(0x0F0F0F0F0F0F0F0F)
    return ((x * np.uint64(0x0101010101010101)) >> np.uint64(56)).astype(np.int64)


def near_duplicate_groups(hashes: np.ndarray, max_bits: int = DUP_BITS,
                          chunk: int = 512) -> np.ndarray:
    """Union-find over all pairs within ``max_bits`` Hamming distance. Returns a group id per
    item. O(n^2) popcounts in numpy chunks (fine for ~10^5 images)."""
    h = hashes.astype(np.uint64)
    n = len(h)
    parent = np.arange(n)

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for s in range(0, n, chunk):
        block = h[s:s + chunk]
        dist = _popcount64(block[:, None] ^ h[None, :])
        ii, jj = np.nonzero(dist <= max_bits)
        for a, b in zip(ii + s, jj, strict=True):
            if a < b:
                ra, rb = find(int(a)), find(int(b))
                if ra != rb:
                    parent[max(ra, rb)] = min(ra, rb)
    return np.array([find(i) for i in range(n)])


@dataclass(frozen=True, slots=True)
class ZipImage:
    zip_path: Path
    member: str


def list_zip_images(zip_path: Path) -> list[str]:
    """Image members of a zip, or image files (relative paths) under a folder."""
    if zip_path.is_dir():
        return sorted(str(f.relative_to(zip_path)).replace("\\", "/")
                      for f in zip_path.rglob("*") if f.suffix.lower() in IMAGE_EXT)
    with zipfile.ZipFile(zip_path) as z:
        return [m for m in z.namelist() if m.lower().endswith(IMAGE_EXT)
                and not m.startswith("__MACOSX")]


def open_image(zip_path: Path, member: str):
    from PIL import Image

    with zipfile.ZipFile(zip_path) as z:
        return Image.open(io.BytesIO(z.read(member))).convert("RGB")


def cache_name(source: str, member: str) -> str:
    return f"{source}/{hashlib.sha1(member.encode()).hexdigest()[:16]}.jpg"


class _Folder:
    """Same ``read`` interface as ZipFile for a cloned dataset folder."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def read(self, member: str) -> bytes:
        return (self.root / member).read_bytes()

    def __enter__(self):
        return self

    def __exit__(self, *exc) -> None:
        return None


def _open_source(path: Path):
    return _Folder(path) if path.is_dir() else zipfile.ZipFile(path)


def build_cache(rows: pd.DataFrame, cache_dir: Path, log=print) -> pd.DataFrame:
    """Resize every image to CACHE_SIZE (shorter side) once; compute its dHash. Rows need
    ``zip_path, member, source``. Unreadable images are dropped and counted."""
    from PIL import Image

    out = []
    by_zip = rows.groupby("zip_path")
    for zip_path, g in by_zip:
        with _open_source(Path(zip_path)) as z:
            for i, r in enumerate(g.itertuples(index=False)):
                dest = cache_dir / cache_name(r.source, r.member)
                try:
                    if dest.exists():
                        img = Image.open(dest).convert("RGB")
                    else:
                        img = Image.open(io.BytesIO(z.read(r.member))).convert("RGB")
                        img.thumbnail((CACHE_SIZE * 2, CACHE_SIZE * 2))
                        w, h = img.size
                        scale = CACHE_SIZE / min(w, h)
                        img = img.resize((max(1, round(w * scale)), max(1, round(h * scale))),
                                         resample=Image.BICUBIC)
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        tmp = dest.with_suffix(".part")
                        img.save(tmp, format="JPEG", quality=90)
                        tmp.replace(dest)
                    out.append({**r._asdict(), "cache": str(dest.relative_to(cache_dir)),
                                "dhash": dhash(img)})
                except Exception as exc:  # corrupt or non-image member
                    log(f"skip {r.member}: {type(exc).__name__}")
                if i and i % 5000 == 0:
                    log(f"{Path(zip_path).name}: {i}/{len(g)}")
    return pd.DataFrame(out)


def split_groups(groups: np.ndarray, val: float, test: float, seed: str) -> np.ndarray:
    """Deterministic split of whole groups by hashing the group id."""
    def u(gid: int) -> float:
        return int(hashlib.sha256(f"{seed}:{gid}".encode()).hexdigest()[:8], 16) / 0xFFFFFFFF

    return np.array(["test" if (x := u(int(g))) < test else "val" if x < test + val
                     else "train" for g in groups])


# --- Hugging Face Parquet sources (Phase 9 data route) ----------------------------------------

MIN_BOX_PX = 32  # PlantDoc boxes smaller than this (either side) are too small to classify


def parquet_class_names(path: Path) -> list[str]:
    """ClassLabel names stored by `datasets` in the Parquet schema metadata."""
    import json as _json

    import pyarrow.parquet as pq

    meta = pq.read_schema(path).metadata or {}
    info = _json.loads(meta.get(b"huggingface", b"{}"))
    feats = info.get("info", {}).get("features", {})
    label = feats.get("label", {})
    return list(label.get("names", []))


def iter_parquet_samples(path: Path, kind: str, batch_rows: int = 64):
    """Yield (member, raw_class, PIL image, origin) from a HF image Parquet file.

    ``origin`` identifies the source photo: the stored file name for classification rows, the
    photo row for PlantDoc crops (all crops of one photo must share a split).

    ``kind="classification"``: one sample per row (``image``, ``label``).
    ``kind="boxes"``: PlantDoc object-detection rows; each labelled box is cropped into its own
    sample (``objects.bbox`` as COCO [x, y, w, h], ``objects.category``). Boxes are skipped when
    the clipped crop is under MIN_BOX_PX, or when the stored image size disagrees with the
    decoded image (the coordinates cannot be trusted then).
    """
    import pyarrow.parquet as pq
    from PIL import Image

    names = parquet_class_names(path) if kind == "classification" else []
    pf = pq.ParquetFile(path)
    row = 0
    for batch in pf.iter_batches(batch_size=batch_rows):
        d = batch.to_pydict()
        for i in range(batch.num_rows):
            img = Image.open(io.BytesIO(d["image"][i]["bytes"])).convert("RGB")
            if kind == "classification":
                lab = d["label"][i]
                member = f"{path.name}#{row}"
                origin = d["image"][i].get("path") or member
                yield member, names[lab] if names else str(lab), img, origin
            elif (d["width"][i], d["height"][i]) == img.size:
                objs = d["objects"][i] or {}
                for j, (box, cat) in enumerate(zip(objs.get("bbox") or [],
                                                   objs.get("category") or [], strict=False)):
                    x, y, w, h = (float(v) for v in box)
                    left, top = max(0.0, x), max(0.0, y)
                    right, bottom = min(float(img.width), x + w), min(float(img.height), y + h)
                    if right - left < MIN_BOX_PX or bottom - top < MIN_BOX_PX:
                        continue
                    yield (f"{path.name}#{row}#{j}", str(cat),
                           img.crop((left, top, right, bottom)), f"{path.name}#{row}")
            row += 1


def colour_histogram(img, bins: int = 16) -> np.ndarray:
    """RGB histogram: unchanged by flips and rotations, so it links augmented copies."""
    a = np.asarray(img.convert("RGB").resize((64, 64), resample=1))
    return np.concatenate([np.histogram(a[..., c], bins=bins, range=(0, 255))[0]
                           for c in range(3)]).astype(np.float32)


def connected_groups(n: int, keys: list[np.ndarray]) -> np.ndarray:
    """Connected components of ``n`` rows, where rows equal under any key array are linked."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components

    rows, cols = [], []
    for key in keys:
        _, first, inverse = np.unique(key, return_index=True, return_inverse=True)
        rows.append(np.arange(n))
        cols.append(first[inverse])
    r, c = np.concatenate(rows), np.concatenate(cols)
    graph = coo_matrix((np.ones(len(r), dtype=np.int8), (r, c)), shape=(n, n))
    return connected_components(graph, directed=False)[1]


THUMB_PX = 48


def grey_thumbnail(img) -> np.ndarray:
    """Zero-mean, unit-norm grey thumbnail, so a dot product is a pixel correlation."""
    a = np.asarray(img.convert("L").resize((THUMB_PX, THUMB_PX), resample=1), dtype=np.float32)
    a = a - a.mean()
    return a / max(float(np.linalg.norm(a)), 1e-6)


def _dihedral(a: np.ndarray) -> list[np.ndarray]:
    """The 8 flips / 90-degree rotations of a stack of square images (N, H, W)."""
    t = a.transpose(0, 2, 1)
    return [a, a[:, :, ::-1], a[:, ::-1], a[:, ::-1, ::-1],
            t, t[:, :, ::-1], t[:, ::-1], t[:, ::-1, ::-1]]


def augmented_family_groups(names: list[str], labels: list[str], thumbs: np.ndarray,
                            min_corr: float = 0.95, chunk: int = 128) -> np.ndarray:
    """Original-photo groups for a set made of augmented copies (Rice Leaf Disease Image
    Samples). Rows are linked when they share (class, file number) or when, within a class,
    their pixels correlate >= ``min_corr`` under any flip or 90-degree rotation. File numbers
    alone are not enough: identical photos also appear under different numbers."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components

    n = len(names)
    numbers = [Path(p).stem.rsplit("_", 1)[-1] for p in names]
    base = connected_groups(n, [np.array([f"{lab}|{k}" for lab, k in
                                          zip(labels, numbers, strict=True)])])
    labs = np.array(labels)
    a, b = [base], [base]
    for lab in np.unique(labs):
        idx = np.flatnonzero(labs == lab)
        ref = thumbs[idx].reshape(len(idx), -1)
        for s in range(0, len(idx), chunk):
            q = thumbs[idx[s:s + chunk]]
            hit = np.zeros((len(q), len(idx)), dtype=bool)
            for v in _dihedral(q):
                hit |= (v.reshape(len(q), -1) @ ref.T) >= min_corr
            i, j = np.nonzero(hit)
            a.append(base[idx[s:s + chunk][i]])
            b.append(base[idx[j]])
    ga, gb = np.concatenate(a), np.concatenate(b)
    m = int(base.max()) + 1
    graph = coo_matrix((np.ones(len(ga), dtype=np.int8), (ga, gb)), shape=(m, m))
    return connected_components(graph, directed=False)[1][base]


def stratified_group_split(groups: np.ndarray, labels: np.ndarray, val: float, test: float,
                           seed: str) -> np.ndarray:
    """Whole groups go to one split. Within each class, a group bigger than the test share
    (a large cluster of copies) stays in train; the others are taken in a stable hashed order
    until test and then val reach their share of those remaining images."""
    out = np.full(len(groups), "train", dtype=object)
    for lab in np.unique(labels):
        idx = np.flatnonzero(labels == lab)
        ids, counts = np.unique(groups[idx], return_counts=True)
        order = sorted(range(len(ids)), key=lambda i: hashlib.sha256(
            f"{seed}:{lab}:{ids[i]}".encode()).hexdigest())
        movable = counts <= test * len(idx)
        pool = int(counts[movable].sum())
        n_test, n_val = 0, 0
        for i in order:
            if not movable[i]:
                continue
            m = idx[groups[idx] == ids[i]]
            if n_test < test * pool:
                out[m], n_test = "test", n_test + counts[i]
            elif n_val < val * pool:
                out[m], n_val = "val", n_val + counts[i]
    return out.astype(str)


def test_rows_matching_training(hists: np.ndarray, labels: np.ndarray, split: np.ndarray,
                                min_cosine: float = 0.9998) -> np.ndarray:
    """Boolean mask of test rows whose colour histogram is a near-exact match of a train/val
    row of the same class: a last guard against augmented copies crossing the split."""
    unit = hists / np.clip(np.linalg.norm(hists, axis=1, keepdims=True), 1e-9, None)
    out = np.zeros(len(split), dtype=bool)
    for lab in np.unique(labels):
        te = np.flatnonzero((labels == lab) & (split == "test"))
        tr = np.flatnonzero((labels == lab) & (split != "test"))
        if len(te) and len(tr):
            out[te] = (unit[te] @ unit[tr].T).max(axis=1) >= min_cosine
    return out


def save_cached(img, dest: Path) -> None:
    from PIL import Image

    w, h = img.size
    scale = CACHE_SIZE / min(w, h)
    img = img.resize((max(1, round(w * scale)), max(1, round(h * scale))),
                     resample=Image.BICUBIC)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".part")
    img.save(tmp, format="JPEG", quality=90)
    tmp.replace(dest)
