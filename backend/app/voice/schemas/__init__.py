# app/voice/schemas/__init__.py
from app.voice.schemas.voice import (
    VoiceQueryResponse,
    AudioRecordResponse,
    TranscriptResponse,
)

__all__ = [
    "VoiceQueryResponse",
    "AudioRecordResponse",
    "TranscriptResponse",
]
