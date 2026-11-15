"""Agri glossary: protected terms and multilingual unit spellings."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

GLOSSARY_PATH = Path(__file__).with_name("agri_glossary.yaml")


@dataclass(frozen=True, slots=True)
class Glossary:
    version: str
    protected_terms: tuple[str, ...]
    units: dict[str, tuple[str, ...]]

    def unit_lookup(self) -> dict[str, str]:
        """spelling (casefolded) -> canonical unit."""
        out: dict[str, str] = {}
        for canonical, spellings in self.units.items():
            for s in spellings:
                out[str(s).casefold()] = canonical
        return out


def load_glossary(path: Path = GLOSSARY_PATH) -> Glossary:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return Glossary(
        version=str(data["version"]),
        protected_terms=tuple(str(t) for t in data["protected_terms"]),
        units={k: tuple(str(s) for s in v) for k, v in data["units"].items()},
    )


@lru_cache(maxsize=1)
def get_glossary() -> Glossary:
    return load_glossary()
