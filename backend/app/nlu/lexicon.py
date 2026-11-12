"""Loader for ``lexicon.yaml``."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

from app.catalog.phrases import PhraseMatcher

LEXICON_PATH = Path(__file__).with_name("lexicon.yaml")


@dataclass(frozen=True, slots=True)
class Lexicon:
    version: str
    priorities: dict[str, int]
    intents: PhraseMatcher
    seasons: PhraseMatcher
    symptoms: PhraseMatcher
    schemes: PhraseMatcher
    times: PhraseMatcher
    romanized_markers: dict[str, frozenset[str]]


def _pairs(groups: dict[str, list[str]]) -> list[tuple[str, str]]:
    return [(label, str(p)) for label, phrases in groups.items() for p in (phrases or [])]


def load_lexicon(path: Path = LEXICON_PATH) -> Lexicon:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    intent_pairs: list[tuple[str, str]] = []
    priorities: dict[str, int] = {}
    for intent, spec in data["intents"].items():
        priorities[intent] = int(spec["priority"])
        for phrases in spec["phrases"].values():
            intent_pairs.extend((intent, str(p)) for p in (phrases or []))
    return Lexicon(
        version=str(data["version"]),
        priorities=priorities,
        intents=PhraseMatcher(intent_pairs),
        seasons=PhraseMatcher(_pairs(data["seasons"])),
        symptoms=PhraseMatcher(_pairs(data["symptoms"])),
        schemes=PhraseMatcher(_pairs(data["schemes"])),
        times=PhraseMatcher(_pairs(data["time_expressions"])),
        romanized_markers={k: frozenset(v) for k, v in data["romanized_markers"].items()},
    )


@lru_cache(maxsize=1)
def get_lexicon() -> Lexicon:
    return load_lexicon()
