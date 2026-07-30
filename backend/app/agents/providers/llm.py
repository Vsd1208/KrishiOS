"""LLM Provider abstraction layer supporting multiple model backends."""

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from loguru import logger


@dataclass(frozen=True, slots=True)
class LLMResponse:
    """Standardized response container from any LLM provider."""

    content: str
    model_name: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    metadata: dict[str, Any] | None = None


@runtime_checkable
class LLMProvider(Protocol):
    """Protocol that all LLM providers (Gemini, OpenAI, Claude, Local) must implement."""

    @property
    def provider_name(self) -> str:
        """Return provider identifier (e.g. 'gemini', 'openai', 'claude', 'local')."""
        ...

    @property
    def model_name(self) -> str:
        """Return model identifier."""
        ...

    async def generate(
        self,
        prompt: str,
        system_instruction: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 1000,
    ) -> LLMResponse:
        """Generate text from a prompt."""
        ...

    async def count_tokens(self, text: str) -> int:
        """Estimate token count for prompt budgeting."""
        ...


class MockLocalLLMProvider:
    """Deterministic local LLM fallback provider for offline execution and testing.

    Ensures KrishiOS runs smoothly without requiring external API keys.
    """

    def __init__(self, model_name: str = "krishios-local-v1") -> None:
        self._model_name = model_name

    @property
    def provider_name(self) -> str:
        return "local"

    @property
    def model_name(self) -> str:
        return self._model_name

    async def generate(
        self,
        prompt: str,
        system_instruction: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 1000,
    ) -> LLMResponse:
        logger.debug("MockLocalLLMProvider: generating response for prompt length={}", len(prompt))
        tokens = len(prompt.split())
        content = (
            f"[Grounded Analysis] Processed query: '{prompt[:100]}...'\n"
            "Recommendation: Apply recommended agricultural practices based on verified RAG knowledge."
        )
        return LLMResponse(
            content=content,
            model_name=self._model_name,
            prompt_tokens=tokens,
            completion_tokens=len(content.split()),
            total_tokens=tokens + len(content.split()),
            metadata={"system": system_instruction},
        )

    async def count_tokens(self, text: str) -> int:
        return len(text.split())
