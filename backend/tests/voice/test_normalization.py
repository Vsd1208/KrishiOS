"""Tests for AgriculturalLanguageNormalizer and term resolution."""

from app.voice.services.normalization import AgriculturalLanguageNormalizer


def test_normalization_telugu_query():
    normalizer = AgriculturalLanguageNormalizer()
    res = normalizer.normalize("నా వరి పైరుకు అగ్గి తెగులు వచ్చింది, ఏమి చేయాలి?", "te")

    assert res.resolved_crop == "Paddy"
    assert res.resolved_disease == "Blast"
    assert len(res.extracted_entities) >= 2


def test_normalization_hindi_query():
    normalizer = AgriculturalLanguageNormalizer()
    res = normalizer.normalize("धान की फसल में भूरा धब्बा रोग का इलाज क्या है?", "hi")

    assert res.resolved_crop == "Paddy"
    assert res.resolved_disease == "Brown Spot"


def test_normalization_code_switched_query():
    normalizer = AgriculturalLanguageNormalizer()
    res = normalizer.normalize("నా వరి crop కి yellow spots వస్తున్నాయి", "te")

    assert res.is_code_switched is True
    assert res.resolved_crop == "Paddy"
    assert res.resolved_symptom == "Yellow Leaves"
