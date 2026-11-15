"""Sanity checks on the committed LGD reference tables."""

import pandas as pd

from krishios_ml.common.paths import REFERENCE_DIR


def test_lgd_districts_unique_and_complete() -> None:
    d = pd.read_csv(REFERENCE_DIR / "lgd_districts.csv")
    assert d.lgd_district_code.is_unique
    assert len(d) == 790  # snapshot observed 2026-11-12
    assert d.census_2011_code.notna().all()


def test_sachet_cap_code_resolves() -> None:
    # A live SACHET CAP alert (2026-11-12) carried LGD District Code 575 for Kanniyakumari.
    d = pd.read_csv(REFERENCE_DIR / "lgd_districts.csv").set_index("lgd_district_code")
    assert d.loc[575, "district_name"] == "Kanniyakumari"
    assert d.loc[575, "state_name"] == "Tamil Nadu"


def test_blocks_reference_known_districts() -> None:
    d = pd.read_csv(REFERENCE_DIR / "lgd_districts.csv")
    b = pd.read_csv(REFERENCE_DIR / "lgd_blocks.csv")
    assert b.lgd_block_code.is_unique
    assert set(b.lgd_district_code) <= set(d.lgd_district_code)
