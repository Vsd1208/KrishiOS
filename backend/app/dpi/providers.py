"""Digital Public Infrastructure adapters (F1, Phase 5).

Phase 0 found no public developer API for AgriStack (farmer registry), Bharat-VISTAAR or
Bhashini production access (orientation report §8). Each is therefore an interface with a
sandbox adapter that returns *no data* and says why, never fabricated records. Real adapters
plug in behind the same interface once access (and, for AgriStack, farmer consent) exists.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from app.providers import ProviderInfo, ProviderKind, ProviderSelector


@dataclass(frozen=True, slots=True)
class DpiResult:
    available: bool
    data: dict[str, Any] = field(default_factory=dict)
    reason: str | None = None
    provider: str = "sandbox"


class FarmerRegistry(Protocol):
    """AgriStack Farmer Registry: look up a farmer's ID and land records, with consent."""

    async def lookup(self, *, farmer_id: int, consent_token: str | None) -> DpiResult: ...


class AdvisoryNetwork(Protocol):
    """Bharat-VISTAAR: exchange advisories with the national network."""

    async def latest_advisories(self, *, lgd_district_code: int) -> DpiResult: ...


class LanguageService(Protocol):
    """Bhashini: translation / speech as a fallback to local models."""

    async def translate(self, *, text: str, source: str, target: str) -> DpiResult: ...


class SandboxFarmerRegistry:
    async def lookup(self, *, farmer_id: int, consent_token: str | None) -> DpiResult:
        if not consent_token:
            return DpiResult(False, reason="consent_required")
        return DpiResult(False, reason="agristack_access_not_granted")


class SandboxAdvisoryNetwork:
    async def latest_advisories(self, *, lgd_district_code: int) -> DpiResult:
        return DpiResult(False, reason="bharat_vistaar_api_not_available")


class SandboxLanguageService:
    async def translate(self, *, text: str, source: str, target: str) -> DpiResult:
        return DpiResult(False, reason="bhashini_access_not_granted")


registry_selector: ProviderSelector[FarmerRegistry] = ProviderSelector("dpi_farmer_registry")
advisory_selector: ProviderSelector[AdvisoryNetwork] = ProviderSelector("dpi_advisory_network")
language_selector: ProviderSelector[LanguageService] = ProviderSelector("dpi_language")

registry_selector.register(ProviderInfo(
    "dpi_farmer_registry", "sandbox", "1.0.0", ProviderKind.SANDBOX,
    description="AgriStack Farmer Registry: needs MoA&FW access + consent; returns no data."),
    SandboxFarmerRegistry)
advisory_selector.register(ProviderInfo(
    "dpi_advisory_network", "sandbox", "1.0.0", ProviderKind.SANDBOX,
    description="Bharat-VISTAAR: no public API found; returns no data."), SandboxAdvisoryNetwork)
language_selector.register(ProviderInfo(
    "dpi_language", "sandbox", "1.0.0", ProviderKind.SANDBOX,
    description="Bhashini: production access not granted; local IndicTrans2 is used instead."),
    SandboxLanguageService)


def _register_status() -> None:
    from app.providers.status import register_capability  # noqa: PLC0415

    register_capability("dpi_farmer_registry", lambda s: "sandbox", lambda: registry_selector)
    register_capability("dpi_advisory_network", lambda s: "sandbox", lambda: advisory_selector)
    register_capability("dpi_language", lambda s: "sandbox", lambda: language_selector)


_register_status()
