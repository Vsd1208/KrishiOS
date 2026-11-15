"""Multilingual crop resolution against the shared catalog."""

import pytest
from app.catalog import ResolutionStatus, get_crop_catalog


@pytest.fixture(scope="module")
def catalog():
    return get_crop_catalog()


def test_catalog_has_core_crops(catalog) -> None:
    assert len(catalog) >= 50
    for key in ("paddy", "cotton", "chilli", "wheat", "maize"):
        assert key in catalog


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("My paddy leaves have brown spots", "paddy"),
        ("rice blast problem", "paddy"),
        ("నా వరి పైరుకు అగ్గి తెగులు వచ్చింది", "paddy"),
        ("నా వరికి మందు ఏమిటి", "paddy"),  # Telugu dative suffix -కి
        ("धान की फसल में रोग", "paddy"),
        ("मेरी कपास में सफेद मक्खी", "cotton"),
        ("పత్తి పంటకు గులాబీ పురుగు", "cotton"),
        ("mirchi lo thrips ekkuva", "chilli"),  # code-switched / romanised Telugu
        ("Chillies price in Guntur", "chilli"),  # plural
        ("गेहूं की बुवाई कब करें", "wheat"),
        ("phool gobhi me keede", "cauliflower"),  # multi-token alias beats 'gobhi'
        ("tur dal crop wilting", "pigeonpea"),  # from 'Pigeon pea (Tur/Arhar)'
    ],
)
def test_resolves_single_crop(catalog, text: str, expected: str) -> None:
    res = catalog.resolve(text)
    assert res.status is ResolutionStatus.RESOLVED, res
    assert res.crop == expected


def test_shared_alias_is_ambiguous(catalog) -> None:
    res = catalog.resolve("gobhi me keede lag gaye")
    assert res.status is ResolutionStatus.AMBIGUOUS
    assert set(res.candidates) == {"cabbage", "cauliflower"}
    assert res.crop is None


def test_two_crops_are_multiple(catalog) -> None:
    res = catalog.resolve("paddy and cotton both affected")
    assert res.status is ResolutionStatus.MULTIPLE
    assert set(res.candidates) == {"paddy", "cotton"}


def test_no_crop(catalog) -> None:
    res = catalog.resolve("will it rain tomorrow?")
    assert res.status is ResolutionStatus.NOT_FOUND


def test_no_false_positive_inside_latin_words(catalog) -> None:
    # 'tur' must not match inside 'nature'/'turmeric'; turmeric is its own crop.
    assert catalog.resolve("natural farming tips").status is ResolutionStatus.NOT_FOUND
    assert catalog.resolve("turmeric rhizome rot").crop == "turmeric"


def test_display_names(catalog) -> None:
    paddy = catalog.get("paddy")
    assert paddy.display_name("te") == "వరి"
    assert paddy.display_name("hi") == "धान"
    assert paddy.display_name("xx") == "Paddy (Rice)"


def test_resolve_name_exact(catalog) -> None:
    assert catalog.resolve_name("Arhar/Tur") is None  # APY names are not aliases yet
    assert catalog.resolve_name("arhar") == "pigeonpea"
    assert catalog.resolve_name("gobhi") is None  # ambiguous


def test_tiers_never_guessed(catalog) -> None:
    assert {e.tier for e in catalog.entries()} == {"unassigned"}
