"""Model-ready yield label table (Phase 7), built from the Phase 6 audit.

Scope-freeze defaults (ADR-026):

- **Tiers:** tier v2 from the Phase 6 audit run of record; only A/B/C series are kept.
- **Eastern rice:** in Assam, Odisha, Bihar, West Bengal and Jharkhand, APY splits rice into
  aus/aman (Kharif) and boro (Zaid) and UPAg files aman differently, so rice there is modelled
  **annually**: production and area are summed over seasons and the yield is production/area
  (never a mean of yields). The annual series inherits the tier of paddy|Kharif.
- **Splits:** ``split_of`` (time split plus a 10% spatial district hold-out), unchanged.
- **Quality:** robust per-district outliers (including zero yields, i.e. crop failures) are
  flagged, not dropped; the model phase decides how to weight them.
"""

from __future__ import annotations

import pandas as pd

from krishios_ml.yield_labels.audit import _robust_outliers, split_of, usable

EAST_RICE_STATES = ("Assam", "Odisha", "Bihar", "West Bengal", "Jharkhand")
ANNUAL_SEASON = "Whole Year"
KEYS = ["lgd_district_code", "crop_canonical", "season", "crop_year"]


def annual_rice(df: pd.DataFrame, states=EAST_RICE_STATES) -> pd.DataFrame:
    """Replace paddy rows in ``states`` by one annual row per district-year."""
    east = (df["crop_canonical"] == "paddy") & df["state_name"].isin(states)
    if not east.any():
        return df.assign(seasons_combined=df["season"])
    g = df[east].groupby(["lgd_district_code", "crop_canonical", "crop_year"], as_index=False)
    annual = g.agg(
        district_name=("district_name", "first"),
        lgd_state_code=("lgd_state_code", "first"),
        state_name=("state_name", "first"),
        yield_unit=("yield_unit", "first"),
        area_ha=("area_ha", "sum"),
        production=("production", lambda s: s.sum(min_count=1)),
        seasons_combined=("season", lambda s: "+".join(sorted(set(s)))),
    )
    annual["season"] = ANNUAL_SEASON
    annual["yield"] = annual["production"] / annual["area_ha"].where(annual["area_ha"] > 0)
    rest = df[~east].assign(seasons_combined=df.loc[~east, "season"])
    return pd.concat([rest, annual[[c for c in rest.columns if c in annual]]], ignore_index=True)


def build_labels(apy: pd.DataFrame, tiers: dict[str, str], split: dict) -> pd.DataFrame:
    """``tiers``: ``"crop|season" -> tier`` from the audit run. Returns one row per KEYS."""
    df = usable(apy).dropna(subset=["crop_canonical", "yield"])
    df = df[df["area_ha"] > 0]
    df = annual_rice(df).dropna(subset=["yield"])
    tier_of = dict(tiers)
    tier_of[f"paddy|{ANNUAL_SEASON}"] = tiers.get("paddy|Kharif", "excluded:insufficient")
    df["tier"] = [tier_of.get(f"{c}|{s}", "excluded:insufficient")
                  for c, s in zip(df["crop_canonical"], df["season"], strict=True)]
    df = df[df["tier"].isin(["A", "B", "C"])].copy()
    flags = [_robust_outliers(g) for _, g in df.groupby(
        ["lgd_district_code", "crop_canonical", "season"])]
    df["outlier_flag"] = pd.concat(flags).reindex(df.index).fillna(False).astype(bool)
    df["split"] = [split_of(int(d), int(y), **split)
                   for d, y in zip(df["lgd_district_code"], df["crop_year"], strict=True)]
    cols = [*KEYS, "district_name", "state_name", "lgd_state_code", "area_ha", "production",
            "yield", "yield_unit", "seasons_combined", "tier", "outlier_flag", "split"]
    out = df[cols].astype({"lgd_district_code": "int64", "crop_year": "int64"})
    dup = out.duplicated(KEYS)
    if dup.any():
        raise ValueError(f"{int(dup.sum())} duplicate label keys")
    return out.sort_values(KEYS).reset_index(drop=True)
