# app/voice/models/__init__.py
from app.voice.models.audio import AudioRecord
from app.voice.models.transcript import SpeechTranscript

__all__ = [
    "AudioRecord",
    "SpeechTranscript",
]
