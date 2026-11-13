"""Bulletin extraction (rules-v1): values, provenance spans and review flags."""

from datetime import timedelta

from app.govconnect.extraction import IST, get_extractor

EN = """District Warning: Heavy Rainfall
Issued by Meteorological Centre Hyderabad on 12.11.2026 at 13:00 IST.
Orange alert: Heavy to very heavy rainfall with thunderstorm and lightning is likely at isolated
places in Khammam and Warangal districts of Telangana, valid till 14.11.2026.
Farmers are advised to postpone spraying on paddy and cotton and provide drainage in fields."""


def extract(text: str):
    return get_extractor().extract(text)


def test_english_warning_fields_and_provenance() -> None:
    e = extract(EN)
    v = e.value
    assert v("authority") == "Meteorological Centre (IMD)" and v("authority_level") == "state"
    assert v("issued_at").isoformat() == "2026-11-12T13:00:00+05:30"
    assert v("valid_to").isoformat() == "2026-11-14T23:59:00+05:30"
    assert v("district_codes") == [509, 522]  # Hyderabad is the issuer's office, not a target
    assert v("crops") == ["paddy", "cotton"]
    assert v("hazard_type") == "heavy_rain" and e.ambiguous["other_hazards"] == ["thunderstorm"]
    assert v("severity") == "HIGH"
    assert v("recommended_actions")[0].startswith("Farmers are advised to postpone")
    for f in e.fields.values():  # every span points at the exact source text
        for s in f.spans:
            assert EN[s.start:s.end] == s.text
    assert "severity" not in e.low_confidence and "district_codes" not in e.low_confidence


def test_telugu_relative_validity_and_authority() -> None:
    text = ("భారత వాతావరణ శాఖ హెచ్చరిక: రాబోయే 48 గంటల్లో భారీ వర్షాలు. జారీ 12-11-2026. "
            "రైతులు పిచికారీ వాయిదా వేయాలని సూచించారు.")
    e = extract(text)
    assert e.value("original_language") == "te"
    assert e.value("authority") == "India Meteorological Department"
    issued = e.value("issued_at")
    assert issued.isoformat() == "2026-11-12T00:00:00+05:30"
    assert e.value("valid_to") == issued + timedelta(hours=48)
    assert e.value("hazard_type") == "heavy_rain"
    assert e.value("recommended_actions")


def test_hindi_date_postposition_marks_validity() -> None:
    e = extract("कृषि विभाग सलाह। 15/11/2026 तक तेज हवा की संभावना। किसान सिंचाई रोकें, छिड़काव न करें।")
    assert e.value("original_language") == "hi"
    assert e.value("valid_to").date().isoformat() == "2026-11-15"
    assert e.value("hazard_type") == "strong_wind"


def test_no_colour_code_gives_low_confidence_severity() -> None:
    e = extract("Advisory from KVK Khammam district: apply neem oil 5 ml per litre on chilli.")
    assert e.value("severity") == "LOW" and "severity" in e.low_confidence
    assert e.value("authority_level") == "district"


def test_colliding_district_name_needs_district_word() -> None:
    # "Mandi" is also the word for market: only a district when written as one.
    assert 509 not in extract("Check mandi prices before selling.").value("district_codes", [])
    with_word = extract("Heavy rain warning for Mandi district of Himachal Pradesh.")
    assert with_word.value("district_codes")


def test_dates_carry_ist_timezone() -> None:
    e = extract("Valid from 2026-11-20 till 2026-11-22.")
    assert e.value("valid_from").tzinfo == IST
    assert e.value("valid_to").isoformat() == "2026-11-22T23:59:00+05:30"


def test_imd_nowcast_names_and_time_first_dates() -> None:
    # Patterns from the SACHET dev split (ADR-021): exonyms, spaceless spellings, directional
    # district names, district names inside state names, and "next 2-3 hours from <time, date>".
    e = extract("Light thunderstorm very likely over some parts of East Midnapore, Coochbehar "
                "and East Burdwan districts during next 2-3 hours from 22:45, 10-11-2026.")
    assert set(e.value("district_codes")) == {317, 308, 306}  # not Delhi's "East" (78)
    assert e.value("valid_to").isoformat() == "2026-11-11T01:45:00+05:30"
    assert extract("Heavy rain over 4 districts of Jammu and Kashmir.").value(
        "district_codes", []) == []  # "Jammu" here is the state, not the district
    issuer = extract("Light thunderstorm over Giridih. Disaster Management Department Ranchi.")
    assert issuer.value("district_codes") == [329]  # Ranchi is the issuing office
