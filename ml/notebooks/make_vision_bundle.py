"""Build ml/notebooks/krishios_vision_bundle.zip for retraining the vision model on Colab.

Contents:
- code and reference files (backend/app, ml/src, ml/scripts, ml/reference, ml/experiments) from
  the working tree, with BUNDLE_COMMIT naming the commit and whether files were uncommitted;
- ``ml/data/processed/vision/india_v1/images.parquet`` and the cached Indian field photos
  (256 px, about 150 MB), from ``scripts/prepare_india_vision.py``;
- ``reference_v1_images.parquet``: the local PlantVillage / PlantDoc / India rice split table.
  Colab downloads those public datasets itself and rebuilds the table; the notebook stops if
  any row's split or label differs, so no test image can move into training.

No .env, secrets or farmer data: every photo is from a public research dataset.

Usage (repo root of this worktree)::

    ml/.venv/Scripts/python ml/notebooks/make_vision_bundle.py
"""

import subprocess
import zipfile
from pathlib import Path

PATHS = ["backend/app", "ml/src", "ml/scripts", "ml/reference", "ml/experiments",
         "ml/pyproject.toml"]
VISION = Path("ml/data/processed/vision")


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def main() -> None:
    root = Path(git(Path.cwd(), "rev-parse", "--show-toplevel"))
    commit = git(root, "rev-parse", "--short", "HEAD")
    dirty = bool(git(root, "status", "--porcelain", "--", *PATHS))
    files = git(root, "ls-files", "-co", "--exclude-standard", "--", *PATHS).splitlines()
    india = root / VISION / "india_v1" / "images.parquet"
    if not india.exists():
        raise SystemExit("run scripts/prepare_india_vision.py first")
    import pandas as pd

    rows = pd.read_parquet(india)
    out = root / "ml" / "notebooks" / "krishios_vision_bundle.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel in files:
            if (root / rel).is_file():
                zf.write(root / rel, rel)
        zf.write(india, str(VISION / "india_v1" / "images.parquet").replace("\\", "/"))
        for rel in rows["cache"]:
            src = root / VISION / "v1" / "cache" / rel
            if not src.exists():
                raise SystemExit(f"missing cached photo {src}; rerun prepare_india_vision.py")
            zf.write(src, f"{VISION.as_posix()}/v1/cache/{rel}", compress_type=zipfile.ZIP_STORED)
        zf.write(root / VISION / "v1" / "images.parquet", "reference_v1_images.parquet")
        zf.writestr("BUNDLE_COMMIT", f"{commit}{' + uncommitted changes' if dirty else ''}\n")
    print(f"wrote {out} ({out.stat().st_size / 1e6:.0f} MB) from {commit}"
          f"{' with uncommitted changes' if dirty else ''}; {len(rows)} Indian photos")


if __name__ == "__main__":
    main()
