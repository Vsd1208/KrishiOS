"""Tests for the shared crop catalog."""

import pytest

from krishios_ml.common.catalog import ambiguous_aliases, load_catalog, normalize


def test_catalog_loads_and_validates() -> None:
    rows = load_catalog()
    assert len(rows) >= 50
    keys = {r.crop_canonical for r in rows}
    for required in ("paddy", "cotton", "chilli", "wheat", "maize", "tomato"):
        assert required in keys


def test_every_crop_has_te_and_hi_names() -> None:
    for row in load_catalog():
        assert row.name_te and row.name_hi, row.crop_canonical


def test_tiers_unassigned_until_label_audit() -> None:
    # Tiers are set from data in Phase 6, never guessed.
    assert {r.tier for r in load_catalog()} == {"unassigned"}


def test_gobhi_is_ambiguous_between_cabbage_and_cauliflower() -> None:
    amb = ambiguous_aliases(load_catalog())
    assert amb[normalize("gobhi")] == ["cabbage", "cauliflower"]


def test_invalid_catalog_reports_errors(tmp_path) -> None:
    bad = tmp_path / "c.csv"
    header = (
        "crop_canonical,name_en,name_te,name_hi,aliases,scientific_name,crop_group,domain,"
        "seasons,yield_unit,apy_names,tier,vision_supported,review_status\n"
    )
    bad.write_text(header + "Bad Key,X,,Y,,,,crop,monsoon,t/ha,,Z,false,draft\n", encoding="utf-8")
    with pytest.raises(ValueError) as err:
        load_catalog(bad)
    msg = str(err.value)
    assert "snake_case" in msg and "seasons" in msg and "tier" in msg and "name_te" in msg
