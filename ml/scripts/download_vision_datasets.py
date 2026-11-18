"""Download the Phase 9 vision datasets from Hugging Face (resumable, retrying).

All are open-licence mirrors (see ml/DATA_SOURCES.md):
- Project-AgML/rice_leaf_disease_classification_india  CC BY 4.0  (Sethy et al., Odisha)
- agyaatcoder/PlantDoc                                  CC BY 4.0  (PlantDoc, object boxes)
- DScomp380/plant_village                               CC0 tag    (PlantVillage, Mendeley)

Files land in data/raw/vision/hf/<owner>__<name>/ (git-ignored). Interrupted downloads resume
from the partial file; each file is retried until complete.

Usage (from ml/)::

    uv run --no-sync python scripts/download_vision_datasets.py
"""

from __future__ import annotations

import time

import _bootstrap  # noqa: F401

from krishios_ml.common.paths import DATA_DIR

REPOS = [
    "Project-AgML/rice_leaf_disease_classification_india",
    "agyaatcoder/PlantDoc",
    "DScomp380/plant_village",
]
OUT = DATA_DIR / "raw" / "vision" / "hf"
ATTEMPTS = 60


def main() -> None:
    from huggingface_hub import HfApi, hf_hub_download

    api = HfApi()
    for repo in REPOS:
        dest = OUT / repo.replace("/", "__")
        files = [f for f in api.list_repo_files(repo, repo_type="dataset")
                 if f.endswith((".parquet", "README.md"))]
        for f in files:
            for attempt in range(1, ATTEMPTS + 1):
                try:
                    hf_hub_download(repo, f, repo_type="dataset", local_dir=dest)
                    print(f"ok {repo}/{f}", flush=True)
                    break
                except Exception as exc:  # flaky network: resume on the next attempt
                    print(f"retry {attempt} {repo}/{f}: {type(exc).__name__}", flush=True)
                    time.sleep(min(60, 5 * attempt))
            else:
                print(f"FAILED {repo}/{f}", flush=True)


if __name__ == "__main__":
    main()
