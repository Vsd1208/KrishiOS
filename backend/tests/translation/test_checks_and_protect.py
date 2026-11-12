"""Number/unit/protected-term checks and span protection."""

import pytest
from app.translation.checks import check_translation, extract_numbers, extract_units
from app.translation.protect import Protector


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Spray 0.6 g/L", {"0.6": 1}),
        ("मात्रा ०.६ ग्राम प्रति लीटर", {"0.6": 1}),  # Devanagari digits
        ("మోతాదు ౦.౬ గ్రాములు", {"0.6": 1}),  # Telugu digits
        ("Rs 1,50,000 and 150,000", {"150000": 2}),  # Indian vs western grouping
        ("2-3 days, 75% WP", {"2": 1, "3": 1, "75": 1}),
        ("model v1.2 and H2O are not quantities", {}),
    ],
)
def test_extract_numbers(text: str, expected: dict) -> None:
    assert dict(extract_numbers(text)) == expected


def test_extract_units_multilingual() -> None:
    assert extract_units("25 kg per acre") == {"kg": 1, "acre": 1}
    assert extract_units("25 किलो प्रति एकड़") == {"kg": 1, "acre": 1}
    assert extract_units("ఎకరానికి 25 కిలోలు") == {"acre": 1, "kg": 1}
    # 'kilogram' must not also count as 'gram'
    assert extract_units("1 kilogram") == {"kg": 1}


def test_check_passes_when_numbers_units_terms_survive() -> None:
    src = "Spray Tricyclazole 75% WP at 0.6 g/L of water."
    tgt = "నీటికి 0.6 g/L చొప్పున Tricyclazole 75% WP పిచికారీ చేయండి."
    assert check_translation(src, tgt).passed


def test_check_fails_on_changed_dose() -> None:
    src = "Apply 25 kg urea per acre."
    tgt = "ఎకరానికి 52 kg urea వేయండి."
    res = check_translation(src, tgt)
    assert not res.passed
    assert res.missing_numbers == ["25"] and res.extra_numbers == ["52"]


def test_check_fails_on_dropped_protected_term_and_leftover_placeholder() -> None:
    res = check_translation("Spray Imidacloprid 0.3 ml/L", "పిచికారీ చేయండి <1> 0.3 ml/L")
    assert not res.passed
    assert res.missing_protected_terms == ["imidacloprid"]
    assert res.leftover_placeholders == ["<1>"]


def test_formulation_codes_are_case_sensitive() -> None:
    # 'SC' (suspension concentrate) must not match 'sc' inside ordinary words.
    res = check_translation("Visit the school.", "పాఠశాలను సందర్శించండి.")
    assert res.passed


def test_protect_and_restore_roundtrip() -> None:
    p = Protector()
    masked = p.mask("Spray Tricyclazole 75% WP at 0.6 g/L on paddy.", "en", "te")
    kinds = sorted(s.kind for s in masked.spans)
    assert kinds == ["crop", "protected", "protected", "quantity", "quantity"]
    assert "0.6" not in masked.text and "Tricyclazole" not in masked.text
    # simulate an MT output that reorders placeholders and returns a Telugu numeral index
    fake_mt = " ".join(f"<{s.index}>" for s in reversed(masked.spans))
    restored, missing = Protector.restore(fake_mt.replace("<1>", "<౧>"), masked.spans)
    assert missing == []
    assert "వరి" in restored  # crop mapped to the catalog's Telugu name
    assert "0.6 g/L" in restored and "Tricyclazole" in restored


def test_placeholder_digits_are_not_quantities() -> None:
    masked = Protector().mask("Apply DAP 50 kg per acre", "en", "hi")
    quantities = [s.source for s in masked.spans if s.kind == "quantity"]
    assert quantities == ["50 kg per acre"]
