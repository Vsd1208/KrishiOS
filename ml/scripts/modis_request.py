"""MOD13A3 monthly NDVI for India via AppEEARS: submit / status / sizes / download.

Usage (from ml/)::

    uv run --no-sync python scripts/modis_request.py submit     # once
    uv run --no-sync python scripts/modis_request.py status
    uv run --no-sync python scripts/modis_request.py sizes      # total size before download
    uv run --no-sync python scripts/modis_request.py download   # resumable

The task id is kept in data/raw/modis/mod13a3/task.json. Credentials: ml/.env (never logged).
"""

from __future__ import annotations

import argparse
import json
from collections import Counter

import _bootstrap  # noqa: F401

from krishios_ml.common.paths import DATA_DIR, ML_ROOT
from krishios_ml.yield_features import modis

OUT = DATA_DIR / "raw" / "modis" / "mod13a3"
TASK = OUT / "task.json"
ENV = ML_ROOT / ".env"
ADM1 = DATA_DIR / "raw" / "boundaries" / "20261114" / "geoBoundaries-IND-ADM1.geojson"
START, END = "02-01-2000", "12-31-2024"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["submit", "status", "sizes", "download"])
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    with modis.session(ENV) as token:
        if args.action == "submit":
            if TASK.exists():
                raise SystemExit(f"already submitted: {json.loads(TASK.read_text())['task_id']}")
            import geopandas as gpd

            aoi = modis.india_aoi(gpd.read_file(ADM1).to_crs(4326))
            n = sum(len(ring) for f in aoi["features"]
                    for poly in f["geometry"]["coordinates"] for ring in poly)
            body = modis.task_body("krishios-india-mod13a3-ndvi", aoi, START, END)
            task_id = modis.submit(token, body)
            TASK.write_text(json.dumps({"task_id": task_id, "product": modis.PRODUCT,
                                        "layers": modis.LAYERS, "start": START, "end": END,
                                        "aoi_vertices": n}, indent=1))
            print("submitted", task_id, "aoi vertices", n)
            return
        task_id = json.loads(TASK.read_text())["task_id"]
        if args.action == "status":
            s = modis.status(token, task_id)
            print({k: s.get(k) for k in ("status", "created", "updated", "progress", "error")})
            return
        files = modis.bundle(token, task_id)
        if args.action == "sizes":
            kinds = Counter(f["file_type"] for f in files)
            total = sum(f["file_size"] for f in files)
            print(len(files), "files", dict(kinds), f"{total / 1e9:.2f} GB")
            return
        for i, f in enumerate(files, 1):
            modis.download(token, task_id, f, OUT / "files")
            if i % 25 == 0:
                print(f"{i}/{len(files)}")
        print("downloaded", len(files))


if __name__ == "__main__":
    main()
