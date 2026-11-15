"""APY (DES / MoA&FW "Area, Production, Yield") district statistics → normalised labels.

Source file: India Data Portal mirror of the Ministry's district-wise APY data (ODC-By), see
``ml/DATA_SOURCES.md``. ``district_code`` in the file is the LGD district code (Phase 6 check:
551/558 code-name pairs match LGD exactly; the 7 others are Odia spelling variants).

Normalisation (no values are changed, only typed and labelled):
- ``crop_year`` = first year of "1997-1998".
- ``season``: Kharif, Rabi, Whole Year kept; the rice seasons Autumn (aus) and Winter (aman)
  map to Kharif and Summer (boro) to Zaid (ADR-025, needs agronomist confirmation);
  "Total" rows are aggregates and are dropped so nothing is double-counted.
- ``crop_canonical`` through the crop catalog's ``apy_names``; unmapped crops are kept with
  ``crop_canonical = None`` and reported by the audit.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd

SEASON_MAP = {
    "kharif": "Kharif", "rabi": "Rabi", "whole year": "Whole Year", "autumn": "Kharif",
    "winter": "Kharif", "summer": "Zaid", "zaid": "Zaid", "total": None,
}
# Crops whose APY "Tonnes" label is contradicted by the data (Phase 6 audit): cotton yields of
# ~1.6 "t/ha" are bales (170 kg) of lint per ha; jute/mesta are 180 kg bales (APY/UPAg mesta
# ratio is exactly 1/0.18); coconut is nuts. The catalog's yield_unit is used instead.
UNIT_FROM_CATALOG = {"cotton", "jute", "mesta", "coconut"}
BALE_TONNES = {"bales_170kg/ha": 0.17, "bales_180kg/ha": 0.18}
COLUMNS = ["lgd_district_code", "district_name", "lgd_state_code", "state_name", "crop_year",
           "crop_raw", "apy_crop_code", "crop_type", "crop_canonical", "season_raw", "season",
           "area_ha", "production", "production_unit", "yield_reported", "yield_unit"]


def apy_crop_map(catalog_csv: Path) -> dict[str, str]:
    """APY crop name (case-insensitive) -> crop_canonical, from the catalog's ``apy_names``."""
    mapping: dict[str, str] = {}
    with catalog_csv.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            for name in (row.get("apy_names") or "").split("|"):
                if name.strip():
                    mapping[name.strip().lower()] = row["crop_canonical"]
    return mapping


def catalog_units(catalog_csv: Path) -> dict[str, str]:
    with catalog_csv.open(encoding="utf-8", newline="") as fh:
        return {r["crop_canonical"]: r["yield_unit"] for r in csv.DictReader(fh)}


def load_apy(csv_path: Path, catalog_csv: Path) -> tuple[pd.DataFrame, dict[str, int]]:
    raw = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
    stats = {"rows_raw": len(raw)}
    crop_map = apy_crop_map(catalog_csv)
    season_raw = raw["season"].str.strip()
    season = season_raw.str.lower().map(SEASON_MAP)
    stats["rows_total_season_dropped"] = int((season_raw.str.lower() == "total").sum())
    unknown_season = season.isna() & (season_raw.str.lower() != "total")
    stats["rows_unknown_season"] = int(unknown_season.sum())

    def num(col: str) -> pd.Series:
        return pd.to_numeric(raw[col].str.replace(",", "", regex=False).replace("", None),
                             errors="coerce")

    df = pd.DataFrame({
        "lgd_district_code": pd.to_numeric(raw["district_code"], errors="coerce").astype("Int64"),
        "district_name": raw["district_name"].str.strip(),
        "lgd_state_code": pd.to_numeric(raw["state_code"], errors="coerce").astype("Int64"),
        "state_name": raw["state_name"].str.strip(),
        "crop_year": pd.to_numeric(raw["year"].str[:4], errors="coerce").astype("Int64"),
        "crop_raw": raw["crop_name"].str.strip(),
        "apy_crop_code": raw["crop_code"].str.strip(),
        "crop_type": raw["crop_type"].str.strip(),
        "crop_canonical": raw["crop_name"].str.strip().str.lower().map(crop_map),
        "season_raw": season_raw,
        "season": season,
        "area_ha": num("area"),
        "production": num("production"),
        "production_unit": raw["production_unit"].str.strip(),
        "yield_reported": num("yield"),
        "yield_unit": raw["yield_unit"].str.strip(),
    })[COLUMNS]
    df = df[df["season"].notna()].reset_index(drop=True)
    units = catalog_units(catalog_csv)
    fix = df["crop_canonical"].isin(UNIT_FROM_CATALOG)
    df.loc[fix, "yield_unit"] = df.loc[fix, "crop_canonical"].map(units)
    df.loc[fix, "production_unit"] = df.loc[fix, "yield_unit"].str.replace("/ha", "", regex=False)
    stats["rows_unit_relabelled"] = int(fix.sum())
    df, stats["season_groups_combined"] = combine_seasons(df)
    stats["rows_kept"] = len(df)
    stats["rows_unmapped_crop"] = int(df["crop_canonical"].isna().sum())
    return df, stats


GROUP_KEYS = ["lgd_district_code", "crop_canonical", "crop_raw", "season", "crop_year"]


def combine_seasons(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Several raw seasons can map to one season (Assam/Odisha/Bihar/WB report autumn and
    winter rice separately; both are Kharif). Their yield is total production / total area,
    never the mean of the yields. Single-row groups keep the published yield unchanged.
    Returns (frame with one row per district-crop-season-year, number of groups combined)."""
    counts = df.groupby(GROUP_KEYS, dropna=False)["area_ha"].transform("size")
    single, multi = df[counts == 1], df[counts > 1]
    if multi.empty:
        return df.reset_index(drop=True), 0
    first = ["district_name", "lgd_state_code", "state_name", "apy_crop_code", "crop_type",
             "production_unit", "yield_unit"]
    agg = multi.groupby(GROUP_KEYS, dropna=False, as_index=False).agg(
        **{c: (c, "first") for c in first},
        season_raw=("season_raw", lambda s: "+".join(sorted(set(s)))),
        area_ha=("area_ha", lambda s: s.sum(min_count=1)),
        production=("production", lambda s: s.sum(min_count=1)),
    )
    agg["yield_reported"] = agg["production"] / agg["area_ha"].where(agg["area_ha"] > 0)
    combined = pd.concat([single, agg[single.columns]], ignore_index=True)
    return combined, len(agg)
