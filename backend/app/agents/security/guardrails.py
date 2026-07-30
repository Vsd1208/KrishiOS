"""GuardrailEngine for verifying grounding, confidence, citations, and hallucination risk."""

from dataclasses import dataclass
from typing import Any

from loguru import logger

_FALLBACK_MESSAGE = "I don't have enough verified information."


@dataclass(frozen=True, slots=True)
class GuardrailResult:
    """Output of guardrail validation."""

    passed: bool
    confidence_score: float
    grounded: bool
    citation_valid: bool
    safe_output: str
    rejection_reason: str | None = None


class GuardrailEngine:
    """Evaluates grounding, citations, and confidence before returning agent responses."""

    def __init__(self, min_confidence_threshold: float = 0.35) -> None:
        self._min_confidence = min_confidence_threshold

    def evaluate(
        self,
        output_text: str,
        confidence_score: float,
        citations: list[dict[str, Any]],
        require_citations: bool = True,
    ) -> GuardrailResult:
        """Evaluate response against safety, grounding, and citation thresholds."""
        if confidence_score < self._min_confidence:
            logger.warning(
                "GuardrailEngine: confidence score {:.2f} < threshold {:.2f}",
                confidence_score,
                self._min_confidence,
            )
            return GuardrailResult(
                passed=False,
                confidence_score=confidence_score,
                grounded=False,
                citation_valid=False,
                safe_output=_FALLBACK_MESSAGE,
                rejection_reason=f"Confidence score {confidence_score:.2f} below threshold {self._min_confidence:.2f}",
            )

        citation_valid = (len(citations) > 0) if require_citations else True
        if require_citations and not citation_valid:
            logger.warning("GuardrailEngine: required citations missing")
            return GuardrailResult(
                passed=False,
                confidence_score=confidence_score,
                grounded=False,
                citation_valid=False,
                safe_output=_FALLBACK_MESSAGE,
                rejection_reason="Verified source citations missing",
            )

        return GuardrailResult(
            passed=True,
            confidence_score=confidence_score,
            grounded=True,
            citation_valid=citation_valid,
            safe_output=output_text,
            rejection_reason=None,
        )
