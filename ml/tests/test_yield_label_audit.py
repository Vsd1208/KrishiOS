"""Yield label audit: definitions behave as documented (synthetic frames, no data files)."""

import pandas as pd

from krishios_ml.yield_labels.audit import TierRule, assign_tier, audit, split_of


def frame(rows):
    base = {"lgd_state_code": 36, "production_unit": "Tonnes", "yield_unit": "Tonnes/Hectare",
            "crop_raw": "Rice", "season": "Kharif"}
    return pd.DataFrame([{**base, **r} for r in rows])


def series(n_years=10, district=509, yield_t=3.0, crop="paddy"):
    return [{"lgd_district_code": district, "crop_year": 2000 + i, "crop_canonical": crop,
             "area_ha": 1000.0, "production": 1000.0 * yield_t, "yield_reported": yield_t}
            for i in range(n_years)]


def test_counts_consistency_and_outliers() -> None:
    rows = series() + series(district=522)
    rows[3] = {**rows[3], "yield_reported": 3.6}  # reported != production/area (+20 %)
    rows[5] = {**rows[5], "production": 30000.0, "yield_reported": 30.0}  # 10x outlier
    rows.append({"lgd_district_code": 509, "crop_year": 2011, "crop_canonical": "paddy",
                 "area_ha": 500.0, "production": None, "yield_reported": None})  # missing
    (s,) = audit(frame(rows))
    assert s.district_years == 20 and s.years == 10 and s.districts == 2  # 2011 has no yield
    assert s.missing_rate == round(1 / 21, 4)
    assert s.consistency_fail_rate == round(1 / 20, 4)
    assert s.outlier_rate == round(1 / 20, 4)  # the 10x year, not the +20 % one
    assert s.median_yield == 3.0


def test_unmapped_crops_are_reported_not_tiered() -> None:
    rows = series(crop=None)
    (s,) = audit(frame(rows))
    assert s.crop == "raw:Rice" and not s.mapped
    rule = TierRule("C", 1, 1, 1, 1.0, 1.0)
    assert assign_tier(s, [rule]) == "excluded:unmapped_crop"


def test_tier_order_and_thresholds() -> None:
    (s,) = audit(frame(series(n_years=20)))
    rules = [TierRule("A", 100, 18, 1, 0.03, 0.05), TierRule("B", 10, 10, 1, 0.05, 0.1)]
    assert assign_tier(s, rules) == "B"  # 20 district-years < 100 for A
    assert assign_tier(s, [TierRule("A", 1000, 1, 1, 1, 1)]) == "excluded:insufficient"


def test_splits_keep_district_years_together_and_are_stable() -> None:
    kw = {"val_from": 2016, "test_from": 2019, "spatial_share": 0.10}
    assert split_of(509, 2010, **kw) == split_of(509, 2010, **kw)  # deterministic
    held_out = [d for d in range(1, 2001) if split_of(d, 2010, **kw) == "spatial_test"]
    assert 150 < len(held_out) < 250  # about 10 % of districts
    d = next(d for d in range(1, 2001) if split_of(d, 2010, **kw) != "spatial_test")
    assert [split_of(d, y, **kw) for y in (2015, 2016, 2018, 2019)] == \
        ["train", "val", "val", "test"]


def test_mapped_seasons_combine_by_production_over_area() -> None:
    from krishios_ml.yield_labels.apy import combine_seasons

    rows = [{"lgd_district_code": 300, "crop_canonical": "paddy", "crop_raw": "Rice",
             "season": "Kharif", "season_raw": sr, "crop_year": 2015, "district_name": "X",
             "lgd_state_code": 18, "state_name": "Assam", "apy_crop_code": "1",
             "crop_type": "Cereals", "production_unit": "Tonnes", "yield_unit": "t/ha",
             "area_ha": area, "production": prod, "yield_reported": prod / area}
            for sr, area, prod in (("Autumn", 100.0, 100.0), ("Winter", 900.0, 2700.0))]
    out, n = combine_seasons(pd.DataFrame(rows))
    assert n == 1 and len(out) == 1
    assert out.iloc[0]["yield_reported"] == 2.8  # 2800 t / 1000 ha, not mean(1.0, 3.0) = 2.0
    assert out.iloc[0]["season_raw"] == "Autumn+Winter"
