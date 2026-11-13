"""Devanagari <-> Telugu transliteration used for IndicTrans2 script unification."""

from app.translation.script import devanagari_to_telugu, telugu_to_devanagari

# Real IndicTrans2 en->te output (script-unified Devanagari), 2026-11-13.
UNIFIED = "नुव्वुलनु जूलै मध्यकालं वरकु नाटवच्चु, किलोकु 2 ग्रामुल चॊप्पुन"
TELUGU = "నువ్వులను జూలై మధ్యకాలం వరకు నాటవచ్చు, కిలోకు 2 గ్రాముల చొప్పున"


def test_devanagari_to_telugu() -> None:
    assert devanagari_to_telugu(UNIFIED) == TELUGU


def test_roundtrip_is_lossless_for_telugu() -> None:
    assert devanagari_to_telugu(telugu_to_devanagari(TELUGU)) == TELUGU


def test_latin_digits_and_danda_untouched() -> None:
    assert devanagari_to_telugu("Thiram 2 g/kg।") == "Thiram 2 g/kg।"


def test_nukta_forms_map_to_base_consonant() -> None:
    assert devanagari_to_telugu("फ़") == "ఫ"
