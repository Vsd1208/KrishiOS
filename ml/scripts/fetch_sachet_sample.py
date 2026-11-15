"""Download a snapshot of NDMA SACHET CAP alerts and build the bulletin-extraction benchmark.

Source: https://sachet.ndma.gov.in/cap_public_website/rss/rss_india.xml (RSS 2.0, the feed
declares ``<copyright>public domain</copyright>``). Each item links to a CAP 1.2 alert whose
structured fields are official labels:

- ``LGD District Code`` geocodes  -> district_codes
- ``severity`` (Minor/Moderate/Severe/Extreme) -> LOW/MEDIUM/HIGH/CRITICAL
- ``expires`` -> valid_to, ``event`` -> hazard (keyword rules, see EVENT_RULES)

The extractor is given only the free text a person would read (headline, description,
instruction), never the structured fields. Requests are sequential, one per second.

Usage (from backend/)::

    uv run python ../ml/scripts/fetch_sachet_sample.py
"""

from __future__ import annotations

import json
import random
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

RSS = "https://sachet.ndma.gov.in/cap_public_website/rss/rss_india.xml"
UA = "KrishiOS-research/0.1"
NS = {"cap": "urn:oasis:names:tc:emergency:cap:1.2"}
ML = Path(__file__).resolve().parents[1]
SEVERITY = {"Minor": "LOW", "Moderate": "MEDIUM", "Severe": "HIGH", "Extreme": "CRITICAL"}
# CAP event -> KrishiOS hazard, by keyword (first rule wins). Light/moderate rain has no
# hazard class in KrishiOS, so it stays unlabelled (None) and is left out of hazard scoring.
EVENT_RULES = [
    ("thunder", "thunderstorm"), ("lightning", "thunderstorm"), ("hail", "hailstorm"),
    ("cyclon", "cyclone"), ("flood", "flood"), ("heat", "heatwave"), ("cold", "cold_wave"),
    ("frost", "cold_wave"), ("fog", "fog"), ("squall", "strong_wind"), ("wind", "strong_wind"),
    ("heavy rain", "heavy_rain"),
]


def map_event(event: str) -> str | None:
    e = event.lower()
    return next((hazard for key, hazard in EVENT_RULES if key in e), None)


DEV_SHARE = 0.4
SEED = 13


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def text(el: ET.Element | None, path: str) -> str:
    found = el.find(path, NS) if el is not None else None
    return (found.text or "").strip() if found is not None and found.text else ""


def parse_cap(xml: bytes) -> dict | None:
    root = ET.fromstring(xml)
    info = root.find("cap:info", NS)
    if info is None:
        return None
    codes = []
    for area in info.findall("cap:area", NS):
        for gc in area.findall("cap:geocode", NS):
            if text(gc, "cap:valueName") == "LGD District Code" and text(gc, "cap:value").isdigit():
                codes.append(int(text(gc, "cap:value")))
    event = text(info, "cap:event")
    return {
        "identifier": text(root, "cap:identifier"), "sender": text(root, "cap:sender"),
        "sent": text(root, "cap:sent"), "language": text(info, "cap:language"),
        "category": text(info, "cap:category"), "event": event,
        "headline": text(info, "cap:headline"), "description": text(info, "cap:description"),
        "instruction": text(info, "cap:instruction"),
        "area_desc": [text(a, "cap:areaDesc") for a in info.findall("cap:area", NS)],
        "labels": {
            "district_codes": sorted(set(codes)),
            "severity": SEVERITY.get(text(info, "cap:severity")),
            "cap_severity": text(info, "cap:severity"),
            "valid_from": text(info, "cap:effective"), "valid_to": text(info, "cap:expires"),
            "hazard": map_event(event),
        },
    }


def main() -> None:
    day = datetime.now(UTC).strftime("%Y%m%d")
    raw = ML / "data" / "raw" / "sachet" / day
    raw.mkdir(parents=True, exist_ok=True)
    rss = get(RSS)
    (raw / "rss_india.xml").write_bytes(rss)
    links = [i.findtext("link") for i in ET.fromstring(rss).iter("item")]
    rows = []
    for n, link in enumerate(links, 1):
        ident = link.rsplit("=", 1)[-1]
        path = raw / f"{ident}.xml"
        if not path.exists():
            path.write_bytes(get(link))
            time.sleep(1.0)
        row = parse_cap(path.read_bytes())
        if row and row["labels"]["district_codes"]:
            row["source_url"] = link
            row["text"] = "\n".join(p for p in (row["headline"], row["description"],
                                                row["instruction"]) if p)
            rows.append(row)
        print(f"{n}/{len(links)}", end="\r", flush=True)
    rng = random.Random(SEED)
    rng.shuffle(rows)
    n_dev = round(len(rows) * DEV_SHARE)
    for i, row in enumerate(rows):
        row["split"] = "dev" if i < n_dev else "test"
    out = ML / "evaluation_sets" / "govconnect" / f"sachet_{day}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in
                             sorted(rows, key=lambda r: r["identifier"])) + "\n", encoding="utf-8")
    print(f"\n{len(rows)} alerts with LGD codes ({n_dev} dev) -> {out.relative_to(ML)}")


if __name__ == "__main__":
    main()
