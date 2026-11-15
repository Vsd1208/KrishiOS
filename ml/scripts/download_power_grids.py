"""Download NASA POWER daily regional grids for India into the raw cache (resumable).

Usage (from ml/)::

    uv run python scripts/download_power_grids.py --start 1997 --end 2024
"""

from __future__ import annotations

import argparse

import _bootstrap  # noqa: F401

from krishios_ml.common.paths import DATA_DIR
from krishios_ml.yield_features.power import download

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=int, default=1997)
    ap.add_argument("--end", type=int, default=2024)
    a = ap.parse_args()
    stats = download(DATA_DIR / "raw" / "nasa_power" / "daily_regional", range(a.start, a.end + 1),
                     log=lambda m: print(m, flush=True))
    print("done", stats)
