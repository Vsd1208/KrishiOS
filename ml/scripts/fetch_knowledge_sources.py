"""Phase 10c: fetch the vetted agriculture library for the AI assistant (a fixed, named list).

Each source is an official publication of a state agricultural university or an ICAR institute,
fetched once from its own address (no crawling). Files go to ``data/raw/knowledge/`` with a
``manifest.json`` recording URL, publisher, crops, region, size, SHA-256 and fetch time.
Approved by the project owner on 2026-11-21 (small named set, under 200 MB, non-commercial use).

Usage (from ml/)::

    python -I scripts/fetch_knowledge_sources.py
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "data" / "raw" / "knowledge"
MAX_BYTES = 60_000_000  # per file
TOTAL_LIMIT = 200_000_000
UA = "Mozilla/5.0 (KrishiOS academic research)"
LICENCE = ("Public extension publication; not under an open licence. Used for non-commercial "
           "academic research with attribution; not redistributed.")

SOURCES = [
    {"id": "tnau_cpg_agriculture_2020", "url": "https://agritech.tnau.ac.in/pdf/AGRICULTURE.pdf",
     "title": "Crop Production Guide: Agriculture (2020)",
     "publisher": "Tamil Nadu Agricultural University and Department of Agriculture, Tamil Nadu",
     "region": "Tamil Nadu", "crops": ["paddy", "cotton", "maize", "pulses", "groundnut"]},
    {"id": "pau_pop_kharif", "url": "https://www.pau.edu/content/ccil/pf/pp_kharif.pdf",
     "title": "Package of Practices for Kharif Crops",
     "publisher": "Punjab Agricultural University",
     "region": "Punjab", "crops": ["paddy", "cotton", "maize", "pulses"]},
    {"id": "pau_pop_rabi", "url": "https://www.pau.edu/content/ccil/pf/pp_rabi.pdf",
     "title": "Package of Practices for Rabi Crops", "publisher": "Punjab Agricultural University",
     "region": "Punjab", "crops": ["wheat", "pulses", "oilseeds"]},
    {"id": "crri_tb250",
     "url": "https://icar-crri.in/wp-content/uploads/2025/12/CRRI_Technology-Bulletin_No-250.pdf",
     "title": "CRRI Technology Bulletin No. 250",
     "publisher": "ICAR-National Rice Research Institute",
     "region": "India", "crops": ["paddy"]},
    {"id": "tnau_cpg_horticulture_2020", "url": "https://agritech.tnau.ac.in/pdf/HORTICULTURE.pdf",
     "title": "Crop Production Guide: Horticulture (2020)",
     "publisher": "Tamil Nadu Agricultural University and Department of Horticulture, Tamil Nadu",
     "region": "Tamil Nadu", "crops": ["chilli", "tomato", "potato", "onion"]},
]


def fetch(url: str, dest: Path) -> tuple[int, str]:
    """Download with curl (handles these sites' TLS); returns (exit code, content type)."""
    tmp = dest.with_suffix(dest.suffix + ".part")
    r = subprocess.run(["curl.exe", "-sSL", "--max-time", "300", "-A", UA, "--max-filesize",
                        str(MAX_BYTES), "-o", str(tmp), "-w", "%{http_code} %{content_type}", url],
                       capture_output=True, text=True, check=False)
    code, _, ctype = r.stdout.partition(" ")
    if r.returncode == 0 and code == "200":
        tmp.replace(dest)
        return 0, ctype
    tmp.unlink(missing_ok=True)
    return r.returncode or int(code or 1), r.stderr.strip()[:120] or f"HTTP {code}"


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    manifest_path = ROOT / "manifest.json"
    manifest = (json.loads(manifest_path.read_text(encoding="utf-8"))
                if manifest_path.exists() else {})
    total = sum(m.get("bytes", 0) for m in manifest.values())
    for src in SOURCES:
        ext = ".pdf" if src["url"].lower().endswith(".pdf") else ".html"
        dest = ROOT / f"{src['id']}{ext}"
        if src["id"] in manifest and dest.exists():
            print("have", src["id"])
            continue
        status, info = fetch(src["url"], dest)
        if status != 0:
            print(f"SKIP {src['id']}: {info}")
            continue
        data = dest.read_bytes()
        if total + len(data) > TOTAL_LIMIT:
            dest.unlink()
            print(f"SKIP {src['id']}: total limit")
            continue
        total += len(data)
        manifest[src["id"]] = {**src, "file": dest.name, "bytes": len(data),
                               "sha256": hashlib.sha256(data).hexdigest(), "content_type": info,
                               "fetched_at": datetime.now(UTC).isoformat(timespec="seconds"),
                               "licence": LICENCE}
        print(f"got {src['id']}: {len(data) / 1e6:.2f} MB")
        manifest_path.write_text(json.dumps(manifest, indent=1, ensure_ascii=False),
                                 encoding="utf-8")
    print(f"{len(manifest)} sources, {total / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
