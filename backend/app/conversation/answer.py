"""Run the agent runtime for an English goal and assemble one answer with citations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

# Order in which agent outputs become the main answer text.
_TEXT_KEYS = ("recommendation", "scheme_details", "summary", "answer", "advisory_text")
LOW_CONFIDENCE = 0.5


@dataclass(slots=True)
class AnswerContext:
    goal_en: str
    session_id: str
    crop_name_en: str | None = None
    district: str | None = None
    state: str | None = None
    season: str | None = None
    auth: Any = None  # AuthContext of the caller; tools may check permissions


@dataclass(slots=True)
class AssembledAnswer:
    text_en: str
    citations: list[dict[str, Any]] = field(default_factory=list)
    agents: list[str] = field(default_factory=list)
    grounded: bool = False
    confidence: float = 0.0
    weather: dict[str, Any] | None = None
    requires_review: bool = False
    review_reason: str | None = None


class AnswerRunner(Protocol):
    async def run(self, ctx: AnswerContext) -> AssembledAnswer: ...


def _weather_text(data: dict[str, Any]) -> str | None:
    forecast = data.get("forecast") or {}
    parts = [str(forecast[k]) for k in ("summary", "spray_window_reason") if forecast.get(k)]
    return " ".join(parts) or None


def assemble(results: list[Any]) -> AssembledAnswer:
    """Pick the main answer text from the agents' outputs and merge citations."""
    text: str | None = None
    weather: dict[str, Any] | None = None
    citations: list[dict[str, Any]] = []
    agents: list[str] = []
    confidences: list[float] = []
    grounded = False
    for r in results:
        agents.append(r.agent_name)
        output = r.output or {}
        if r.agent_name == "weather_intelligence_agent" and output:
            weather = output
        for key in _TEXT_KEYS:
            value = output.get(key)
            if text is None and isinstance(value, str) and value.strip():
                text = value.strip()
        for c in r.citations or []:
            if c not in citations:
                citations.append(c)
        if r.agent_name != "response_validation_agent":
            confidences.append(float(r.confidence_score or 0.0))
            grounded = grounded or bool(r.grounded)
    if text is None and weather:
        text = _weather_text(weather)
    confidence = max(confidences) if confidences else 0.0
    answer = AssembledAnswer(text_en=text or "", citations=citations, agents=agents,
                             grounded=grounded, confidence=round(confidence, 3),
                             weather=weather)
    if not answer.text_en:
        answer.requires_review, answer.review_reason = True, "no_answer"
    elif not grounded and not weather:
        answer.requires_review, answer.review_reason = True, "not_grounded"
    elif confidence < LOW_CONFIDENCE:
        answer.requires_review, answer.review_reason = True, "low_confidence"
    return answer


class RuntimeAnswerRunner:
    """Production runner: the existing agent runtime (planner routes on NLU)."""

    async def run(self, ctx: AnswerContext) -> AssembledAnswer:
        from app.agents.execution.context import ExecutionContext  # noqa: PLC0415
        from app.agents.runtime.factory import get_runtime_engine  # noqa: PLC0415

        runtime = get_runtime_engine()
        exec_ctx = ExecutionContext(session_id=ctx.session_id, auth=ctx.auth,
                                    crop=ctx.crop_name_en,
                                    district=ctx.district, state=ctx.state, season=ctx.season)
        results = await runtime.execute(ctx.goal_en, ctx.session_id, exec_ctx)
        return assemble(results)
