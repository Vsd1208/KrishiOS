"""Mock translation: tags the source text; never presented as a real translation."""

from __future__ import annotations


class MockTranslationProvider:
    provider_name = "mock-translation"
    model_version = "0.1.0"

    def supports(self, source_language: str, target_language: str) -> bool:
        return True

    async def translate(
        self, texts: list[str], source_language: str, target_language: str
    ) -> list[str]:
        return [f"[MOCK {source_language}->{target_language}] {t}" for t in texts]
