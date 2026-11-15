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


def test_indictrans2_bracketless_placeholders_restore() -> None:
    # IndicTrans2 drops ">" (not in its source vocabulary): "<ID1>" comes back as "<ID1".
    p = Protector()
    masked = p.mask("Spray Tricyclazole at 0.6 g/L for blast.", "en", "hi",
                    placeholder="<ID{i}>")
    assert "<ID0>" in masked.text and "<ID1>" in masked.text
    mt_output = "विस्फोट के लिए <ID0 पर <ID1 का छिड़काव करें ।"
    restored, missing = Protector.restore(mt_output, masked.spans)
    assert missing == []
    assert "0.6 g/L" in restored and "Tricyclazole" in restored
    assert check_translation("Spray Tricyclazole at 0.6 g/L for blast.", restored).passed


def test_less_than_text_is_not_a_placeholder() -> None:
    res = check_translation("Rain <5 mm expected", "<5 mm వర్షం")
    assert res.passed and res.leftover_placeholders == []


def test_rupee_spelling_does_not_match_inside_hours() -> None:
    # Bug found in the Phase 2 probe: "rs." matched the end of "hours.".
    assert extract_units("in next 3 hours.") == {}
    assert extract_units("Rs. 500 per quintal") == {"rupee": 1, "quintal": 1}


def test_bracketless_placeholder_with_prime_is_restored() -> None:
    masked = Protector().mask("Spray Thiram @ 2 g per kg", "en", "hi", placeholder="<ID{i}>")
    out = " ".join(f"<ID{s.index}′" for s in masked.spans)
    restored, missing = Protector.restore(out, masked.spans)
    assert missing == [] and "′" not in restored
