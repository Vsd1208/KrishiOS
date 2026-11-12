"""LGD directory lookups."""

from app.catalog import get_lgd_directory


def test_lookup_by_code() -> None:
    lgd = get_lgd_directory()
    assert len(lgd) == 790
    d = lgd.district(575)
    assert d is not None and d.district_name == "Kanniyakumari" and d.state_name == "Tamil Nadu"


def test_resolve_by_name_and_state() -> None:
    lgd = get_lgd_directory()
    d = lgd.resolve_district("Khammam", "Telangana")
    assert d is not None and d.lgd_district_code == 509


def test_duplicate_district_names_need_state() -> None:
    lgd = get_lgd_directory()
    # 'Bilaspur' exists in Himachal Pradesh (15) and Chhattisgarh (375).
    matches = lgd.find_districts("Bilaspur")
    assert {d.lgd_district_code for d in matches} == {15, 375}
    assert lgd.resolve_district("Bilaspur") is None
    assert lgd.resolve_district("Bilaspur", "Chhattisgarh").lgd_district_code == 375


def test_blocks_for_district() -> None:
    lgd = get_lgd_directory()
    blocks = lgd.blocks_of(509)
    assert blocks and all(b.lgd_district_code == 509 for b in blocks)
