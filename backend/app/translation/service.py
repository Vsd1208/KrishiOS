"""Translation service: protect → translate → restore → check → policy.

Policy (brief §10a):

* Same language: passthrough.
* Each provider in the chain (primary, then fallback) is tried until one passes the checks.
  Off-device providers are skipped for personal data unless ALLOW_OFF_DEVICE_PROVIDERS.
* No passing output: status ``blocked`` (not deliverable). The best attempt is kept for an
  officer to edit.
* Severity HIGH/CRITICAL: status ``pending_review`` (deliverable only after officer approval
  of the translated text). Lower severity with passing checks: ``auto_approved``.
"""

from __future__ import annotations

import re
import time
from dataclasses import asdict, dataclass, field
from enum import StrEnum

from loguru import logger

from app.config.settings import get_settings
from app.providers import ProviderConfigurationError
from app.translation.cache import CachedTranslation, TranslationCache, content_hash
from app.translation.checks import CheckResult, check_translation
from app.translation.glossary import get_glossary
from app.translation.protect import Protector
from app.translation.providers.base import TranslationError, TranslationProvider
from app.translation.selection import translation_selector

REVIEW_SEVERITIES = {"HIGH", "CRITICAL"}
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?।])\s+")


class TranslationStatus(StrEnum):
    PASSTHROUGH = "passthrough"
    AUTO_APPROVED = "auto_approved"
    PENDING_REVIEW = "pending_review"
    BLOCKED = "blocked"


@dataclass(slots=True)
class Attempt:
    provider: str
    provider_version: str | None
    outcome: str  # passed | failed_checks | error | skipped
    detail: str = ""
    latency_ms: float | None = None


@dataclass(slots=True)
class TranslationOutcome:
    source_text: str
    source_language: str
    target_language: str
    text: str
    status: TranslationStatus
    deliverable: bool
    checks: CheckResult
    provider: str | None
    provider_version: str | None
    glossary_version: str
    content_hash: str | None
    cached: bool = False
    protected_spans: int = 0
    attempts: list[Attempt] = field(default_factory=list)
    back_translation: str | None = None

    def to_dict(self) -> dict:
        data = asdict(self)
        data["status"] = self.status.value
        return data


class TranslationService:
    """Stateless apart from the in-process cache; safe to share."""

    def __init__(
        self, cache: TranslationCache | None = None, protector: Protector | None = None
    ) -> None:
        self._cache = cache or TranslationCache()
        self._protector = protector or Protector()
        self._glossary = get_glossary()

    def _chain(self) -> list[str]:
        s = get_settings()
        chain = [s.TRANSLATION_PROVIDER]
        if s.TRANSLATION_FALLBACK_PROVIDER and s.TRANSLATION_FALLBACK_PROVIDER not in chain:
            chain.append(s.TRANSLATION_FALLBACK_PROVIDER)
        return chain

    async def _run_provider(
        self, provider: TranslationProvider, masked_text: str, src: str, tgt: str
    ) -> str:
        segments = [seg for seg in _SENTENCE_SPLIT.split(masked_text) if seg.strip()]
        outs = await provider.translate(segments or [masked_text], src, tgt)
        return " ".join(o.strip() for o in outs)

    async def translate(  # noqa: PLR0913 - options are keyword-only
        self,
        text: str,
        source_language: str,
        target_language: str,
        *,
        severity: str | None = None,
        personal_data: bool = True,
        back_translate: bool = False,
    ) -> TranslationOutcome:
        settings = get_settings()
        if source_language == target_language:
            return TranslationOutcome(
                text,
                source_language,
                target_language,
                text,
                TranslationStatus.PASSTHROUGH,
                True,
                check_translation(text, text),
                None,
                None,
                self._glossary.version,
                None,
            )

        masked = self._protector.mask(text, source_language, target_language)
        attempts: list[Attempt] = []
        best: tuple[str, CheckResult, str, str] | None = None

        for name in self._chain():
            try:
                info = translation_selector.info(name)
                provider = translation_selector.get(name)
            except (ProviderConfigurationError, TranslationError) as exc:
                attempts.append(Attempt(name, None, "error", str(exc)))
                continue
            if (
                info.sends_data_off_device
                and personal_data
                and not settings.ALLOW_OFF_DEVICE_PROVIDERS
            ):
                attempts.append(
                    Attempt(
                        name,
                        info.version,
                        "skipped",
                        "off-device provider not allowed for personal data",
                    )
                )
                continue
            if not provider.supports(source_language, target_language):
                attempts.append(Attempt(name, info.version, "skipped", "unsupported pair"))
                continue

            key = content_hash(
                text,
                source_language=source_language,
                target_language=target_language,
                provider=name,
                provider_version=provider.model_version,
                glossary_version=self._glossary.version,
            )
            cached = self._cache.get(key)
            t0 = time.perf_counter()
            if cached is not None:
                translated = cached.text
            else:
                try:
                    raw = await self._run_provider(
                        provider, masked.text, source_language, target_language
                    )
                except TranslationError as exc:
                    attempts.append(Attempt(name, info.version, "error", str(exc)))
                    continue
                translated, _missing = Protector.restore(raw, masked.spans)
            latency = round((time.perf_counter() - t0) * 1000, 1)
            checks = check_translation(text, translated, self._glossary)
            if checks.passed:
                self._cache.put(key, CachedTranslation(translated, name, provider.model_version))
                attempts.append(Attempt(name, provider.model_version, "passed", "", latency))
                review = (severity or "").upper() in REVIEW_SEVERITIES
                outcome = TranslationOutcome(
                    text,
                    source_language,
                    target_language,
                    translated,
                    TranslationStatus.PENDING_REVIEW if review else TranslationStatus.AUTO_APPROVED,
                    deliverable=not review,
                    checks=checks,
                    provider=name,
                    provider_version=provider.model_version,
                    glossary_version=self._glossary.version,
                    content_hash=key,
                    cached=cached is not None,
                    protected_spans=len(masked.spans),
                    attempts=attempts,
                )
                if back_translate:
                    outcome.back_translation = await self._back_translate(
                        translated, target_language, source_language, personal_data
                    )
                return outcome
            attempts.append(
                Attempt(
                    name,
                    provider.model_version,
                    "failed_checks",
                    "; ".join(checks.reasons),
                    latency,
                )
            )
            if best is None:
                best = (translated, checks, name, provider.model_version)

        logger.warning(
            "Translation blocked | {}->{} | attempts={}",
            source_language,
            target_language,
            [(a.provider, a.outcome) for a in attempts],
        )
        text_out, checks, prov, ver = best or ("", check_translation(text, ""), None, None)
        return TranslationOutcome(
            text,
            source_language,
            target_language,
            text_out,
            TranslationStatus.BLOCKED,
            deliverable=False,
            checks=checks,
            provider=prov,
            provider_version=ver,
            glossary_version=self._glossary.version,
            content_hash=None,
            protected_spans=len(masked.spans),
            attempts=attempts,
        )

    async def _back_translate(
        self, text: str, src: str, tgt: str, personal_data: bool
    ) -> str | None:
        result = await self.translate(text, src, tgt, personal_data=personal_data)
        return result.text if result.status is not TranslationStatus.BLOCKED else None


_service: TranslationService | None = None


def get_translation_service() -> TranslationService:
    global _service  # noqa: PLW0603 - process-wide singleton
    if _service is None:
        _service = TranslationService()
    return _service
