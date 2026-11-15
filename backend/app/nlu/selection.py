"""Config-driven NLU provider selection."""

from __future__ import annotations

from typing import Protocol

from app.config.settings import get_settings
from app.nlu.providers.rule_based import RuleBasedNLUProvider
from app.nlu.types import NLUResult
from app.providers import ProviderInfo, ProviderKind, ProviderSelector
from app.providers.status import register_capability


class NLUProvider(Protocol):
    provider_name: str
    model_version: str

    async def parse(self, text: str, language_hint: str | None = None) -> NLUResult: ...


nlu_selector: ProviderSelector[NLUProvider] = ProviderSelector("nlu")


def _gemini() -> NLUProvider:
    from app.nlu.providers.gemini_nlu import GeminiNLUProvider  # noqa: PLC0415

    s = get_settings()
    return GeminiNLUProvider(s.GEMINI_API_KEY, s.LLM_MODEL)


nlu_selector.register(
    ProviderInfo("nlu", "rule-based-nlu", RuleBasedNLUProvider().model_version, ProviderKind.LIVE,
                 description="Deterministic multilingual lexicon + catalog/LGD resolution."),
    RuleBasedNLUProvider,
)
nlu_selector.register(
    ProviderInfo("nlu", "gemini-nlu", get_settings().LLM_MODEL, ProviderKind.LIVE,
                 sends_data_off_device=True,
                 description="Gemini structured output; entities re-validated locally."),
    _gemini,
)

register_capability("nlu", lambda s: s.NLU_PROVIDER, lambda: nlu_selector)
