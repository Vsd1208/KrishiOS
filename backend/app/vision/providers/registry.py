"""Registry for managing and resolving vision model providers."""

from loguru import logger
from app.vision.providers.base import VisionModelProvider


class ModelRegistry:
    """Central registry for vision model providers."""

    def __init__(self) -> None:
        self._providers: dict[str, VisionModelProvider] = {}

    def register(self, provider: VisionModelProvider) -> None:
        """Register a new vision model provider."""
        if provider.model_name in self._providers:
            logger.warning("ModelRegistry: Overwriting existing provider for '{}'", provider.model_name)
            
        self._providers[provider.model_name] = provider
        logger.info("ModelRegistry: Registered provider '{}' (v{})", provider.model_name, provider.model_version)

    def get(self, model_name: str) -> VisionModelProvider | None:
        """Retrieve a provider by name."""
        return self._providers.get(model_name)

    def list_models(self) -> list[dict[str, str]]:
        """List all registered models and their versions."""
        return [
            {"name": p.model_name, "version": p.model_version}
            for p in self._providers.values()
        ]

# Global singleton registry instance
vision_model_registry = ModelRegistry()
