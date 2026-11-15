# Phase 8: Yield Baselines and Integration (+F15)

- **Date:** 2026-11-15
- **Runs of record** (all logged in `ml/experiments/`; full per-crop tables are in `ml/reports/data/`):

| Run | What | Run id | Output |
|---|---|---|---|
| Validation | Tuning, selection, conformal calibration | `ab9ba29db405` | `yield_baselines_val_ab9ba29db405.json`; frozen selection `yield_baselines_selection.json` |
| Test | `test` and `spatial_test`, scored **once** for the frozen configuration (selection hash `3fa49bb95ac4`) | `37dc01be91cf` | `yield_baselines_test_37dc01be91cf.json` |
| Export | Serving forecasts for crop year 2026 | `6d86822f3afc` | artifact `ml/artifacts/forecasts/b3-ab9ba29db405-2026-202611150601/` (git-ignored); the first export, `c9b6d46ebc64`, used the long-run normal and is superseded |

**Integrity notes.**
- **Validation only for choices:** every choice (Ridge alpha, LightGBM grid, intervals) was made on validation.
- **Test scored once:** the test script refuses a second test run of the same frozen configuration.
- **Clean-row rule fixed in advance:** the rule for which rows count in the primary metrics was set before any model was scored.
- **Seeds:** LightGBM models use 3 seeds and are reported as mean ± std. B1, B1p and Ridge are deterministic.
- **Phase 7 defaults still apply:** the inputs use the scope-freeze defaults from ADR-026 (still awaiting sign-off). NDVI and soil are **not** in any model yet.

## 1. Setup

- **Target.** Every model predicts the ratio of the yield to the series' own historical mean (a series is one district × crop × season). The prediction in native units is mean × ratio.
  - History uses only years **≤ Y−2**, because APY district figures are published with a delay.
  - Training targets are clipped to [0, 3]. Evaluation always uses the raw yields.
- **Features.**
  - Yield history: trend, last value, coefficient of variation, count, log mean.
  - Season weather at the lead time: raw values and anomalies against district normals fitted on train only.
  - Crop, season and state.
- **Evaluation set.** The same rows for every model: at least 3 prior years and weather available (248,481 rows per lead).
  - **Primary metrics** also drop implausible labels: flagged outliers above the series' history, or more than 10× it. That is 5,240 + 201 rows (about 2.2%).
  - **Low-side outliers stay in:** real crop failures, including zero yields.
  - Metrics on all rows are kept as `A_all` in the JSON.
- **Splits** (rows at each lead):

  | Split | Rows |
  |---|---|
  | train (≤ 2015) | 140,328 |
  | val (2016-18) | 35,899 |
  | test (2019-22) | 50,961 |
  | spatial_test (10% of districts, all years) | 21,293 |

- **Metrics.**
  - Per crop, in native units: MAE, RMSE and R². The primary metric is **nMAE = MAE / mean yield** for that crop.
  - Summarised over the 30 tier-A crops as the **median** and the **worst decile** (90th percentile). Tier B (8 crops) is reported separately.
- **Models.**

  | Model | Description |
  |---|---|
  | B1 | Historical mean (ratio = 1) |
  | B1p | Persistence (latest available year) |
  | B2 | Ridge on all features |
  | **B3** | **One multi-crop LightGBM** (Huber loss) |
  | B4 | LightGBM on weather only, with no yield history |
  | Per-crop | One LightGBM per crop (the RQ5 reference) |

  B4 for vegetation and for soil waits for those data.

## 2. Validation (selection run `ab9ba29db405`)

Tier-A median nMAE (B3 and per-crop are mean of 3 seeds):

| Model | Lead 0 | Lead 30 | Lead 60 | Lead 90 | Worst decile (lead 0) | Tier B (lead 0) |
|---|---|---|---|---|---|---|
| B1 hist mean | 0.2830 | 0.2830 | 0.2830 | 0.2830 | 0.4063 | 0.3860 |
| B1p persistence | 0.2759 | 0.2759 | 0.2759 | 0.2759 | 0.3860 | 0.2639 |
| B2 ridge | 0.2433 | 0.2421 | 0.2422 | 0.2422 | 0.3402 | 0.2840 |
| **B3 lgbm** | **0.2372** | 0.2388 | 0.2377 | 0.2345 | **0.3305** | **0.2482** |
| B4 weather only | 0.2623 | 0.2639 | 0.2609 | 0.2602 | 0.3681 | 0.3524 |
| Per-crop lgbm | 0.2379 | 0.2337 | 0.2347 | 0.2335 | 0.3529 | 0.2652 |

**Selected settings.**
- B3: `num_leaves=127, min_child_samples=50` at every lead.
- Ridge alpha: 10 / 10 / 100 / 1 for leads 0 / 30 / 60 / 90.

**Conformal half-widths** (80%, in ratio units): about **0.48** for tier A and **0.50** for tier B, at every lead. In other words, an 80% interval is roughly **±48% of the series' mean yield**.

## 3. Held-out test (run `37dc01be91cf`, scored once)

**Time test (2019-22)**, tier A:

| Model | Lead 0 median | Lead 0 worst decile | Lead 90 median | Lead 90 worst decile | Tier B (lead 0) |
|---|---|---|---|---|---|
| B1 hist mean | 0.2730 | 0.3691 | 0.2730 | 0.3691 | 0.2778 |
| B1p persistence | 0.2465 | 0.3187 | 0.2465 | 0.3187 | 0.2473 |
| B2 ridge | **0.2363** | 0.3392 | 0.2373 | 0.3354 | 0.2413 |
| **B3 lgbm** | 0.2415 ± 0.0019 | **0.3090 ± 0.0049** | **0.2369 ± 0.0009** | **0.3106 ± 0.0068** | **0.2395** |
| B4 weather only | 0.2583 ± 0.0019 | 0.3671 | 0.2645 | 0.3620 | 0.2796 |
| Per-crop lgbm | 0.2466 ± 0.0012 | 0.3301 | 0.2449 | 0.3334 | 0.2488 |

**Spatial hold-out** (districts never seen in training, all years), tier A:

| Model | Lead 0 median | Lead 0 worst decile | Lead 90 median | Tier B (lead 0) |
|---|---|---|---|---|
| B1 hist mean | 0.2671 | 0.4015 | 0.2671 | 0.2898 |
| B2 ridge | 0.2359 | 0.3308 | 0.2354 | 0.2770 |
| **B3 lgbm** | **0.2226 ± 0.0007** | **0.2940 ± 0.0041** | **0.2222 ± 0.0005** | **0.2153** |
| B4 weather only | 0.2494 | 0.3788 | 0.2552 | 0.3126 |
| Per-crop lgbm | 0.2331 | 0.3024 | 0.2327 | 0.2353 |

The median per-crop R² for B3 is 0.45-0.46 on the time test and 0.55-0.57 on the spatial hold-out; for B1 it is 0.32 and 0.42.

**What this shows.**

1. **B3 beats the historical mean.** On the time test it cuts the median error by about **11-14%** (0.273 → 0.236-0.242) and the worst decile by about 16%. On unseen districts the cut is about **17%** (0.267 → 0.222).
2. **Ridge matches B3 in the median on the time test.** But B3 is clearly better in the worst decile (0.31 vs 0.34) and on unseen districts. B3 therefore stays the serving model, as the brief requires a multi-crop LightGBM first.
3. **RQ5: the shared multi-crop model helps the weaker crops.** On held-out data it is better than per-crop models in the median, the worst decile and tier B on the time test. On unseen districts it is better in the median and similar in the worst decile. On validation, per-crop models had a similar median but a worse worst decile.
4. **Weather alone carries signal** (B4 beats B1 everywhere), **but most of the skill comes from the yield history.** More in-season weather (lead 0 → 90) improves B3 only slightly on the time test (0.2415 → 0.2369) and not on unseen districts. Two likely causes:
   - the draft season-level calendar windows are coarse (ADR-026);
   - NASA POWER at district scale is smooth.

   Crop × state calendars and NDVI are the next things to test (Phase 10).
5. **Persistence is strong on the time test** (0.2465, better than on validation). Ratio-to-history baselines are hard to beat by much at district level, and the improvements above should be read in that light.

## 4. Calibration of the B3 intervals (80% nominal, from validation)

| Lead | Test, tier A | Test, tier B | Test, tier C | Spatial, tier A | Spatial, tier B |
|---|---|---|---|---|---|
| 0 | 0.818 | 0.877 | 0.812 | 0.838 | 0.848 |
| 30 | 0.813 | 0.871 | 0.810 | 0.846 | 0.856 |
| 60 | 0.818 | 0.867 | 0.809 | 0.842 | 0.854 |
| 90 | 0.819 | 0.871 | 0.816 | 0.842 | 0.856 |

Coverage is close to the nominal 80% for tier A, and conservative for tier B and on unseen districts. The intervals are honest but **wide** (about ±48% of normal), which is why the shortfall rule (section 7) requires the whole interval to sit below normal.

## 5. Integration (backend, frontend)

- **`backend/app/forecasting/`:**
  - the `YieldForecast` contract, with checks: tier C must abstain with no number; tier B, a missing modality or an out-of-distribution row must require human review; the interval must contain the forecast;
  - the importer: all-or-nothing, the manifest hash is checked, and importing is idempotent;
  - the service (latest per crop, outlook, shortfalls);
  - providers `baseline-lgbm-batch` (live) and `mock-yield` (tests), selected by `YIELD_PROVIDER`.
- **Migration `0016`** adds two tables only: `yield_forecast_import` and `yield_forecast`.
- **API:**

  | Endpoint | Who |
  |---|---|
  | `GET /forecasting/model` | Readers |
  | `GET /forecasting/forecast` | Farmers (`ADVISORY_READ`) |
  | `GET /forecasting/outlook` | Officers (`ADVISORY_CREATE`) |
  | `POST /forecasting/import` | Officers |

- **Worker job `forecast_import`** (every 6 h), which:
  - imports the newest artifact;
  - raises `agronomy.yield_shortfall_forecast` events for farmers in affected districts;
  - creates **one officer-review advisory draft per district and season** (`source_type=forecast`, status `needs_review`, severity MEDIUM, labelled as a model estimate, not an official figure).

  Nothing is published without the normal Govt Connect review, translation and approval.
- **`YieldShortfallRule`** (proactive engine): matches only the farmer's crop, never tier C, and is HIGH only at a shortfall of 35% or more.
- **`YieldForecastTool`** is registered in the agent runtime.
- **Bot:**
  - Yield questions skip the LLM runtime. They are answered from the imported forecast using fixed en/hi/te templates (numbers filled in by code, never translated), with a "model estimate, not official" notice and a `yield_forecast` card.
  - Tier B is flagged for officer review. An abstention or a missing forecast is stated with no number.
- **Frontend:**
  - officer `YieldOutlookPage` (`/officer/yield`): shortfalls first, abstentions shown as "insufficient data", and a link to the review drafts;
  - `YieldCard` in the farmer chat;
  - farmer `InsurancePage` (`/farmer/insurance`, linked from Govt Updates).
- **F15 insurance helper:**
  - PMFBY added as a **draft** scheme entry;
  - `app/schemes/insurance_guidance.yaml`: premium caps, voluntary enrolment, enrolment cut-offs, 72-hour loss intimation, post-harvest cover, and how claims are assessed. Each item has its source and the date it was checked.
  - Farmers see the guidance only after an officer verifies the PMFBY entry. Until then they see a "pending verification" note and the official portal link.
  - The yield context is always labelled as **not** a YES-TECH, crop-cutting or claim estimate.
- **Tests:**
  - backend: 20 new unit tests (contract, importer, shortfall, rule, tool, insurance helper), 5 conversation tests, and 1 Postgres integration test (`tests/integration/test_phase8_db.py`);
  - frontend: 4 tests;
  - ml: 4 tests (history lag, conformal coverage, per-crop metrics).
- **Full suites pass:** backend 307 (non-integration) + integration 10; frontend 75; ml 30.

## 6. Problems found and fixed in this phase

1. **Three existing bugs in the proactive engine.** Any event that named a district would crash before reaching a rule. Phase 8's shortfall events exercised this path for the first time, and the integration test found it.
   - `get_event_processor` read `runtime_engine.agents`, which doesn't exist; it should be `registry()`.
   - `proactive/context.py` used `District.name` (the column is `district_name`).
   - The same file used `crop.name` (the field is `crop_name`).
2. **Label errors.** A few APY rows are hundreds of times their own series' history (up to 47,271×). They would dominate MAE/RMSE, so they are excluded from the primary metrics by the rule fixed in advance (section 1).
3. **"Normal" that misleads.** The model's reference is the long-run mean since 1997, which understates today's level for crops with a rising trend. Khammam groundnut showed 2.52 t/ha against a "normal" of 1.38 (+83%). The *displayed* normal, which is also what the shortfall test uses, is now the **average of the 5 most recent reported years**. The model and its test metrics are unchanged.

## 7. Serving forecasts for 2026

- **Model:** B3 with the frozen settings, refitted on all labelled rows with the validated number of rounds (351 for Kharif, 354 for Rabi).
- **Weather:** NASA POWER for 1 Jan 2025 - 10 Nov 2026 (100 requests, the same grid and aggregation as training). There is no live Open-Meteo input, so no train/serve skew.
- **Rows:**

  | Target | Forecasts | Abstentions | Flagged for review |
  |---|---|---|---|
  | Kharif 2026, lead 90 | 8,087 | 2,814 | 1,192 |
  | Rabi 2026, lead 30 | 6,656 | 2,218 | 1,777 |

  Abstentions are tier C or too little history.
- **Import into the test database:** 19,775 rows imported. 137 likely shortfalls under the strict rule produced **121 district × season advisory drafts**, all in `needs_review`. There were 0 farmer events because the test database has no farmers in those districts. With the long-run normal, the superseded export gave 48 shortfalls.

## 8. Limitations

- **Serving uses an older history than training.** APY ends at 2022, so for a 2026 forecast the newest history is 4 years old; in training it is always 2. UPAg covers 2023-24 and agrees with APY 97.6% of the time, but it is not used, to avoid mixing sources.
- **Intervals are wide**, and in-season weather adds little (section 3). NDVI is still processing at NASA, and soil is missing.
- **The crop calendar is season-level and draft**, so lead windows are not crop-specific.
- **Telugu-script district names are not resolved** by the rule-based NLU or the LGD index. "ఖమ్మం" gets a "which district?" question, while "Khammam" works. This needs a script-aware alias list (NLU work, not in this phase).
- **The PMFBY guidance is unverified.** The 72-hour intimation window and the 14-day post-harvest cover come from empanelled insurers' guidance; I could not reach an official page for them. Premium caps, voluntary enrolment and cut-off windows match the MyGov PMFBY page, checked on 2026-11-15. Secondary sources mention a revised PMFBY from Kharif 2026 (for example, wild-animal and paddy inundation cover), but I could not confirm it from an official text, so it is not included.
- **The hi/te templates and strings are drafts** pending native review.

## 9. For review

1. **Serving model:** B3, or Ridge? They are equal in the median on the time test, and B3 is better in the worst decile and on unseen districts.
2. **Shortfall threshold:** at least 20% below the recent normal *and* the whole interval below normal. With intervals this wide, the rule is conservative.
3. **Officer verification of the PMFBY entry and guidance:** especially the 72-hour window and the 14-day post-harvest cover against pmfby.gov.in.
4. **Definition of "normal"** shown to farmers: the 5 most recent reported years.
