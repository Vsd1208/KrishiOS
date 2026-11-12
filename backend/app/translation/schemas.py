"""Pydantic v2 schemas for the translation API."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

LANG = "^(en|hi|te)$"


class TranslateRequest(BaseModel):
    text: str = Field(min_length=1, max_length=8000)
    source_language: str = Field(pattern=LANG)
    target_language: str = Field(pattern=LANG)
    severity: str | None = Field(default=None, pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$")
    personal_data: bool = Field(
        default=True,
        description="True for farmer-provided text. Off-device providers are then skipped "
                    "unless ALLOW_OFF_DEVICE_PROVIDERS is enabled.",
    )
    back_translate: bool = False
    persist: bool = Field(default=False, description="Store a TranslationRecord for audit.")


class CheckOut(BaseModel):
    passed: bool
    missing_numbers: list[str]
    extra_numbers: list[str]
    missing_units: list[str]
    extra_units: list[str]
    missing_protected_terms: list[str]
    leftover_placeholders: list[str]
    numbers_in_source: int


class AttemptOut(BaseModel):
    provider: str
    provider_version: str | None
    outcome: str
    detail: str
    latency_ms: float | None


class TranslateResponse(BaseModel):
    source_language: str
    target_language: str
    text: str
    status: str
    deliverable: bool
    checks: CheckOut
    provider: str | None
    provider_version: str | None
    glossary_version: str
    cached: bool
    protected_spans: int
    attempts: list[AttemptOut]
    back_translation: str | None
    record_uuid: UUID | None = None


class CheckRequest(BaseModel):
    source: str = Field(min_length=1, max_length=8000)
    translation: str = Field(min_length=1, max_length=8000)


class ApproveRequest(BaseModel):
    edited_text: str | None = Field(
        default=None, max_length=8000,
        description="Reviewer's corrected translation. It is re-checked before approval.",
    )


class RecordOut(BaseModel):
    uuid: UUID
    status: str
    translated_text: str
    provider: str | None
    approved_by: UUID | None
    edited_by_reviewer: bool
    checks: dict


class GlossaryOut(BaseModel):
    version: str
    protected_terms: list[str]
    units: dict[str, list[str]]
