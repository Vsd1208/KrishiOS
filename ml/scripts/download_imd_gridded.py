"""Download IMD gridded daily rainfall (0.25 deg) and max/min temperature (1 deg), 1951-2024.

Source: India Meteorological Department, Pune (imdpune.gov.in/cmpg/Griddata), free for research.
Approved by the project owner for this non-commercial academic project (about 2.1 GB).

Each year is one raw binary file (float32, day x lat x lon; missing = -999 for rain, 99.9 for
temperature). Transfers sometimes end early, so every file must have exactly the expected size
(grid x days x 4 bytes) or it is fetched again. Requests are paced. Two limits apply: the saved
files may not exceed ``DISK_LIMIT`` (the approved size), and all bytes received, including failed
attempts, may not exceed ``TRANSFER_LIMIT``, so a server that keeps dropping connections cannot make
the download run forever. (Until 2026-11-21 one 2.5 GB limit counted failed attempts too, and it
stopped the rain download at 1.3 GB on disk.)

Usage (from ml/)::

    python -I scripts/download_imd_gridded.py
"""

from __future__ import annotations

import calendar
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "data" / "raw" / "imd"
BASE = "https://www.imdpune.gov.in/cmpg/Griddata/"
HEADERS = {"User-Agent": "Mozilla/5.0 (research data client)"}
YEARS = range(1951, 2025)
# variable -> (php endpoint, form field, grid points)
VARS = {"rain": ("rainfall.php", "rain", 135 * 129),
        "tmax": ("maxtemp.php", "maxtemp", 31 * 31),
        "tmin": ("mintemp.php", "mintemp", 31 * 31)}
DISK_LIMIT = 2_200_000_000  # saved files; the full 1951-2024 set is about 1.9 GB
TRANSFER_LIMIT = 4_000_000_000  # everything received, including failed attempts
PAUSE = 3.0
ATTEMPTS = 8
PASSES = 4  # files that keep failing are retried in later passes


def expected(points: int, year: int) -> int:
    return points * 4 * (366 if calendar.isleap(year) else 365)


def on_disk() -> int:
    return sum(f.stat().st_size for f in ROOT.glob("*/*.grd"))


def fetch(var: str, year: int, used: list[int]) -> None:
    php, field, points = VARS[var]
    path = ROOT / var / f"{year}.grd"
    size = expected(points, year)
    if path.exists() and path.stat().st_size == size:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    body = urllib.parse.urlencode({field: str(year)}).encode()
    for attempt in range(1, ATTEMPTS + 1):
        if on_disk() + size > DISK_LIMIT:
            raise SystemExit(f"stopping: {on_disk() / 1e9:.2f} GB on disk, "
                             f"limit {DISK_LIMIT / 1e9} GB")
        if used[0] + size > TRANSFER_LIMIT:
            raise SystemExit(f"stopping: {used[0] / 1e9:.2f} GB transferred, "
                             f"limit {TRANSFER_LIMIT / 1e9} GB")
        tmp = path.with_suffix(".part")
        got = 0
        try:
            req = urllib.request.Request(BASE + php, data=body, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=300) as r, tmp.open("wb") as out:
                while chunk := r.read(1 << 20):
                    out.write(chunk)
                    got += len(chunk)
        except Exception as exc:  # network trouble: count what arrived, then retry
            print(f"{var} {year} attempt {attempt}: {type(exc).__name__}", flush=True)
        used[0] += got
        if got == size:
            tmp.replace(path)
            return
        print(f"{var} {year} attempt {attempt}: {got} of {size} bytes", flush=True)
        tmp.unlink(missing_ok=True)
        time.sleep(min(300.0, PAUSE * 2 ** attempt))
    raise RuntimeError(f"{var} {year}: failed after {ATTEMPTS} attempts")


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    ledger = ROOT / "ledger.json"
    used = [json.loads(ledger.read_text())["bytes"] if ledger.exists() else 0]
    todo = [(var, year) for var in ("tmax", "tmin", "rain") for year in YEARS]
    try:
        for n in range(1, PASSES + 1):
            failed = []
            for var, year in todo:
                before = used[0]
                try:
                    fetch(var, year, used)
                    status = "ok"
                except RuntimeError as exc:  # the server keeps dropping this file: come back later
                    print(f"{exc}; will retry in pass {n + 1}", flush=True)
                    failed.append((var, year))
                    status = "failed"
                if used[0] != before:
                    ledger.write_text(json.dumps({"bytes": used[0]}))
                    print(f"{var} {year} {status}, {on_disk() / 1e9:.3f} GB on disk, "
                          f"{used[0] / 1e9:.3f} GB transferred", flush=True)
                    time.sleep(PAUSE)
            todo = failed
            if not todo:
                break
            print(f"pass {n}: {len(todo)} files still missing; waiting 10 minutes", flush=True)
            time.sleep(600)
    finally:
        ledger.write_text(json.dumps({"bytes": used[0]}))
    if todo:
        raise SystemExit(f"still missing after {PASSES} passes: {todo}")
    print(f"done: {on_disk() / 1e9:.3f} GB on disk, {used[0] / 1e9:.3f} GB transferred")


if __name__ == "__main__":
    sys.exit(main())
