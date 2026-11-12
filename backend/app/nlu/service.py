"""NLU service: primary provider with deterministic fallback."""

from __future__ import annotations

from loguru import logger

from app.config.settings import get_settings
from app.nlu.providers.rule_based import RuleBasedNLUProvider
from app.nlu.selection import nlu_selector
from app.nlu.types import NLUResult
from app.providers import ProviderConfigurationError

_rules = RuleBasedNLUProvider()


async def parse(text: str, language_hint: str | None = None,
                personal_data: bool = True) -> NLUResult:
    """Parse with ``NLU_PROVIDER``. Off-device providers are skipped for personal data unless
    allowed. Any provider error falls back to ``NLU_FALLBACK_PROVIDER`` and then to rules."""
    settings = get_settings()
    chain = [settings.NLU_PROVIDER]
    if settings.NLU_FALLBACK_PROVIDER and settings.NLU_FALLBACK_PROVIDER not in chain:
        chain.append(settings.NLU_FALLBACK_PROVIDER)
    for name in chain:
        try:
            info = nlu_selector.info(name)
            if info.sends_data_off_device and personal_data and \
                    not settings.ALLOW_OFF_DEVICE_PROVIDERS:
                logger.info("NLU provider {} skipped (off-device not allowed)", name)
                continue
            return await nlu_selector.get(name).parse(text, language_hint)
        except ProviderConfigurationError:
            raise
        except Exception as exc:  # provider/network failure -> next in chain
            logger.warning("NLU provider {} failed: {}", name, type(exc).__name__)
    return _rules.parse_sync(text, language_hint)


def parse_sync(text: str, language_hint: str | None = None) -> NLUResult:
    """Deterministic parse for synchronous callers (the planner)."""
    return _rules.parse_sync(text, language_hint)
