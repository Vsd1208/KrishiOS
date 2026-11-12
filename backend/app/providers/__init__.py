"""Config-driven provider selection shared by every pluggable capability (Sprint 11).

Rule (ADR-005): an unknown provider name is a configuration error, never a silent mock.
Every active provider is reported with its kind (live / sandbox / mock) so the API and UI
can show it, and with whether it sends user data off the device (DPDP disclosure).
"""

from app.providers.base import ProviderInfo, ProviderKind
from app.providers.selection import (
    ProviderConfigurationError,
    ProviderSelector,
)

__all__ = ["ProviderConfigurationError", "ProviderInfo", "ProviderKind", "ProviderSelector"]
