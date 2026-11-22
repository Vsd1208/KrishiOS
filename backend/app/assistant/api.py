"""Phase 10c assistant API: grounded answers (/assistant/ask) and document analysis."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from app.api.dependencies.auth import AuthContext, RequirePermission
from app.assistant.documents import DocumentAnalyzer
from app.assistant.service import AssistantService
from app.assistant.wiring import get_assistant_service, get_document_analyzer
from app.auth.permissions import Permission
from app.config.settings import get_settings

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


class DocumentAnalysisResponse(BaseModel):
    audience: Literal["officer", "farmer"]
    language: str
    text: str = Field(description="Brief or summary in the asked language (English if "
                                  "translation_failed)")
    text_en: str
    extracted: dict = Field(description="Officer brief: structured fields with source spans")
    pages: int
    chars_read: int
    truncated: bool = Field(description="True: only the first part of the document was read")
    dropped_lines: int = Field(description="Lines removed because a number was not in the "
                                           "document")
    translation_failed: bool
    model: str | None
    timings_ms: dict[str, float]


@router.post("/analyze-document", response_model=DocumentAnalysisResponse)
async def analyze_document(
    auth: Annotated[AuthContext, Depends(RequirePermission(Permission.KNOWLEDGE_SEARCH))],
    analyzer: Annotated[DocumentAnalyzer, Depends(get_document_analyzer)],
    file: Annotated[UploadFile, File(description="PDF, DOCX, TXT or photo of a document")],
    audience: Annotated[Literal["officer", "farmer"], Form()] = "farmer",
    language: Annotated[Literal["en", "hi", "te"], Form()] = "en",
) -> DocumentAnalysisResponse:
    """Brief for an officer or plain summary for a farmer. The file is read in memory and not
    stored (a farmer's upload is personal data); everything runs on this machine."""
    if audience == "officer" and not auth.has_permission(Permission.DOCUMENT_READ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Officer briefs are for staff")
    data = await file.read()
    if len(data) > get_settings().MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File is too large")
    out = await analyzer.analyze(data, file.filename or "upload", audience, language)
    return DocumentAnalysisResponse(
        audience=out.audience, language=out.language, text=out.text, text_en=out.text_en,
        extracted=out.extracted, pages=out.pages, chars_read=out.chars_read,
        truncated=out.truncated, dropped_lines=out.dropped_lines,
        translation_failed=out.translation_failed, model=out.model, timings_ms=out.timings_ms)
