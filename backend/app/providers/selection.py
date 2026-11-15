"""Generic, fail-loud provider selector."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

from loguru import logger

from app.providers.base import ProviderInfo


class ProviderConfigurationError(RuntimeError):
    """Raised when configuration names a provider that is not registered or not allowed."""


class ProviderSelector[T]:
    """Registry of named provider factories for one capability.

    Instances are created lazily and cached, so importing a module never loads a model.
    """

    def __init__(self, capability: str) -> None:
        self.capability = capability
        self._factories: dict[str, Callable[[], T]] = {}
        self._infos: dict[str, ProviderInfo] = {}
        self._instances: dict[str, T] = {}

    def register(self, info: ProviderInfo, factory: Callable[[], T]) -> None:
        """Register a provider factory under ``info.name``."""
        if info.capability != self.capability:
            info = replace(info, capability=self.capability)
        self._factories[info.name] = factory
        self._infos[info.name] = info

    def names(self) -> list[str]:
        return sorted(self._factories)

    def info(self, name: str) -> ProviderInfo:
        self._check(name)
        return self._infos[name]

    def get(self, name: str) -> T:
        """Return the (cached) provider instance, raising on unknown names."""
        self._check(name)
        if name not in self._instances:
            self._instances[name] = self._factories[name]()
            info = self._infos[name]
            logger.info(
                "Provider selected | capability={} | name={} | version={} | kind={}",
                self.capability, info.name, info.version, info.kind,
            )
        return self._instances[name]

    def reset(self) -> None:
        """Drop cached instances (tests, config reloads)."""
        self._instances.clear()

    def _check(self, name: str) -> None:
        if name not in self._factories:
            raise ProviderConfigurationError(
                f"Unknown {self.capability} provider {name!r}. "
                f"Registered: {', '.join(self.names()) or '(none)'}"
            )
