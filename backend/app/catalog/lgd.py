"""LGD (Local Government Directory) district and block lookup.

Backed by ``ml/reference/lgd_districts.csv`` and ``lgd_blocks.csv`` (GODL-India snapshot).
Used to key bulletins, forecasts and targeting by LGD code instead of free-text names.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from loguru import logger

from app.catalog.paths import reference_dir
from app.catalog.text import normalize

# Common spelling variants seen in government feeds vs. LGD names.
_STATE_ALIASES = {
    "orissa": "odisha",
    "pondicherry": "puducherry",
    "jammu & kashmir": "jammu and kashmir",
    "j&k": "jammu and kashmir",
}


@dataclass(frozen=True, slots=True)
class LGDDistrict:
    lgd_district_code: int
    district_name: str
    lgd_state_code: int
    state_name: str
    census_2011_code: int | None


@dataclass(frozen=True, slots=True)
class LGDBlock:
    lgd_block_code: int
    block_name: str
    lgd_district_code: int
    lgd_state_code: int


def _norm_state(name: str) -> str:
    n = normalize(name.replace("&", " and "))
    return _STATE_ALIASES.get(n, n)


class LGDDirectory:
    """In-memory LGD lookup by code or (state, district) name."""

    def __init__(self, districts: list[LGDDistrict], blocks: list[LGDBlock]) -> None:
        self._by_code = {d.lgd_district_code: d for d in districts}
        self._by_name: dict[str, list[LGDDistrict]] = {}
        for d in districts:
            self._by_name.setdefault(normalize(d.district_name), []).append(d)
        self._blocks_by_district: dict[int, list[LGDBlock]] = {}
        self._blocks = {b.lgd_block_code: b for b in blocks}
        for b in blocks:
            self._blocks_by_district.setdefault(b.lgd_district_code, []).append(b)

    def __len__(self) -> int:
        return len(self._by_code)

    def districts(self) -> list[LGDDistrict]:
        return list(self._by_code.values())

    def district(self, lgd_code: int) -> LGDDistrict | None:
        return self._by_code.get(lgd_code)

    def block(self, lgd_block_code: int) -> LGDBlock | None:
        return self._blocks.get(lgd_block_code)

    def blocks_of(self, lgd_district_code: int) -> list[LGDBlock]:
        return list(self._blocks_by_district.get(lgd_district_code, []))

    def find_districts(self, name: str, state: str | None = None) -> list[LGDDistrict]:
        """All districts with this name (optionally within a state). Names can repeat
        across states (e.g. 'Aurangabad' in Bihar and Maharashtra)."""
        matches = self._by_name.get(normalize(name), [])
        if state:
            wanted = _norm_state(state)
            matches = [d for d in matches if _norm_state(d.state_name) == wanted]
        return list(matches)

    def resolve_district(self, name: str, state: str | None = None) -> LGDDistrict | None:
        """Unique district for a name (+state); ``None`` if absent or ambiguous."""
        matches = self.find_districts(name, state)
        return matches[0] if len(matches) == 1 else None


def _int_or_none(value: str) -> int | None:
    value = (value or "").strip()
    return int(value) if value.isdigit() else None


def load_lgd_directory(directory: Path) -> LGDDirectory:
    with (directory / "lgd_districts.csv").open(encoding="utf-8", newline="") as fh:
        districts = [
            LGDDistrict(
                lgd_district_code=int(r["lgd_district_code"]),
                district_name=r["district_name"].strip(),
                lgd_state_code=int(r["lgd_state_code"]),
                state_name=r["state_name"].strip(),
                census_2011_code=_int_or_none(r["census_2011_code"]),
            )
            for r in csv.DictReader(fh)
        ]
    blocks: list[LGDBlock] = []
    blocks_path = directory / "lgd_blocks.csv"
    if blocks_path.exists():
        with blocks_path.open(encoding="utf-8", newline="") as fh:
            blocks = [
                LGDBlock(
                    lgd_block_code=int(r["lgd_block_code"]),
                    block_name=r["block_name"].strip(),
                    lgd_district_code=int(r["lgd_district_code"]),
                    lgd_state_code=int(r["lgd_state_code"]),
                )
                for r in csv.DictReader(fh)
            ]
    logger.info("LGD directory loaded | districts={} | blocks={}", len(districts), len(blocks))
    return LGDDirectory(districts, blocks)


@lru_cache(maxsize=1)
def get_lgd_directory() -> LGDDirectory:
    return load_lgd_directory(reference_dir())
