"""Tests for AudioValidator service."""

from app.voice.services.validator import AudioValidator


def test_audio_validator_accepts_valid_wav(monkeypatch):
    class MockSettings:
        MAX_AUDIO_UPLOAD_SIZE_MB = 25
        MAX_AUDIO_DURATION_SECONDS = 180
        AUDIO_ALLOWED_MIMES = ["audio/wav", "audio/mpeg", "audio/webm"]

    monkeypatch.setattr("app.voice.services.validator.get_settings", lambda: MockSettings())

    validator = AudioValidator()
    # Dummy RIFF WAV header
    wav_bytes = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00" + b"0" * 2000

    result = validator.validate(wav_bytes, "audio/wav")

    assert result.valid is True
    assert result.mime_type == "audio/wav"
    assert result.file_size == len(wav_bytes)
    assert len(result.errors) == 0


def test_audio_validator_rejects_empty_file():
    validator = AudioValidator()
    result = validator.validate(b"", "audio/wav")

    assert result.valid is False
    assert any("empty" in err for err in result.errors)


def test_audio_validator_rejects_oversized_file(monkeypatch):
    class MockSettings:
        MAX_AUDIO_UPLOAD_SIZE_MB = 1  # 1 MB limit
        MAX_AUDIO_DURATION_SECONDS = 180
        AUDIO_ALLOWED_MIMES = ["audio/wav"]

    monkeypatch.setattr("app.voice.services.validator.get_settings", lambda: MockSettings())
    validator = AudioValidator()

    file_bytes = b"RIFF" + b"0" * (2 * 1024 * 1024)
    result = validator.validate(file_bytes, "audio/wav")

    assert result.valid is False
    assert any("exceeds maximum size" in err for err in result.errors)
