"""Provider metadata contracts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ProviderKind(StrEnum):
    """How real a provider is. Never present SANDBOX or MOCK as LIVE."""

    LIVE = "live"
    SANDBOX = "sandbox"
    MOCK = "mock"


@dataclass(frozen=True, slots=True)
class ProviderInfo:
    """Public description of a provider implementation."""

    capability: str
    name: str
    version: str
    kind: ProviderKind
    sends_data_off_device: bool = False
    description: str = ""

    @property
    def is_mock(self) -> bool:
        return self.kind is ProviderKind.MOCK
