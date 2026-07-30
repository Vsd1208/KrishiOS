"""Evaluation utilities for agent output quality assessment."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.agents.execution.context import ExecutionResult


@dataclass(frozen=True, slots=True)
class EvaluationScore:
    """Individual evaluation dimension score."""

    dimension: str
    score: float
    passed: bool
    details: str = ""


@dataclass(slots=True)
class EvaluationReport:
    """Aggregated evaluation report for an agent execution."""

    agent_name: str
    overall_score: float
    passed: bool
    scores: list[EvaluationScore] = field(default_factory=list)


class AgentEvaluator:
    """Evaluate agent outputs for grounding, confidence, and consistency."""

    def __init__(self, min_confidence: float = 0.35, min_grounding_score: float = 0.5) -> None:
        self._min_confidence = min_confidence
        self._min_grounding_score = min_grounding_score

    def evaluate(self, result: ExecutionResult) -> EvaluationReport:
        """Produce an evaluation report for a single agent result."""
        scores: list[EvaluationScore] = []

        confidence_passed = result.confidence_score >= self._min_confidence
        scores.append(
            EvaluationScore(
                dimension="confidence",
                score=result.confidence_score,
                passed=confidence_passed,
                details=f"Confidence {result.confidence_score:.2f}",
            )
        )

        grounding_score = 1.0 if result.grounded else 0.0
        grounding_passed = grounding_score >= self._min_grounding_score or not result.citations
        scores.append(
            EvaluationScore(
                dimension="grounding",
                score=grounding_score,
                passed=grounding_passed or result.grounded,
                details="Output is grounded in retrieved knowledge" if result.grounded else "No grounding evidence",
            )
        )

        citation_score = min(1.0, len(result.citations) / 3) if result.citations else 0.0
        scores.append(
            EvaluationScore(
                dimension="citations",
                score=citation_score,
                passed=len(result.citations) > 0 or not result.grounded,
                details=f"{len(result.citations)} citation(s) present",
            )
        )

        consistency_passed = result.status.value in {"completed", "idle"}
        scores.append(
            EvaluationScore(
                dimension="consistency",
                score=1.0 if consistency_passed else 0.0,
                passed=consistency_passed,
                details=f"Status: {result.status.value}",
            )
        )

        overall = sum(s.score for s in scores) / len(scores) if scores else 0.0
        passed = all(s.passed for s in scores)

        return EvaluationReport(
            agent_name=result.agent_name,
            overall_score=overall,
            passed=passed,
            scores=scores,
        )

    def evaluate_batch(self, results: list[ExecutionResult]) -> dict[str, Any]:
        """Evaluate a batch of results and return summary statistics."""
        reports = [self.evaluate(r) for r in results]
        if not reports:
            return {"count": 0, "avg_score": 0.0, "pass_rate": 0.0}

        return {
            "count": len(reports),
            "avg_score": sum(r.overall_score for r in reports) / len(reports),
            "pass_rate": sum(1 for r in reports if r.passed) / len(reports),
            "reports": [
                {"agent": r.agent_name, "score": r.overall_score, "passed": r.passed}
                for r in reports
            ],
        }
