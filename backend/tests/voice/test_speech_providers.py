"""Registration and disclosure of real speech providers (models are not loaded here)."""

from app.providers import ProviderKind
from app.voice.providers.selection import stt_selector, tts_selector


def test_real_stt_providers_registered() -> None:
    names = stt_selector.names()
    assert {"faster-whisper-small", "faster-whisper-medium", "gemini-stt"} <= set(names)
    assert stt_selector.info("faster-whisper-small").kind is ProviderKind.LIVE
    assert not stt_selector.info("faster-whisper-small").sends_data_off_device


def test_gemini_stt_discloses_off_device() -> None:
    assert stt_selector.info("gemini-stt").sends_data_off_device


def test_mms_tts_discloses_non_commercial_licence() -> None:
    info = tts_selector.info("mms-tts")
    assert "non-commercial" in info.description.lower()
    assert "CC BY-NC" in info.description


def test_providers_are_lazy() -> None:
    # Registering must not load any model; instances are created on first get().
    assert "faster-whisper-small" not in stt_selector._instances
