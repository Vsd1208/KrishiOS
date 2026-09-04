"""LLM provider abstraction and Gemini implementation for KrishiOS."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from google import genai
from google.genai import types
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
    """Protocol implemented by all KrishiOS LLM providers."""

    @property
    def provider_name(self) -> str:
        """Return the provider identifier."""
        ...

    @property
    def model_name(self) -> str:
        """Return the model identifier."""
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
        """Count or estimate tokens for prompt budgeting."""
        ...


class GeminiLLMProvider:
    """Production LLM provider backed by the Google Gemini API."""

    def __init__(
        self,
        api_key: str,
        model_name: str = "gemini-3.6-flash",
        timeout_seconds: float = 30.0,
    ) -> None:
        if not api_key or not api_key.strip():
            raise ValueError("GEMINI_API_KEY is required when LLM_PROVIDER=gemini")

        if not model_name.strip():
            raise ValueError("LLM_MODEL must not be empty")

        self._model_name = model_name
        self._timeout_seconds = timeout_seconds

        self._client = genai.Client(
            api_key=api_key.strip(),
            http_options=types.HttpOptions(
                timeout=int(timeout_seconds * 1000),
            ),
        )

        logger.info(
            "GeminiLLMProvider initialized | model={} | timeout_seconds={}",
            self._model_name,
            self._timeout_seconds,
        )

    @property
    def provider_name(self) -> str:
        return "gemini"

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
        """Generate a response asynchronously using Gemini."""

        if not prompt.strip():
            raise ValueError("LLM prompt must not be empty")

        if max_tokens <= 0:
            raise ValueError("max_tokens must be greater than zero")

        logger.info(
            "GeminiLLMProvider: generating response | model={} | prompt_chars={}",
            self._model_name,
            len(prompt),
        )

        try:
            config = types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
                system_instruction=system_instruction,
            )

            response = await self._client.aio.models.generate_content(
                model=self._model_name,
                contents=prompt,
                config=config,
            )

            content = (response.text or "").strip()

            if not content:
                raise RuntimeError(
                    "Gemini returned an empty response. "
                    "The model may have blocked or failed to generate the content."
                )

            usage = getattr(response, "usage_metadata", None)

            prompt_tokens = int(
                getattr(usage, "prompt_token_count", 0) or 0
            )
            completion_tokens = int(
                getattr(usage, "candidates_token_count", 0) or 0
            )
            total_tokens = int(
                getattr(usage, "total_token_count", 0) or 0
            )

            metadata: dict[str, Any] = {
                "provider": self.provider_name,
                "model": self.model_name,
                "finish_reason": self._extract_finish_reason(response),
            }

            logger.info(
                "GeminiLLMProvider: response generated | model={} | "
                "prompt_tokens={} | completion_tokens={} | total_tokens={}",
                self._model_name,
                prompt_tokens,
                completion_tokens,
                total_tokens,
            )

            return LLMResponse(
                content=content,
                model_name=self._model_name,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                metadata=metadata,
            )

        except Exception:
            logger.exception(
                "GeminiLLMProvider: generation failed | model={}",
                self._model_name,
            )
            raise

    async def count_tokens(self, text: str) -> int:
        """Return Gemini's token count for the supplied text."""

        if not text.strip():
            return 0

        try:
            response = await self._client.aio.models.count_tokens(
                model=self._model_name,
                contents=text,
            )

            return int(getattr(response, "total_tokens", 0) or 0)

        except Exception:
            logger.exception(
                "GeminiLLMProvider: token counting failed | model={}",
                self._model_name,
            )

            # Token counting is auxiliary. Fall back to a conservative
            # word-based estimate rather than failing an otherwise valid request.
            return len(text.split())

    @staticmethod
    def _extract_finish_reason(response: Any) -> str | None:
        """Extract the candidate finish reason without coupling to SDK internals."""

        try:
            candidates = getattr(response, "candidates", None)

            if not candidates:
                return None

            reason = getattr(candidates[0], "finish_reason", None)

            if reason is None:
                return None

            return str(reason)

        except Exception:
            return None


class MockLocalLLMProvider:
    """Deterministic local LLM fallback provider for offline execution and tests."""

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
        logger.debug(
            "MockLocalLLMProvider: generating response | prompt_length={}",
            len(prompt),
        )

        tokens = len(prompt.split())

        content = (
            f"[Grounded Analysis] Processed query: '{prompt[:100]}...'\n"
            "Recommendation: Apply recommended agricultural practices based on "
            "verified RAG knowledge."
        )

        completion_tokens = len(content.split())

        return LLMResponse(
            content=content,
            model_name=self._model_name,
            prompt_tokens=tokens,
            completion_tokens=completion_tokens,
            total_tokens=tokens + completion_tokens,
            metadata={
                "provider": self.provider_name,
                "model": self.model_name,
                "system": system_instruction,
            },
        )

    async def count_tokens(self, text: str) -> int:
        return len(text.split())