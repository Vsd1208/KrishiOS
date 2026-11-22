"""Phase 10c: ``POST /assistant/ask``: a cited answer from the vetted guides, or a clear decline."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.dependencies.auth import AuthContext, RequirePermission
from app.assistant.service import AssistantService
from app.assistant.wiring import get_assistant_service
from app.auth.permissions import Permission

router = APIRouter(prefix="/assistant", tags=["Assistant"])


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    language: Literal["en", "hi", "te"] = "en"


class SourceCitation(BaseModel):
    n: int
    title: str | None
    page: int | None
    source_url: str | None


class AskResponse(BaseModel):
    answered: bool = Field(description="False: no verified source was found, nothing is claimed")
    answer: str = Field(description="In the asked language, or English if translation_failed")
    answer_en: str
    citations: list[SourceCitation]
    translation_failed: bool
    model: str | None
    timings_ms: dict[str, float]


@router.post("/ask", response_model=AskResponse)
async def ask(
    body: AskRequest,
    _: Annotated[AuthContext, Depends(RequirePermission(Permission.KNOWLEDGE_SEARCH))],
    service: Annotated[AssistantService, Depends(get_assistant_service)],
) -> AskResponse:
    """Answer only from the vetted guides, citing passages; otherwise say there is no source.

    The question is farmer text (personal data): it is translated and answered on this machine
    only (local IndicTrans2 and the on-device LLM).
    """
    out = await service.ask(body.question, body.language)
    return AskResponse(answered=out.answered, answer=out.answer, answer_en=out.answer_en,
                       citations=[SourceCitation(**c) for c in out.citations],
                       translation_failed=out.translation_failed, model=out.model,
                       timings_ms=out.timings_ms)
