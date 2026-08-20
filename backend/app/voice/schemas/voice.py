"""Pydantic schemas for the Voice API endpoints."""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class AudioRecordResponse(BaseModel):
    id: int
    uuid: UUID
    owner_uuid: UUID
    original_filename: str
    mime_type: str
    file_size: int
    duration_seconds: float
    language_detected: str | None = None
    language_confidence: float | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TranscriptResponse(BaseModel):
    id: int
    uuid: UUID
    audio_uuid: UUID
    raw_transcript: str
    detected_language: str
    language_confidence: float
    transcription_confidence: float
    model_name: str
    model_version: str
    normalized_query: str | None = None
    detected_intent: str | None = None
    extracted_entities: list[dict] | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class VoiceQueryResponse(BaseModel):
    """Structured response returned by POST /voice/query."""
    request_id: UUID
    audio_id: int
    audio_uuid: UUID
    detected_language: str
    raw_transcript: str
    normalized_query: str
    response_text: str
    spoken_audio_reference: UUID | None = None
    citations: list[dict] = Field(default_factory=list)
    confidence: float
    is_code_switched: bool = False
    processing_time_ms: float = 0.0
    agent_used: str = "crop_advisory_agent"

    model_config = {"from_attributes": True}
