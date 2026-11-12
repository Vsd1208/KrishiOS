"""Translation cache keyed by content hash, language pair, provider and glossary version."""

from __future__ import annotations

import hashlib
from collections import OrderedDict
from dataclasses import dataclass


def content_hash(  # noqa: PLR0913 - keyword-only cache key parts
    text: str,
    *,
    source_language: str,
    target_language: str,
    provider: str,
    provider_version: str,
    glossary_version: str,
) -> str:
    """Stable SHA-256 over everything that can change a translation."""
    payload = "\x1f".join(
        [provider, provider_version, glossary_version, source_language, target_language, text]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class CachedTranslation:
    text: str
    provider: str
    provider_version: str


class TranslationCache:
    """In-process LRU. The persistent record (audit + approval) is ``TranslationRecord``."""

    def __init__(self, max_items: int = 5000) -> None:
        self._max = max_items
        self._items: OrderedDict[str, CachedTranslation] = OrderedDict()

    def get(self, key: str) -> CachedTranslation | None:
        item = self._items.get(key)
        if item is not None:
            self._items.move_to_end(key)
        return item

    def put(self, key: str, value: CachedTranslation) -> None:
        self._items[key] = value
        self._items.move_to_end(key)
        while len(self._items) > self._max:
            self._items.popitem(last=False)

    def __len__(self) -> int:
        return len(self._items)
