"""Provider transparency endpoint (Sprint 11)."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.providers.status import active_providers, check_provider_policy

router = APIRouter(prefix="/providers", tags=["Providers"])


class ProviderStatusOut(BaseModel):
    """Active provider for one capability, as shown in the UI badges."""

    capability: str
    configured: str | None
    name: str | None
    version: str | None
    kind: str | None
    sends_data_off_device: bool | None
    description: str | None
    error: str | None


class ProvidersResponse(BaseModel):
    providers: list[ProviderStatusOut]
    policy_violations: list[str]


@router.get("", response_model=ProvidersResponse)
async def list_active_providers() -> ProvidersResponse:
    """List the active provider (live / sandbox / mock) for every capability."""
    items = [
        ProviderStatusOut(
            capability=ap.capability,
            configured=ap.configured,
            name=ap.info.name if ap.info else None,
            version=ap.info.version if ap.info else None,
            kind=ap.info.kind.value if ap.info else None,
            sends_data_off_device=ap.info.sends_data_off_device if ap.info else None,
            description=ap.info.description if ap.info else None,
            error=ap.error,
        )
        for ap in active_providers()
    ]
    return ProvidersResponse(providers=items, policy_violations=check_provider_policy())
