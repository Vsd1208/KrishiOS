"""Phase 10c assistant API: grounded answers (/assistant/ask) and document analysis."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from app.api.dependencies.auth import AuthContext, RequirePermission
from app.assistant.documents import DocumentAnalyzer, FarmerContext
from app.assistant.jobs import Job, JobStore, get_job_store
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
    parts_read: int
    parts_total: int
    truncated: bool = Field(description="True: some parts of the document were not read")
    dropped_lines: int = Field(description="Lines removed because a number was not in the "
                                           "document")
    translation_failed: bool
    model: str | None
    timings_ms: dict[str, float]


class DocumentJobResponse(BaseModel):
    job_id: str
    status: Literal["queued", "running", "done", "failed"]
    queue_position: int = Field(description="Jobs ahead of this one (0 = running or next)")
    error: str | None = None
    result: DocumentAnalysisResponse | None = None


def _job_response(job: Job, store: JobStore) -> DocumentJobResponse:
    result = None
    if job.status == "done":
        out = job.result
        result = DocumentAnalysisResponse(
            audience=out.audience, language=out.language, text=out.text, text_en=out.text_en,
            extracted=out.extracted, pages=out.pages, chars_read=out.chars_read,
            parts_read=out.parts_read, parts_total=out.parts_total, truncated=out.truncated,
            dropped_lines=out.dropped_lines, translation_failed=out.translation_failed,
            model=out.model, timings_ms=out.timings_ms)
    return DocumentJobResponse(job_id=job.job_id, status=job.status,
                               queue_position=store.position(job), error=job.error,
                               result=result)


def _crop_list(crops: str | None) -> list[str]:
    return [c.strip() for c in (crops or "").split(",") if c.strip()][:10]


@router.post("/analyze-document", response_model=DocumentJobResponse,
             status_code=status.HTTP_202_ACCEPTED)
async def analyze_document(  # noqa: PLR0913, PLR0917 - FastAPI form fields
    auth: Annotated[AuthContext, Depends(RequirePermission(Permission.KNOWLEDGE_SEARCH))],
    analyzer: Annotated[DocumentAnalyzer, Depends(get_document_analyzer)],
    store: Annotated[JobStore, Depends(get_job_store)],
    file: Annotated[UploadFile, File(description="PDF, DOCX, TXT or photo of a document")],
    audience: Annotated[Literal["officer", "farmer"], Form()] = "farmer",
    language: Annotated[Literal["en", "hi", "te"], Form()] = "en",
    crops: Annotated[str | None, Form(description="Comma-separated, e.g. paddy,cotton")] = None,
    district: Annotated[str | None, Form(max_length=100)] = None,
    state: Annotated[str | None, Form(max_length=100)] = None,
) -> DocumentJobResponse:
    """Queue a brief (officer) or a plain summary (farmer); poll GET /analyze-document/{job_id}.

    Takes minutes on a laptop, so it runs in the background, one job at a time. The file and the
    result stay in memory only (a farmer's upload is personal data) and expire after an hour.
    Crops, district and state focus a long document on the parts that concern the farmer.
    """
    if audience == "officer" and not auth.has_permission(Permission.DOCUMENT_READ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Officer briefs are for staff")
    data = await file.read()
    if len(data) > get_settings().MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File is too large")
    context = (FarmerContext(crops=_crop_list(crops), district=district, state=state)
               if (crops or district or state) else None)
    filename = file.filename or "upload"
    job = store.submit(str(auth.user_uuid), lambda: analyzer.analyze(
        data, filename, audience, language, context))
    return _job_response(job, store)


@router.get("/analyze-document/{job_id}", response_model=DocumentJobResponse)
async def document_job(
    job_id: str,
    auth: Annotated[AuthContext, Depends(RequirePermission(Permission.KNOWLEDGE_SEARCH))],
    store: Annotated[JobStore, Depends(get_job_store)],
) -> DocumentJobResponse:
    """Status of a document job, with the result once done. Only its submitter can see it."""
    job = store.get(job_id, str(auth.user_uuid))
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found or expired")
    return _job_response(job, store)

