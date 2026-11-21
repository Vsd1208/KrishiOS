# ruff: noqa: E501 - long lines are notebook cell source
"""Generate vision_india_colab.ipynb: retrain the crop / condition model with the Indian field photos.

Run: ``python ml/notebooks/build_vision_colab.py``. Pair it with the bundle from
``make_vision_bundle.py``.
"""

import json
from pathlib import Path

MD, CODE = "markdown", "code"

INTRO = """# KrishiOS vision retraining with Indian field photos (Colab GPU)

Trains experiment **E3_india**: the Phase 9 model's data (PlantVillage, PlantDoc, India rice) plus
4,500 checked Indian field photos of potato, chilli, tomato, soybean and wheat. Chilli and wheat
are new crops for the model. Three seeds; model choice and temperatures use validation photos
only; the test photos (including a held-out 15% of the Indian photos) are scored once.

**Before running**
1. *Runtime > Change runtime type >* **T4 GPU**.
2. In Google Drive, make a folder **`KrishiOS_vision`** and put **`krishios_vision_bundle.zip`** in it.
3. *Runtime > Run all.* Allow Drive access when asked.

The public datasets (about 2 GB) are downloaded from Hugging Face inside Colab; nothing large is
uploaded from the laptop. Each finished seed is saved to `KrishiOS_vision/progress`. **If Colab
disconnects, reconnect and Run all again**: it resumes from the last finished seed. The rebuilt
image cache is also kept in Drive, so a restart does not rebuild it.

Expected time on a T4: about 30 minutes of setup, then about 1-1.5 hours per seed.
At the end, `krishios_vision_results.zip` is written to `KrishiOS_vision`: give that file back
to Claude Code.
"""

GPU = """# 1. GPU check
import torch
print("torch", torch.__version__, "| CUDA:", torch.cuda.is_available())
print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else "WARNING: no GPU, switch to a T4 runtime")
"""

DRIVE = """# 2. Google Drive and the code bundle
import pathlib, zipfile
from google.colab import drive
drive.mount("/content/drive")
DRIVE = pathlib.Path("/content/drive/MyDrive/KrishiOS_vision")
BUNDLE = DRIVE / "krishios_vision_bundle.zip"
assert BUNDLE.exists(), f"put krishios_vision_bundle.zip in {DRIVE}"
ROOT = pathlib.Path("/content/KrishiOS")
if not (ROOT / "ml").exists():
    with zipfile.ZipFile(BUNDLE) as z:
        z.extractall(ROOT)
ML = ROOT / "ml"
for rel in ("reports/data", "experiments", "data/interim"):  # the scripts write here
    (ML / rel).mkdir(parents=True, exist_ok=True)
print("bundle:", (ROOT / "BUNDLE_COMMIT").read_text().strip())
"""

DEPS = """# 3. Dependencies. Pillow and pandas match the laptop, because image hashes decide the splits.
!pip -q install "timm==1.0.31" "pillow==13.0.0" "pandas==2.3.3" "pyarrow>=19" "huggingface_hub>=0.30" loguru pydantic-settings
import os, sys, subprocess
sys.path.insert(0, str(ML / "src"))
os.environ["PYTHONPATH"] = str(ML / "src")
def run(script, *args):
    # Streams the script's output; on failure, repeats its last 40 lines so the cause is easy to copy.
    print(">>", script, *args, flush=True)
    p = subprocess.Popen([sys.executable, "-u", f"scripts/{script}", *args], cwd=ML,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    tail = []
    for line in p.stdout:
        print(line, end="", flush=True)
        tail = (tail + [line])[-40:]
    if p.wait():
        print("\\n===== last lines of", script, "=====\\n" + "".join(tail))
        raise SystemExit(f"{script} failed (exit {p.returncode}); copy the lines above")
"""

DATA = """# 4. Public datasets and the shared image cache (restored from Drive when it is there)
import shutil, tarfile
V1 = ML / "data/processed/vision/v1"
CACHE_TAR = DRIVE / "v1_cache.tar"
if not (V1 / "images.parquet").exists():
    if CACHE_TAR.exists() and (DRIVE / "v1_images.parquet").exists():
        print("restoring the cache from Drive")
        with tarfile.open(CACHE_TAR) as t:
            t.extractall(V1)
        shutil.copy(DRIVE / "v1_images.parquet", V1 / "images.parquet")
    else:
        try:
            from google.colab import userdata
            os.environ["HF_TOKEN"] = userdata.get("HF_TOKEN")  # optional: these datasets are public
        except Exception:
            pass
        run("download_vision_datasets.py")
        run("build_vision_dataset.py")
        with tarfile.open(CACHE_TAR, "w") as t:  # keeps a restart from rebuilding the cache
            for p in (V1 / "cache").iterdir():
                if p.name != "india_field":
                    t.add(p, arcname=f"cache/{p.name}")
        shutil.copy(V1 / "images.parquet", DRIVE / "v1_images.parquet")
print(len(list((V1 / "cache").rglob("*.jpg"))), "cached images")
"""

VERIFY = """# 5. Integrity check: the rebuilt splits must equal the laptop's exactly
import pandas as pd
KEY = ["source", "member", "raw_class", "crop_label", "condition", "split"]
local = pd.read_parquet(ROOT / "reference_v1_images.parquet")[KEY]
colab = pd.read_parquet(V1 / "images.parquet")[KEY]
diff = local.merge(colab, how="outer", indicator=True).query("_merge != 'both'")
print(len(local), "laptop rows,", len(colab), "Colab rows,", len(diff), "differences")
if len(diff):
    print(diff.head(20).to_string())
    raise SystemExit("STOP: the splits differ from the laptop's; do not train. Send this output back.")
india = pd.read_parquet(ML / "data/processed/vision/india_v1/images.parquet")
missing = [c for c in india["cache"] if not (V1 / "cache" / c).exists()]
assert not missing, f"{len(missing)} Indian photos missing from the bundle"
print(india.groupby("split").size().to_dict(), "Indian photos by split")
"""

TRAIN = """# 6. Train E3_india, three seeds (resumes from Drive after a disconnect)
run("train_vision.py", "--with-india", "--experiments", "E3_india", "--seeds", "0", "1", "2",
    "--epochs", "8", "--progress-dir", str(DRIVE / "progress"))
"""

PACK = """# 7. Results to Drive: logs, per-run report and the trained weights
import glob
out = pathlib.Path("/content/krishios_vision_results")
if out.exists():
    shutil.rmtree(out)
for rel in ("ml/experiments", "ml/reports/data"):
    shutil.copytree(ROOT / rel, out / rel)
runs = sorted(glob.glob(str(ML / "artifacts/vision/runs/*")), key=os.path.getmtime)
if runs:
    shutil.copytree(runs[-1], out / "ml/artifacts/vision/runs" / pathlib.Path(runs[-1]).name)
(out / "GPU.txt").write_text(torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu")
shutil.make_archive("/content/krishios_vision_results", "zip", out)
shutil.copy("/content/krishios_vision_results.zip", DRIVE)
print("saved", DRIVE / "krishios_vision_results.zip")
"""

CELLS = [(MD, INTRO), (CODE, GPU), (CODE, DRIVE), (CODE, DEPS), (CODE, DATA), (CODE, VERIFY),
         (CODE, TRAIN), (CODE, PACK)]


def main() -> None:
    nb = {"nbformat": 4, "nbformat_minor": 5,
          "metadata": {"accelerator": "GPU", "colab": {"provenance": [], "gpuType": "T4"},
                       "kernelspec": {"name": "python3", "display_name": "Python 3"},
                       "language_info": {"name": "python"}},
          "cells": []}
    for kind, src in CELLS:
        cell = {"cell_type": kind, "metadata": {}, "source": src.strip("\n").splitlines(True)}
        if kind == CODE:
            cell.update({"execution_count": None, "outputs": []})
        nb["cells"].append(cell)
    out = Path(__file__).with_name("vision_india_colab.ipynb")
    out.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
    print("wrote", out, len(CELLS), "cells")


if __name__ == "__main__":
    main()
