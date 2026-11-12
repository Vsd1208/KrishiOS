"""Build the English source side of the agri MT test set from real public advisories.

Sources (public government text):
* ICAR-CRIDA National Agromet Advisory Services (NAAS) bulletins (PDF, English portion);
* NDMA SACHET CAP alerts (IMD/SDMA headlines), fetched from the public RSS feed.

Selection: English sentences of 6-45 words that contain an agricultural or weather action
term. Weather-only region lists are excluded. Each row keeps its provenance (document, page
or CAP identifier). References in te/hi are written by native reviewers into
``references_template.tsv``; this script never produces references.

Usage: ``uv run python -m krishios_ml.translation.evaluation.build_source_set``
"""

from __future__ import annotations

import csv
import re
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

import pymupdf
from loguru import logger

from krishios_ml.common.paths import DATA_DIR, ML_ROOT

OUT_DIR = ML_ROOT / "evaluation_sets" / "mt"
SACHET_RSS = "https://sachet.ndma.gov.in/cap_public_website/rss/rss_india.xml"
_AGRI = re.compile(
    r"\b(spray|apply|applied|sow|sowing|sown|irrigat\w*|drain\w*|harvest\w*|fertili[sz]\w*|"
    r"urea|pest\w*|disease\w*|insect\w*|weed\w*|nursery|transplant\w*|mulch\w*|stor\w+|"
    r"crop\w*|paddy|rice|maize|cotton|soybean|pulses|groundnut|wheat|vegetables?|orchards?|"
    r"livestock|cattle|animals?|poultry|fish\w*|fodder|rain\w*|thunderstorm|lightning|"
    r"wind\w*|temperature|heat\w*)\b",
    re.IGNORECASE,
)
_REGION_LIST = re.compile(r"(?:,\s*[A-Z][a-z]+(?:[\s-][A-Z][a-z]+)*){4,}")
MIN_WORDS, MAX_WORDS = 6, 45


def _english_sentences(text: str) -> list[str]:
    text = re.sub(r"\s*\n\s*", " ", text)
    text = re.sub(r"[•●▪]\s*", ". ", text)
    out = []
    for sent in re.split(r"(?<=[.!?])\s+", text):
        sent = sent.strip(" .;:-")
        if not sent:
            continue
        ascii_ratio = sum(c.isascii() for c in sent) / len(sent)
        words = sent.split()
        if ascii_ratio < 0.97 or not MIN_WORDS <= len(words) <= MAX_WORDS:
            continue
        if not _AGRI.search(sent) or _REGION_LIST.search(sent):
            continue
        out.append(sent + ".")
    return out


def from_pdfs(pdf_dir: Path) -> list[dict]:
    rows = []
    for pdf in sorted(pdf_dir.glob("naas_*.pdf")):
        doc = pymupdf.open(pdf)
        for page_no, page in enumerate(doc, start=1):
            for sent in _english_sentences(page.get_text()):
                rows.append({"source_doc": pdf.name, "locator": f"page {page_no}", "text": sent})
    return rows


def from_sachet(limit: int = 60) -> list[dict]:
    req = urllib.request.Request(SACHET_RSS, headers={"User-Agent": "krishios-eval/0.1"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        root = ET.fromstring(resp.read())
    rows = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        for sent in _english_sentences(title):
            rows.append({"source_doc": "SACHET CAP", "locator": link, "text": sent})
    return rows[:limit]


def _dedupe(rows: list[dict], seen: set[str]) -> list[dict]:
    out = []
    for r in rows:
        key = r["text"].casefold()
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out


def build(per_pdf: int = 65, sachet: int = 30) -> Path:
    """Balanced set: up to ``per_pdf`` sentences per bulletin (sentences with digits first,
    since doses and dates are what the safety checks must protect) plus SACHET alerts."""
    seen: set[str] = set()
    unique: list[dict] = []
    by_doc: dict[str, list[dict]] = {}
    for r in from_pdfs(DATA_DIR / "raw" / "advisories"):
        by_doc.setdefault(r["source_doc"], []).append(r)
    for rows in by_doc.values():
        rows = _dedupe(rows, seen)
        rows.sort(key=lambda r: not re.search(r"\d", r["text"]))  # stable: digits first
        unique.extend(rows[:per_pdf])
    unique.extend(_dedupe(from_sachet(limit=200), seen)[:sachet])
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "source_en.tsv"
    with out.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, delimiter="\t")
        w.writerow(["id", "source_doc", "locator", "text"])
        for i, r in enumerate(unique, start=1):
            w.writerow([f"mt{i:04d}", r["source_doc"], r["locator"], r["text"]])
    tmpl = OUT_DIR / "references_template.tsv"
    if not tmpl.exists():
        with tmpl.open("w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh, delimiter="\t")
            w.writerow(["id", "reference_te", "reference_hi", "reviewer_te", "reviewer_hi",
                        "notes"])
            for i in range(1, len(unique) + 1):
                w.writerow([f"mt{i:04d}", "", "", "", "", ""])
    logger.info("wrote {} source sentences -> {}", len(unique), out)
    return out


if __name__ == "__main__":  # pragma: no cover
    build()
