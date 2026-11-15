"""Translation policy: provider chain, blocking, review, off-device rules."""

import pytest
from app.config.settings import get_settings
from app.providers import ProviderInfo, ProviderKind
from app.translation.selection import translation_selector
from app.translation.service import TranslationService, TranslationStatus


class EchoPlaceholders:
    """Fake MT that keeps placeholders and adds Telugu words around them."""

    provider_name = "fake-good"
    model_version = "1"

    def supports(self, s, t):
        return True

    async def translate(self, texts, s, t):
        return [f"అనువాదం {x}" for x in texts]


class CorruptsNumbers:
    """Fake MT that drops placeholders (simulates a bad model)."""

    provider_name = "fake-bad"
    model_version = "1"

    def supports(self, s, t):
        return True

    async def translate(self, texts, s, t):
        return ["అనువాదం 99" for _ in texts]


class OffDevice(EchoPlaceholders):
    provider_name = "fake-cloud"


translation_selector.register(ProviderInfo("translation", "fake-good", "1", ProviderKind.LIVE),
                              EchoPlaceholders)
translation_selector.register(ProviderInfo("translation", "fake-bad", "1", ProviderKind.LIVE),
                              CorruptsNumbers)
translation_selector.register(
    ProviderInfo("translation", "fake-cloud", "1", ProviderKind.LIVE, sends_data_off_device=True),
    OffDevice,
)


@pytest.fixture
def configure(monkeypatch):
    def _set(**kw):
        settings = get_settings()
        for k, v in kw.items():
            monkeypatch.setattr(settings, k, v)
    return _set


SRC = "Spray Tricyclazole 75% WP at 0.6 g/L for blast in paddy."


async def test_passing_translation_is_auto_approved(configure) -> None:
    configure(TRANSLATION_PROVIDER="fake-good", TRANSLATION_FALLBACK_PROVIDER=None)
    out = await TranslationService().translate(SRC, "en", "te", severity="LOW")
    assert out.status is TranslationStatus.AUTO_APPROVED and out.deliverable
    assert "0.6 g/L" in out.text and "Tricyclazole" in out.text and "వరి" in out.text
    assert out.provider == "fake-good"


async def test_high_severity_requires_review(configure) -> None:
    configure(TRANSLATION_PROVIDER="fake-good", TRANSLATION_FALLBACK_PROVIDER=None)
    out = await TranslationService().translate(SRC, "en", "hi", severity="CRITICAL")
    assert out.status is TranslationStatus.PENDING_REVIEW
    assert not out.deliverable


async def test_failed_checks_fall_back_then_block(configure) -> None:
    configure(TRANSLATION_PROVIDER="fake-bad", TRANSLATION_FALLBACK_PROVIDER="fake-good")
    out = await TranslationService().translate(SRC, "en", "te")
    assert out.provider == "fake-good"
    assert [a.outcome for a in out.attempts] == ["failed_checks", "passed"]

    configure(TRANSLATION_PROVIDER="fake-bad", TRANSLATION_FALLBACK_PROVIDER=None)
    blocked = await TranslationService().translate(SRC, "en", "te")
    assert blocked.status is TranslationStatus.BLOCKED and not blocked.deliverable
    assert "0.6" in blocked.checks.missing_numbers


async def test_off_device_skipped_for_personal_data(configure) -> None:
    configure(TRANSLATION_PROVIDER="fake-cloud", TRANSLATION_FALLBACK_PROVIDER="fake-good",
              ALLOW_OFF_DEVICE_PROVIDERS=False)
    out = await TranslationService().translate(SRC, "en", "te", personal_data=True)
    assert out.provider == "fake-good"
    assert out.attempts[0].outcome == "skipped"
    # Public government text may use the off-device provider.
    public = await TranslationService().translate(SRC, "en", "te", personal_data=False)
    assert public.provider == "fake-cloud"


async def test_same_language_passthrough() -> None:
    out = await TranslationService().translate("hello", "en", "en")
    assert out.status is TranslationStatus.PASSTHROUGH and out.text == "hello"


async def test_cache_hit(configure) -> None:
    configure(TRANSLATION_PROVIDER="fake-good", TRANSLATION_FALLBACK_PROVIDER=None)
    svc = TranslationService()
    first = await svc.translate(SRC, "en", "te")
    second = await svc.translate(SRC, "en", "te")
    assert not first.cached and second.cached and second.text == first.text


async def test_unknown_provider_is_reported_not_silently_mocked(configure) -> None:
    configure(TRANSLATION_PROVIDER="nope", TRANSLATION_FALLBACK_PROVIDER=None)
    out = await TranslationService().translate(SRC, "en", "te")
    assert out.status is TranslationStatus.BLOCKED
    assert out.attempts[0].outcome == "error"
