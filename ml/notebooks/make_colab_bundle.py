"""Build a Colab bundle from the committed HEAD.

Default: ``krishios_colab_bundle.zip`` with code and evaluation sets only (backend/app, ml/src,
ml/scripts, ml/evaluation_sets, ml/reference) plus BUNDLE_COMMIT. No .env, secrets or data.

``--yield``: ``krishios_phase10_bundle.zip`` with the same code plus the processed yield data for
the Phase 10 B5 experiments, restricted to the training and validation years (up to 2018):
labels of the ``train`` and ``val`` splits only, and inputs (weather, NDVI) up to 2018. The test
years and the spatial-test districts are not in it, so it cannot be used to score them. The data
is public (APY/UPAg, NASA POWER, MODIS) and contains no farmer data.

Usage (repo root)::

    python ml/notebooks/make_colab_bundle.py
    ml/.venv/Scripts/python ml/notebooks/make_colab_bundle.py --yield
"""

import argparse
import io
import subprocess
import tarfile
import zipfile
from pathlib import Path

PATHS = ["backend/app", "ml/src", "ml/scripts", "ml/evaluation_sets", "ml/reference"]
LAST_DEV_YEAR = 2018  # validation ends here; 2019-22 are the test years
YIELD = "ml/data/processed/yield_features/v1"
LABELS = "ml/data/processed/yield_labels/v1/labels.parquet"


def yield_files(root: Path) -> dict[str, bytes]:
    import numpy as np
    import pandas as pd

    def parquet(df: pd.DataFrame) -> bytes:
        buf = io.BytesIO()
        df.to_parquet(buf, index=False)
        return buf.getvalue()

    out = {}
    labels = pd.read_parquet(root / LABELS)
    dev = labels[labels["split"].isin(["train", "val"])]
    assert dev["crop_year"].max() <= LAST_DEV_YEAR
    out[LABELS] = parquet(dev)
    for name in ("season_features.parquet", "season_ndvi.parquet"):
        df = pd.read_parquet(root / YIELD / name)
        out[f"{YIELD}/{name}"] = parquet(df[df["crop_year"] <= LAST_DEV_YEAR])
    with np.load(root / YIELD / "sequences.npz") as z:
        keep = z["crop_year"] <= LAST_DEV_YEAR
        arrays = {k: z[k][keep] for k in z.files}
    buf = io.BytesIO()
    np.savez(buf, **arrays)
    out[f"{YIELD}/sequences.npz"] = buf.getvalue()
    print(f"yield data: {len(dev)} labelled rows (train/val), {int(keep.sum())} timelines, "
          f"years up to {LAST_DEV_YEAR}")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--yield", dest="with_yield", action="store_true",
                    help="add the Phase 10 yield data (train/val years only)")
    args = ap.parse_args()
    root = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip())
    commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=root,
                                     text=True).strip()
    tar_bytes = subprocess.check_output(["git", "archive", "--format=tar", "HEAD", *PATHS],
                                        cwd=root)
    name = "krishios_phase10_bundle.zip" if args.with_yield else "krishios_colab_bundle.zip"
    out = root / "ml" / "notebooks" / name
    extra = yield_files(root) if args.with_yield else {}
    with tarfile.open(fileobj=io.BytesIO(tar_bytes)) as tar, \
            zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for member in tar.getmembers():
            if member.isfile():
                data = tar.extractfile(member).read()  # type: ignore[union-attr]
                zf.writestr(member.name, data)
        for path, data in extra.items():
            zf.writestr(path, data)
        zf.writestr("BUNDLE_COMMIT", commit + "\n")
    print(f"wrote {out} ({out.stat().st_size / 1e6:.1f} MB) from commit {commit}")


if __name__ == "__main__":
    main()
