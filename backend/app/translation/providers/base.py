"""Translation provider protocol."""

from __future__ import annotations

from typing import Protocol

# ISO 639-1 codes used across KrishiOS.
LANGUAGE_NAMES = {"en": "English", "hi": "Hindi", "te": "Telugu"}


class TranslationError(RuntimeError):
    """Raised when a provider cannot translate (missing model, network, unsupported pair)."""


class TranslationProvider(Protocol):
    """Batch translation between ISO 639-1 language codes."""

    @property
    def provider_name(self) -> str: ...

    @property
    def model_version(self) -> str: ...

    def supports(self, source_language: str, target_language: str) -> bool: ...

    async def translate(
        self, texts: list[str], source_language: str, target_language: str
    ) -> list[str]: ...
