# Phase 6: Yield Label Audit

- **Date:** 2026-11-14
- **Audit run of record:** `ee75501cc5ef`, logged in `ml/experiments/yield_label_audit.jsonl`. The full per-series metrics are in `ml/reports/data/yield_label_audit_ee75501cc5ef.json`.
- An earlier run, `cfdb0966e45e`, had two bugs, found and fixed during this audit (section 3). It is kept for the record.

**Integrity notes.**
- Every number below comes from the audit run above.
- Tier thresholds and splits are **proposals for the scope freeze**. No model has been trained or evaluated, so nothing was tuned on test results.
- The season mapping and the crop calendar are drafts that need an agronomist.

## 1. Sources

| Source | What | Years | Rows | Licence | Status |
|---|---|---|---|---|---|
| APY (DES, MoA&FW), India Data Portal mirror | District x crop x season area, production, yield | 1997-2022 | 455,359 raw | ODC-By | **Primary label** |
| UPAg (MoA&FW), India Data Portal mirror | Same measures, unified portal | 2013-2024 | 156,189 | ODC-By | Cross-check, and candidate for 2023-2024 |
| ICRISAT-TCI DLD | Boundary-apportioned district data, 1966-2017 | - | - | Unresolved (CC BY vs CC BY-NC) | **Not ingested:** `data.icrisat.org` unreachable on 2026-11-14; Dataverse needs a login |

**District keys.** Both files carry **LGD district codes**. In APY, 551 of 558 code-name pairs match our LGD reference exactly, and the other 7 are Odia spelling variants (e.g. Balasore / Baleshwar). No name crosswalk is needed (ADR-025).

## 2. Ingestion

| Step | Count |
|---|---|
| Raw APY rows | 455,359 |
| "Total" season rows dropped (aggregates that would double-count) | 48,044 |
| Raw seasons combined into one season (e.g. Autumn + Winter rice -> Kharif), by total production / total area | 5,418 groups |
| Rows relabelled to their real unit (cotton, jute, mesta, coconut; see section 3) | 15,826 |
| Rows kept | 401,840 |
| Rows whose crop is not in the catalog (reported below, not tiered) | 31,605 |

The output is versioned Parquet, `ml/data/processed/yield_labels/v1/{apy,upag}.parquet`, keyed by LGD district code. It is not committed; `scripts/run_yield_label_audit.py` rebuilds it from the downloaded files.

## 3. What the audit found

1. **APY's "Tonnes" unit label is wrong for four crops.** The audit tests units from the magnitudes, not only from the unit column:
   - **Cotton** has a median of 1.64 "t/ha", while lint yields are about 0.3-0.6 t/ha. These are **bales of 170 kg per ha**.
   - **Jute and mesta** are **bales of 180 kg**. Mesta's APY/UPAg ratio is exactly 5.556 = 1/0.18.
   - **Coconut**, at about 8,100 "t/ha", is **nuts per ha**.
   - These four crops now carry the catalog unit. Values are unchanged; only the label is corrected.
2. **Bug (fixed): mean of yields across combined seasons.** When two raw seasons mapped to one season, their yields were averaged. They are now combined as total production / total area. Unit test: `test_mapped_seasons_combine_by_production_over_area`.
3. **Bug (fixed): outliers missed in near-constant series.** When most years are identical, the robust scale (MAD) was zero, so outliers were never flagged. The code now falls back to the mean absolute deviation.
4. **APY vs UPAg agreement:** **97.5%** of 77,316 overlapping district-crop-season-years agree within 5% (years 2013-2022).
   - Mesta agrees 100% after converting bales to tonnes.
   - Paddy agrees 84% season by season, but **99.9% on annual totals** (6,370 district-years).
   - The difference is a **season convention**, not bad data: UPAg books winter (aman) rice under Rabi in Assam, Odisha, Bihar, West Bengal and Jharkhand, while our APY mapping puts it in Kharif. This is a decision for you (section 6).
5. **Internal consistency is high:** the reported yield matches production / area within 5% in almost every row. Per-series failure rates are in the JSON.
6. **Outlier rates of 3-9%** in rainfed crops (pulses, cotton, sorghum, sesame) mostly reflect **real crop failures**, such as droughts and zero-yield years (maize/Kharif alone has 220 zero-yield rows), not label errors. They are reported and must be handled in training (robust loss or flags), not silently dropped.

## 4. Tiers (proposal)

**v1** was set before the counts were seen. It gated on outlier rate (at most 3% / 5% / 8%) and gave 5 A, 23 B and 54 C (82 series). That excluded the largest series in the country (maize Kharif, chickpea Rabi) purely because of real drought variability.

**v2** (proposed) gates on coverage and treats the outlier rate as a quality flag with a looser cap:

| Tier | District-years | Years | Districts | Max outlier rate | Max missing |
|---|---|---|---|---|---|
| A | >= 2,000 | >= 18 | >= 150 | 10% | 5% |
| B | >= 500 | >= 12 | >= 40 | 10% | 10% |
| C | >= 100 | >= 8 | >= 10 | 12% | 20% |

**Result:**
- **107 crop-season series across 43 crops:** 46 A, 27 B, 34 C.
- **Excluded:** 70 series have too little data, and 96 have crops that are not in the catalog.
- **Against the target:** the brief expected about 100 series. The audit supports 107, but tier C series (100-500 district-years) are thin, and a per-crop model will be weak for them.

| Tier | Crop | Season | District-years | Years | Districts | States | Outlier rate | Median yield | Unit |
|---|---|---|---|---|---|---|---|---|---|
| A | paddy | Kharif | 15,049 | 26 | 723 | 33 | 0.026 | 2.041 | t/ha |
| A | maize | Kharif | 13,843 | 26 | 707 | 30 | 0.060 | 1.765 | t/ha |
| A | wheat | Rabi | 12,399 | 26 | 639 | 30 | 0.025 | 2.113 | t/ha |
| A | rapeseed_mustard | Rabi | 11,673 | 26 | 657 | 32 | 0.051 | 0.843 | t/ha |
| A | chickpea | Rabi | 11,660 | 26 | 635 | 28 | 0.056 | 0.888 | t/ha |
| A | sesame | Kharif | 11,280 | 26 | 683 | 30 | 0.077 | 0.333 | t/ha |
| A | pigeonpea | Kharif | 11,238 | 26 | 653 | 27 | 0.068 | 0.795 | t/ha |
| A | black_gram | Kharif | 10,963 | 26 | 633 | 28 | 0.053 | 0.5 | t/ha |
| A | green_gram | Kharif | 10,163 | 26 | 631 | 26 | 0.069 | 0.436 | t/ha |
| A | sugarcane | Whole Year | 9,954 | 26 | 633 | 30 | 0.091 | 54.444 | t/ha |
| A | groundnut | Kharif | 9,469 | 26 | 587 | 28 | 0.043 | 1.025 | t/ha |
| A | sorghum | Kharif | 7,861 | 26 | 521 | 24 | 0.053 | 1.0 | t/ha |
| A | pearl_millet | Kharif | 7,560 | 26 | 511 | 23 | 0.041 | 1.077 | t/ha |
| A | field_pea | Rabi | 7,444 | 26 | 517 | 22 | 0.089 | 0.999 | t/ha |
| A | lentil | Rabi | 7,210 | 26 | 460 | 25 | 0.059 | 0.75 | t/ha |
| A | small_millets | Kharif | 6,802 | 26 | 560 | 28 | 0.083 | 0.622 | t/ha |
| A | linseed | Rabi | 6,648 | 26 | 439 | 22 | 0.090 | 0.5 | t/ha |
| A | cotton | Kharif | 6,577 | 26 | 462 | 26 | 0.076 | 1.643 | bales_170kg/ha |
| A | barley | Rabi | 6,249 | 26 | 356 | 16 | 0.049 | 1.842 | t/ha |
| A | chilli | Whole Year | 5,849 | 26 | 528 | 23 | 0.095 | 0.833 | t/ha |
| A | soybean | Kharif | 5,778 | 26 | 452 | 24 | 0.056 | 1.0 | t/ha |
| A | potato | Whole Year | 5,751 | 26 | 537 | 28 | 0.072 | 9.866 | t/ha |
| A | onion | Whole Year | 5,414 | 26 | 508 | 24 | 0.091 | 8.649 | t/ha |
| A | maize | Rabi | 5,259 | 26 | 446 | 20 | 0.054 | 2.833 | t/ha |
| A | paddy | Zaid | 4,846 | 26 | 369 | 16 | 0.031 | 2.548 | t/ha |
| A | finger_millet | Kharif | 4,595 | 26 | 363 | 21 | 0.038 | 1.0 | t/ha |
| A | maize | Zaid | 4,358 | 26 | 310 | 11 | 0.034 | 2.19 | t/ha |
| A | coriander | Whole Year | 4,327 | 26 | 381 | 15 | 0.089 | 0.5 | t/ha |
| A | horse_gram | Kharif | 4,101 | 26 | 320 | 15 | 0.065 | 0.452 | t/ha |
| A | green_gram | Zaid | 3,921 | 26 | 339 | 12 | 0.037 | 0.605 | t/ha |
| A | onion | Rabi | 3,896 | 24 | 360 | 18 | 0.029 | 14.18 | t/ha |
| A | potato | Rabi | 3,851 | 25 | 332 | 17 | 0.058 | 15.879 | t/ha |
| A | sunflower | Kharif | 3,688 | 26 | 431 | 20 | 0.065 | 0.756 | t/ha |
| A | black_gram | Rabi | 3,469 | 26 | 396 | 18 | 0.062 | 0.57 | t/ha |
| A | green_gram | Rabi | 3,382 | 26 | 441 | 20 | 0.058 | 0.467 | t/ha |
| A | coconut | Whole Year | 3,288 | 26 | 183 | 11 | 0.074 | 8114.983 | nuts/ha |
| A | ginger | Whole Year | 3,225 | 26 | 290 | 16 | 0.066 | 6.624 | t/ha |
| A | sorghum | Rabi | 2,728 | 26 | 225 | 11 | 0.037 | 0.975 | t/ha |
| A | groundnut | Zaid | 2,695 | 26 | 167 | 7 | 0.027 | 1.498 | t/ha |
| A | sunflower | Rabi | 2,681 | 26 | 371 | 17 | 0.074 | 0.847 | t/ha |
| A | chilli | Kharif | 2,655 | 26 | 283 | 13 | 0.029 | 0.93 | t/ha |
| A | potato | Kharif | 2,585 | 25 | 297 | 18 | 0.066 | 8.727 | t/ha |
| A | sugarcane | Kharif | 2,505 | 26 | 265 | 15 | 0.040 | 58.822 | t/ha |
| A | black_gram | Zaid | 2,273 | 24 | 227 | 8 | 0.038 | 0.579 | t/ha |
| A | jute | Kharif | 2,166 | 26 | 200 | 14 | 0.073 | 9.607 | bales_180kg/ha |
| A | horse_gram | Rabi | 2,029 | 26 | 194 | 10 | 0.074 | 0.462 | t/ha |
| B | safflower | Rabi | 1,995 | 26 | 256 | 10 | 0.063 | 0.525 | t/ha |
| B | groundnut | Rabi | 1,985 | 26 | 204 | 12 | 0.029 | 1.747 | t/ha |
| B | arecanut | Whole Year | 1,975 | 26 | 140 | 10 | 0.090 | 1.345 | t/ha |
| B | onion | Zaid | 1,735 | 21 | 138 | 7 | 0.016 | 13.455 | t/ha |
| B | cashew | Whole Year | 1,621 | 26 | 121 | 12 | 0.081 | 0.387 | t/ha |
| B | sweet_potato | Kharif | 1,588 | 20 | 186 | 9 | 0.030 | 11.793 | t/ha |
| B | sunflower | Zaid | 1,520 | 25 | 129 | 5 | 0.032 | 1.093 | t/ha |
| B | paddy | Rabi | 1,444 | 26 | 146 | 11 | 0.046 | 2.745 | t/ha |
| B | sesame | Rabi | 1,367 | 26 | 175 | 10 | 0.074 | 0.406 | t/ha |
| B | coriander | Rabi | 1,359 | 20 | 157 | 8 | 0.051 | 0.571 | t/ha |
| B | garlic | Rabi | 1,357 | 19 | 146 | 6 | 0.064 | 5.355 | t/ha |
| B | onion | Kharif | 1,319 | 25 | 197 | 11 | 0.026 | 9.52 | t/ha |
| B | chilli | Rabi | 1,231 | 26 | 181 | 11 | 0.015 | 2.359 | t/ha |
| B | sesame | Zaid | 1,203 | 23 | 109 | 6 | 0.058 | 0.46 | t/ha |
| B | finger_millet | Rabi | 1,165 | 26 | 176 | 10 | 0.035 | 1.656 | t/ha |
| B | pigeonpea | Rabi | 1,102 | 25 | 143 | 10 | 0.033 | 1.0 | t/ha |
| B | sesame | Whole Year | 1,072 | 24 | 152 | 6 | 0.040 | 0.486 | t/ha |
| B | tobacco | Rabi | 850 | 19 | 175 | 12 | 0.079 | 2.909 | t/ha |
| B | rapeseed_mustard | Kharif | 838 | 22 | 81 | 7 | 0.048 | 0.209 | t/ha |
| B | pearl_millet | Zaid | 729 | 26 | 78 | 4 | 0.034 | 2.385 | t/ha |
| B | pearl_millet | Rabi | 712 | 25 | 107 | 7 | 0.060 | 1.387 | t/ha |
| B | turmeric | Rabi | 659 | 19 | 105 | 7 | 0.033 | 2.833 | t/ha |
| B | cotton | Rabi | 596 | 15 | 115 | 6 | 0.064 | 1.923 | bales_170kg/ha |
| B | maize | Whole Year | 591 | 26 | 156 | 9 | 0.069 | 1.17 | t/ha |
| B | banana | Zaid | 563 | 16 | 72 | 2 | 0.055 | 45.143 | t/ha |
| B | finger_millet | Zaid | 562 | 26 | 51 | 3 | 0.052 | 1.722 | t/ha |
| B | turmeric | Kharif | 538 | 20 | 104 | 8 | 0.065 | 4.5 | t/ha |
| C | castor | Kharif | 4,714 | 26 | 410 | 18 | 0.101 | 0.518 | t/ha |
| C | banana | Whole Year | 4,170 | 26 | 372 | 20 | 0.111 | 20.474 | t/ha |
| C | tobacco | Whole Year | 2,866 | 26 | 311 | 22 | 0.111 | 1.0 | t/ha |
| C | mesta | Kharif | 2,586 | 26 | 270 | 15 | 0.110 | 5.038 | bales_180kg/ha |
| C | tapioca | Whole Year | 2,163 | 26 | 168 | 12 | 0.104 | 13.333 | t/ha |
| C | black_pepper | Whole Year | 1,591 | 26 | 125 | 9 | 0.103 | 0.54 | t/ha |
| C | field_pea | Kharif | 861 | 26 | 117 | 9 | 0.113 | 1.3 | t/ha |
| C | arecanut | Rabi | 498 | 14 | 47 | 3 | 0.088 | 0.815 | t/ha |
| C | sunflower | Whole Year | 428 | 16 | 110 | 8 | 0.068 | 1.0 | t/ha |
| C | banana | Kharif | 417 | 26 | 79 | 6 | 0.065 | 34.083 | t/ha |
| C | castor | Rabi | 410 | 20 | 93 | 7 | 0.063 | 0.566 | t/ha |
| C | cotton | Whole Year | 402 | 17 | 156 | 10 | 0.087 | 1.746 | bales_170kg/ha |
| C | sorghum | Whole Year | 379 | 16 | 67 | 4 | 0.063 | 1.0 | t/ha |
| C | sorghum | Zaid | 357 | 26 | 47 | 3 | 0.039 | 1.804 | t/ha |
| C | tobacco | Kharif | 354 | 20 | 113 | 9 | 0.040 | 1.821 | t/ha |
| C | wheat | Zaid | 348 | 20 | 30 | 1 | 0.046 | 1.361 | t/ha |
| C | chilli | Zaid | 323 | 19 | 36 | 3 | 0.012 | 2.66 | t/ha |
| C | sweet_potato | Rabi | 290 | 18 | 95 | 8 | 0.007 | 11.011 | t/ha |
| C | groundnut | Whole Year | 289 | 19 | 102 | 4 | 0.035 | 1.505 | t/ha |
| C | pigeonpea | Whole Year | 268 | 17 | 99 | 4 | 0.026 | 0.732 | t/ha |
| C | potato | Zaid | 263 | 21 | 40 | 5 | 0.106 | 14.424 | t/ha |
| C | finger_millet | Whole Year | 217 | 16 | 94 | 7 | 0.065 | 1.775 | t/ha |
| C | chickpea | Whole Year | 213 | 12 | 85 | 3 | 0.117 | 0.643 | t/ha |
| C | black_gram | Whole Year | 192 | 9 | 38 | 2 | 0.120 | 0.449 | t/ha |
| C | cashew | Kharif | 182 | 15 | 32 | 3 | 0.110 | 0.373 | t/ha |
| C | lentil | Kharif | 174 | 17 | 87 | 7 | 0.109 | 0.59 | t/ha |
| C | tobacco | Zaid | 156 | 16 | 41 | 2 | 0.000 | 2.604 | t/ha |
| C | niger_seed | Rabi | 154 | 18 | 50 | 4 | 0.039 | 0.5 | t/ha |
| C | chickpea | Kharif | 149 | 25 | 90 | 8 | 0.027 | 0.591 | t/ha |
| C | horse_gram | Zaid | 128 | 21 | 38 | 2 | 0.039 | 0.298 | t/ha |
| C | small_millets | Whole Year | 126 | 11 | 72 | 4 | 0.024 | 0.362 | t/ha |
| C | rapeseed_mustard | Whole Year | 124 | 9 | 85 | 4 | 0.089 | 0.504 | t/ha |
| C | black_pepper | Rabi | 112 | 14 | 14 | 2 | 0.116 | 0.653 | t/ha |
| C | soybean | Rabi | 112 | 11 | 45 | 3 | 0.062 | 1.456 | t/ha |


**Crops not in the catalog** (largest first; candidates to add):

| APY crop | Rows |
|---|---|
| Other Kharif Pulses | 6,575 |
| Other Rabi Pulses | 5,704 |
| Sannhamp | 3,309 |
| Cowpea(Lobia) | 2,525 |
| Guar Seed | 2,483 |
| Khesari | 2,010 |
| Other Cereals | 1,874 |
| Other Oilseeds | 1,717 |
| Moth | 1,626 |
| Other Fresh Fruits | 420 |
| Other Vegetables | 391 |
| Pome Fruit | 297 |

The "Other ..." groups are mixtures and should stay out of the catalog. Cowpea, guar, khesari, moth, sannhamp and korra are real crops and could be added.

## 5. Splits (proposal)

- **Time:** train up to 2015, validation 2016-2018, test 2019-2022.
- **Space:** a fixed hold-out of about 10% of districts (hash of the LGD code), used only as a **spatial test**.
- **Grouping:** all crops of one district-year always share a split (brief rule).
- **Future check:** UPAg 2023-2024 is an optional out-of-time check.

| Split | District-years | Label rows (tiered series) |
|---|---|---|
| train | 10,364 | 213,061 |
| val | 1,892 | 42,056 |
| test | 2,616 | 58,582 |
| spatial_test | 1,377 | 29,350 |

Scalers and imputers will be fitted on train only (Phase 7). Lead-time leakage tests come with the feature pipeline.

## 6. Decisions for the scope freeze

1. **Tier rule:** accept tier v2 (107 series), or v1 (82 series)? Or another cut, for example A + B only (73 series)?
2. **Eastern-state rice seasons:** keep APY's split (aus/aman -> Kharif, boro -> Zaid), follow UPAg (aman -> Rabi), or model rice in those states **annually**? The two sources agree 99.9% annually, so annual is the safest choice.
3. **Splits:** train up to 2015 / validation 2016-2018 / test 2019-2022, plus a 10% spatial district hold-out?
4. **Catalog:** add cowpea, guar, khesari, moth, sannhamp, korra?
5. **ICRISAT DLD:** drop it (APY plus UPAg already cover 1997-2024), or should I request access and resolve the licence first?
6. **Crop calendar:** an agronomist needs to supply crop x state sowing and harvest windows before Phase 7's lead-time windows are final. The current file is season-level and draft.
