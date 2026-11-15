# Phase 7: Yield Predictor Pipeline

- **Date:** 2026-11-15
- **Dataset build run of record:** `99682d517b17` (all stages, logged in `ml/experiments/yield_dataset.jsonl`). Metrics are in `ml/reports/data/yield_dataset_99682d517b17.json`.
- Earlier `yield_dataset` runs (`ef1960297312`, `31de753f4f38`, `a88136adb324`, `d54f474a73b8`, `52e8d40f92cd`, `1371b242058c`, `2140f09bffaa`, `7a82c4965c22`) were partial or used inputs that were later fixed (section 5). They are kept for the record but superseded.
- Build command, from `ml/`: `uv run --no-sync python scripts/build_yield_dataset.py --stage all`

**Integrity notes.**
- No model was trained and no metric was computed on any split. This phase builds inputs only.
- The scope-freeze answers in ADR-026 are **defaults I adopted to unblock work**. They still need faculty and agronomist sign-off.
- Features are raw district values. Climatologies, scalers and imputers will be fitted on train only, in Phase 8.

## 1. Outputs

All outputs are versioned (`v1`) and keyed by LGD district code.

| Output | Rows | What |
|---|---|---|
| `data/processed/yield_labels/v1/labels.parquet` | 340,765 | Label table: tier v2, split, outlier flag |
| `data/processed/yield_features/v1/district_daily/<year>.parquet` | 730 districts × 1997-2024 | District daily weather: 5 parameters |
| `data/processed/yield_features/v1/season_features.parquet` | 205,700 | 51,425 district × year × season keys, × 4 lead times |
| `data/processed/yield_features/v1/power_cell_weights.parquet` | - | Overlap weights per grid |
| `reference/district_polygon_crosswalk.csv` (committed) | 735 | Polygon → LGD match, with method and review flag |
| `reference/district_polygon_overrides.csv` (committed) | 60 | Reviewed renames and transliterations |

## 2. Labels

The label table is built from the Phase 6 audit run of record, `ee75501cc5ef`.

| | |
|---|---|
| Rows | 340,765 |
| Series (crop × season) | 108: the 107 tier-v2 series, plus annual eastern rice |
| Crops | 43 |
| Districts | 740 |
| Years | 1997-2022 |
| Tier A / B / C rows | 283,097 / 31,652 / 26,016 |
| Kharif / Rabi / Whole Year / Zaid rows | 149,173 / 107,952 / 60,025 / 23,615 |
| train / val / test / spatial_test rows | 211,612 / 41,814 / 58,224 / 29,115 |
| Rows flagged as robust outliers (kept, flagged) | 6.06% |
| Annual eastern-rice rows | 3,428 |

**Eastern rice.** In Assam, Odisha, Bihar, West Bengal and Jharkhand, rice is modelled annually: yield = total production / total area. APY and UPAg file the aman season differently, but agree 99.9% at annual level (report 06). A unit test checks that the annual yield is production over area, not a mean of seasonal yields.

## 3. District polygons

Source: geoBoundaries IND ADM2 (2021 vintage, built from LGD).

| Match method | Polygons |
|---|---|
| Exact name (after normalising accents and punctuation) | 619 |
| Alias list | 1 |
| Fuzzy (≥ 0.80, unique within state; all 50 reviewed: spelling variants) | 50 |
| Override: official rename | 50 |
| Override: Odia transliteration (LGD uses e.g. Kataka for Cuttack) | 6 |
| Override: predecessor (polygon predates a later split) | 4 |
| Unmatched | 5 |

The five unmatched polygons are Ladakh ("DATA NOT AVAILABLE"), Yanam, Mahe, Lakshadweep and Shahdara. None of them has tiered labels.

Before the overrides, 667 polygons were coded and 9.06% of label rows had no polygon. Now 730 LGD districts have one polygon each, and no code is shared.

## 4. Weather

Source: NASA POWER daily regional, 1997-2024.

| Grid | Parameters | Cell centres | Districts | Median cells per district | Single-cell districts |
|---|---|---|---|---|---|
| MERRA-2 0.5° × 0.625° | PRECTOTCORR, T2M_MAX, T2M_MIN, RH2M | 2,980 | 730 | 5 | 11 |
| CERES 1° × 1° | ALLSKY_SFC_SW_DWN | 916 | 730 | 3 | 79 |

- **Coverage:** district-day coverage is 100% for every parameter in every year, 1997-2024.
- **Labels with weather:** 99.76% of label rows have weather:

  | Split | Share with weather |
  |---|---|
  | train | 100% |
  | val | 99.93% |
  | test | 98.78% |
  | spatial_test | 99.71% |

- **Labels without weather:** the remaining 823 rows (28 districts, 2014-2022) are districts created after the 2021 polygon vintage. That is 13 new Andhra Pradesh districts, 5 in Chhattisgarh, 5 in Nagaland, and one or two each in Haryana, Karnataka, Punjab and Sikkim. They stay missing; they are not mapped to the parent district.
- **Sanity check:** Khammam (LGD 509) had 691 mm of rain in 2015, a deficit year, and mean solar radiation of 18.9 MJ/m²/day.

**Season features.** There is one row per district × crop year × season × lead time (0, 30, 60 and 90 days).

- **Window:** `[anchor − 60 d, anchor + lead)`. The anchors are 1 Jun (Kharif, Whole Year), 1 Oct (Rabi) and 1 Mar of the next year (Zaid).
- **Features:**
  - rainfall sum;
  - rain days (≥ 2.5 mm);
  - longest dry spell (< 1 mm);
  - mean Tmax and Tmin;
  - heat days (Tmax ≥ 35 °C);
  - growing degree days (base 10 °C, cap 35 °C);
  - mean RH;
  - mean solar radiation;
  - a coverage share for each group;
  - `last_input_date`.
- **Coverage:** the median coverage is 1.0 at every lead time.

**No-leakage test.** Every value on or after the cutoff is replaced with extremes (999 mm, 60 °C). The features must stay identical, and the last input must be the day before the cutoff (`tests/test_yield_features.py`).

## 5. Problems found and fixed in this phase

1. **Solar radiation on the wrong grid (my bug).**
   - What happened: solar radiation was averaged with MERRA-2 weights. It only matched where cell centres happened to coincide, leaving 27.86% coverage in every year.
   - Correction: my earlier note that solar was "72% missing in 1997" described this bug, not the data.
   - Fix: weights are now built per grid. `build_daily` raises an error if any weighted cell is absent, and a regression test covers this.
2. **Odia transliterations and official renames.** These were invisible to string similarity (Cuttack/Kataka, Gurgaon/Gurugram, Belgaum/Belagavi, and so on). They are fixed by the reviewed override file. Each row records its relation, and the build fails if an override matches no polygon or points to an unknown LGD code.
3. **The Andaman & Nicobar Islands were outside every POWER box.** A 10th box (6-16°N, 88-98°E) was added.
4. **Two downloads ran at once.** A process from the previous session was still running, and both wrote the same cache. I stopped the older process by PID. All files were then checked: each reads and has a full year. Cache writes are now atomic (temporary file, then rename).
5. **Two 2024 chunks failed** after retries (a timeout and an incomplete read). They were refetched; the cache is complete at 1,400 files.
6. **The polygon crosswalk was built by a one-off command.** It is now the reproducible `boundaries` stage.

## 6. Satellite NDVI (in progress)

- **Request:** MOD13A3.061 monthly 1 km NDVI plus pixel reliability, February 2000 to 2024. One AppEEARS area request covers India: a simplified state union with 44 parts and 1,644 vertices.
- **Status:** submitted 2026-11-15, task `895e0eb5-7cf5-4fff-ba67-da25754bb304`, status *pending* at NASA.
- **Size check:** `scripts/modis_request.py sizes` reports the real size before download.
- **Processing** (`yield_features/modis.py`, tested):
  - district raster index (pixel centres; districts too small for a centre get their touched pixels);
  - mean over pixels with reliability 0 (good) or 1 (marginal);
  - good-pixel share recorded.
- **Leak-safe rule:** a month enters a forecast only if month end + 15 days is before the cutoff. A test poisons all later months to check this.
- **Gap:** label years 1997-1999 predate MODIS and will have no NDVI.

## 7. Limitations

- **Missing modalities:**
  - soil: SoilGrids was unreachable;
  - irrigation and management: no district data ingested;
  - NDVI: pending.
- **Crop calendar:** it is season-level and draft, so lead windows are the same for every crop in a season. Crop × state calendars from an agronomist would change the anchors.
- **District splits:** labels from before a split use the LGD code of the district that exists now. 4 predecessor polygons cover more area than today's district (Korea, Ballari, Gangtok, Gyalshing).
- **Grid size:** POWER is coarse, and 11 districts (MERRA-2) and 79 districts (CERES) take their values from a single cell.

## 8. For review

1. Confirm or replace the ADR-026 scope-freeze defaults.
2. Have a second reviewer check `reference/district_polygon_overrides.csv` and the 50 fuzzy matches (`review=True` in the crosswalk).
3. Get agronomist input on crop × state sowing windows. This is the largest open source of error in the lead-time windows.
