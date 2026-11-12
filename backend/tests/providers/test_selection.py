"""Fail-loud provider selection and status reporting (ADR-005)."""

import pytest
from app.config.settings import get_settings
from app.live_data.providers.registry import LiveDataProviderRegistry, market_selector
from app.providers import ProviderConfigurationError, ProviderInfo, ProviderKind, ProviderSelector
from app.providers.status import active_providers, check_provider_policy


def test_unknown_provider_raises() -> None:
    sel: ProviderSelector[object] = ProviderSelector("demo")
    sel.register(ProviderInfo("demo", "a", "1", ProviderKind.MOCK), object)
    with pytest.raises(ProviderConfigurationError, match="Registered: a"):
        sel.get("missing")


def test_instances_are_lazy_and_cached() -> None:
    calls = []
    sel: ProviderSelector[object] = ProviderSelector("demo")
    sel.register(
        ProviderInfo("demo", "a", "1", ProviderKind.LIVE), lambda: calls.append(1) or object()
    )
    assert calls == []
    assert sel.get("a") is sel.get("a")
    assert calls == [1]


def test_live_data_registry_no_longer_falls_back() -> None:
    with pytest.raises(ProviderConfigurationError):
        LiveDataProviderRegistry().get_weather_provider("does-not-exist")


def test_agmarknet_is_reported_as_mock() -> None:
    assert market_selector.info("agmarknet-v1").kind is ProviderKind.MOCK


def test_active_providers_lists_every_capability() -> None:
    caps = {ap.capability for ap in active_providers()}
    assert {"llm", "vision", "stt", "tts", "weather", "market", "advisory", "scheme"} <= caps
    vision = next(ap for ap in active_providers() if ap.capability == "vision")
    assert vision.info is not None and vision.info.kind is ProviderKind.MOCK


def test_policy_flags_mocks_when_disallowed() -> None:
    settings = get_settings().model_copy(update={"ALLOW_MOCK_PROVIDERS": False})
    problems = check_provider_policy(settings)
    assert any("vision: mock provider" in p for p in problems)


def test_policy_flags_unknown_names() -> None:
    settings = get_settings().model_copy(update={"VISION_PROVIDER": "nope"})
    problems = check_provider_policy(settings)
    assert any(p.startswith("vision: Unknown vision provider") for p in problems)


def test_providers_endpoint(client) -> None:
    body = client.get("/api/v1/providers").json()
    by_cap = {p["capability"]: p for p in body["providers"]}
    assert by_cap["stt"]["kind"] == "mock"
    assert by_cap["notification:in_app"]["kind"] == "sandbox"
    assert isinstance(body["policy_violations"], list)
