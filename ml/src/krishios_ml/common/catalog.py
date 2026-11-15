"""Loader and validator for ``ml/reference/crop_catalog.csv``.

The catalog is the single source of truth for crop names across yield, vision, NLU
and RAG. The backend loads the same CSV (see ``backend/app/catalog``).
"""

from __future__ import annotations

import csv
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from krishios_ml.common.paths import REFERENCE_DIR

CATALOG_PATH = REFERENCE_DIR / "crop_catalog.csv"

REQUIRED_COLUMNS = (
    "crop_canonical", "name_en", "name_te", "name_hi", "aliases", "scientific_name",
    "crop_group", "domain", "seasons", "yield_unit", "apy_names", "tier",
    "vision_supported", "review_status",
)
VALID_SEASONS = {"kharif", "rabi", "summer", "zaid", "whole_year"}
VALID_TIERS = {"A", "B", "C", "unassigned"}
VALID_DOMAINS = {"crop", "livestock", "fisheries"}


@dataclass(frozen=True, slots=True)
class CatalogRow:
    """One validated catalog entry."""

    crop_canonical: str
    name_en: str
    name_te: str
    name_hi: str
    aliases: tuple[str, ...]
    seasons: tuple[str, ...]
    apy_names: tuple[str, ...]
    crop_group: str
    domain: str
    yield_unit: str
    tier: str
    vision_supported: bool
    review_status: str


def _split(value: str) -> tuple[str, ...]:
    return tuple(v.strip() for v in value.split("|") if v.strip())


def normalize(text: str) -> str:
    """NFC-normalize, casefold and collapse whitespace (same rule as the backend)."""
    return " ".join(unicodedata.normalize("NFC", text).casefold().split())


def load_catalog(path: Path = CATALOG_PATH) -> list[CatalogRow]:
    """Load and validate the catalog. Raises ``ValueError`` listing every problem."""
    errors: list[str] = []
    rows: list[CatalogRow] = []
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        missing = [c for c in REQUIRED_COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"crop_catalog.csv missing columns: {missing}")
        seen: set[str] = set()
        for line_no, raw in enumerate(reader, start=2):
            key = raw["crop_canonical"].strip()
            if not key or key != key.lower() or " " in key:
                errors.append(f"line {line_no}: crop_canonical must be snake_case: {key!r}")
            if key in seen:
                errors.append(f"line {line_no}: duplicate crop_canonical {key!r}")
            seen.add(key)
            seasons = _split(raw["seasons"])
            if not seasons or set(seasons) - VALID_SEASONS:
                errors.append(f"line {line_no}: invalid seasons {seasons}")
            if raw["tier"] not in VALID_TIERS:
                errors.append(f"line {line_no}: invalid tier {raw['tier']!r}")
            if raw["domain"] not in VALID_DOMAINS:
                errors.append(f"line {line_no}: invalid domain {raw['domain']!r}")
            for col in ("name_en", "name_te", "name_hi", "yield_unit"):
                if not raw[col].strip():
                    errors.append(f"line {line_no}: empty {col}")
            rows.append(
                CatalogRow(
                    crop_canonical=key,
                    name_en=raw["name_en"].strip(),
                    name_te=raw["name_te"].strip(),
                    name_hi=raw["name_hi"].strip(),
                    aliases=_split(raw["aliases"]),
                    seasons=seasons,
                    apy_names=_split(raw["apy_names"]),
                    crop_group=raw["crop_group"].strip(),
                    domain=raw["domain"].strip(),
                    yield_unit=raw["yield_unit"].strip(),
                    tier=raw["tier"].strip(),
                    vision_supported=raw["vision_supported"].strip().lower() == "true",
                    review_status=raw["review_status"].strip(),
                )
            )
    if errors:
        raise ValueError("crop_catalog.csv invalid:\n" + "\n".join(errors))
    return rows


def ambiguous_aliases(rows: list[CatalogRow]) -> dict[str, list[str]]:
    """Return aliases shared by more than one crop (these must trigger a crop picker)."""
    index: dict[str, set[str]] = {}
    for row in rows:
        for name in (row.crop_canonical, row.name_en, row.name_te, row.name_hi, *row.aliases):
            index.setdefault(normalize(name), set()).add(row.crop_canonical)
    return {alias: sorted(crops) for alias, crops in index.items() if len(crops) > 1}
