# Phase 10: KrishiOS Yield Model and Research (interim)

- **Status:** in progress on `feat/sprint-11-phase10-yield-research`. Last updated 2026-11-21.
- **Serving model:** unchanged. Forecasts still come from the Phase 8 B3 LightGBM.
- **Test years untouched:** every number below uses the 2016-18 validation years, or forward periods inside
  the training years (2010-12 and 2013-15, each trained only on earlier years). The 2019-22 test split and
  the spatial test have not been scored for any Phase 10 model.
- **Metric:** median nMAE over tier-A crops (lower is better), as in Phase 8, unless a table says otherwise.

## Runs of record

All runs are logged in `ml/experiments/`, and full results are in `ml/reports/data/`.

| Experiment | Run id | Script | Output |
|---|---|---|---|
| MODIS NDVI district processing | `44b6f843e847` | `scripts/process_modis_ndvi.py` | `district_ndvi_monthly.parquet` (git-ignored) |
| NDVI added to B3 (validation) | `3f1421c9270e` | `scripts/run_yield_ndvi.py` | `yield_ndvi_val_3f1421c9270e.json` |
| B5, first version | `58b91d618aaa` | `scripts/run_yield_b5.py` | `yield_b5_val_58b91d618aaa.json` |
| B5, tuned (grid + 3 seeds) | `6df72643cd82` | `scripts/run_yield_b5.py --grid` | `yield_b5_val_6df72643cd82.json` |
| Global + regional climate drivers | `8d35785e0f9f` | `scripts/run_yield_climate.py` | `yield_climate_8d35785e0f9f.json` |
| Permutation tests (20 placebos) | `14ead9935125` | `scripts/run_yield_climate_tests.py` | `yield_climate_tests_14ead9935125.json` |
| River flow vs placebos (20) | `d98038796300` | `scripts/run_yield_river.py` | `yield_river_d98038796300.json` |
| Nepal rainfall vs 99 placebos | `f7fcab8f1033` | `scripts/run_yield_climate_tests.py --nepal-only --placebos 99` | `yield_climate_tests_f7fcab8f1033.json` |
| P1 self-supervised pretraining (5 seeds, Colab T4) | `20f973a599b6` | `scripts/run_yield_p1p2.py --experiment both` | `yield_p1_val_20f973a599b6.json` |
| P2 modality dropout (5 seeds, Colab T4) | `8a577ddc2da2` | `scripts/run_yield_p1p2.py --experiment both` | `yield_p2_val_8a577ddc2da2.json` |
| B5 held-out states (5 groups, 3 seeds) | `34354360f130` | `scripts/run_yield_generalisation.py --model b5 --study states` | `yield_gen_b5_states_34354360f130.json` |
| B3 interval calibration, out of time (3 seeds) | `af450e064e14` | `scripts/run_yield_uncertainty.py` | `yield_uncertainty_af450e064e14.json` |
| B5 unseen crops and 5-shot (10 crops, 3 seeds) | `f5ee494e6440` | `scripts/run_yield_generalisation.py --model b5 --study crops` | `yield_gen_b5_crops_f5ee494e6440.json` |
| Global indices vs 99 placebos | `1463bb39371d` | `scripts/run_yield_climate_tests.py --global-only --placebos 99` | `yield_climate_tests_1463bb39371d.json` |
| B3 held-out states (5 groups, 3 seeds) | `6e6a495c0874` | `scripts/run_yield_generalisation.py --model b3 --study states` | `yield_gen_b3_states_6e6a495c0874.json` |
| B3 year gap, frozen vs refitted (3 seeds) | `bb69dfe28d9a` | `scripts/run_yield_generalisation.py --model b3 --study years` | `yield_gen_b3_years_bb69dfe28d9a.json` |
| B3 unseen crops and 5-shot (30 crops, 3 seeds) | `837b485f9102` | `scripts/run_yield_generalisation.py --model b3 --study crops` | `yield_gen_b3_crops_837b485f9102.json` |

`ef6f04b49792` is a one-epoch smoke run of B5 and is not evidence.

## 1. MODIS NDVI

- **Data:** MOD13A3 monthly 1 km NDVI, 299 months (Feb 2000 to Dec 2024) for all 730 districts, with no
  missing months. Only 0.01% of district-months lack a value. July is the weak month, because monsoon cloud
  leaves about 62.5% of pixels usable, against 96-99% in most other months.
- **Leakage rule:** a month counts only if its end plus 15 days is before the forecast cutoff.
- **Result:** no reliable gain. Averaged over 3 seeds, B3 with NDVI scores 0.2370 / 0.2398 / 0.2375 / 0.2337 at
  leads 0 / 30 / 60 / 90, against 0.2372 / 0.2388 / 0.2377 / 0.2345 without it. The differences are within
  seed variation. Tier B got worse at three of four leads (for example 0.2495 to 0.2614 at lead 60).
- **Signal exists but is redundant:** NDVI alone scores 0.261-0.268, better than the historical mean (0.283)
  but well behind yield history plus weather.

## 2. B5, the shared neural model

- **Design:** a GRU over 15 dekads (10-day steps) of weather and NDVI with availability masks; a static encoder
  for yield history and season anomalies with missingness flags; embeddings for crop, season, state and lead.
  There is no district embedding, so the model can serve unseen districts. One model covers all four leads.
- **Leakage controls:** a forecast at lead L sees only dekads that ended before its cutoff, and NDVI only after
  its publication day. Tests in `ml/tests/test_yield_sequences.py` change future values and check that the
  model input does not change.
- **Result:** B5 does not beat B3. The grid selected hidden 64, dropout 0.3, learning rate 3e-4 and weight decay
  1e-3 on seed 0 (0.2356), but the three-seed average was 0.2384 against 0.2371 for B3. It is clearly worse on
  the hardest crops (worst decile about 0.358 against 0.331) and on tier B (about 0.28 against 0.25). It
  overfits within a few epochs.

| Lead | B5 median | B3 median | B5 worst decile | B3 worst decile |
|---|---|---|---|---|
| 0 | 0.2402 | 0.2372 | 0.3580 | 0.3305 |
| 30 | 0.2380 | 0.2388 | 0.3585 | 0.3338 |
| 60 | 0.2380 | 0.2377 | 0.3585 | 0.3311 |
| 90 | 0.2373 | 0.2345 | 0.3560 | 0.3301 |

## 3. Large-scale and regional climate drivers

The hypothesis, from the project owner, is that yields depend on conditions far from the farm. Each region
gets the remote drivers that physically relate to it:

| Region (states) | Drivers routed to it |
|---|---|
| North-west (Punjab, Chandigarh, Haryana, Rajasthan) | 200 hPa westerlies over the Middle East and Central Asia, 500 hPa height over Central Asia (western disturbances) |
| Western Himalaya (J&K, Ladakh, Himachal, Uttarakhand) | The same westerlies, plus western Tibetan Plateau temperature at 500 hPa |
| Ganga east (Uttar Pradesh, Bihar) | GPCP rainfall over Nepal (upstream rivers) |
| North-east (Assam, Sikkim and the north-eastern states) | Eastern Tibet and Himalaya temperature (stand-in for snow and glacier melt), rainfall over the upper Brahmaputra |
| All India | Somali jet, tropical easterly jet, Bay of Bengal and Arabian Sea OLR and SST, equatorial Indian Ocean SST, plus the indices below |

- **Global indices:** Niño 3.4 (satellite OISST), Indian Ocean Dipole, equatorial OLR, Southern Oscillation and
  Tropical North Atlantic, each as latest value, 3-month mean and 3-month change.
- **Regional drivers:** monthly box means from NOAA PSL subsets, as anomalies against 1982-2009 normals
  (before the first evaluation period).
- **Publication lag:** 30 days for most series, 90 days for GPCP rainfall.
- **Evaluation:** forward chaining over 2010-12, 2013-15 and 2016-18, with a placebo that feeds the same values
  from the wrong years.

Average over 12 period x lead combinations (run `8d35785e0f9f`, 3 seeds):

| Model | Median nMAE | Worst decile | Wins vs B3 (of 12) |
|---|---|---|---|
| B3 | 0.2376 | 0.3390 | n/a |
| B3 + global indices | 0.2365 | 0.3289 | 7 |
| B3 + global + regional | 0.2369 | 0.3278 | 8 |
| Placebo (wrong years) | 0.2380 | 0.3317 | 5 |

Permutation test with 20 placebos (run `14ead9935125`; ratio MAE on clean tier A/B rows):

| Region | B3 | + all drivers | Placebo mean | p (all drivers) | + Nepal rain only | p (Nepal) |
|---|---|---|---|---|---|---|
| Uttar Pradesh, Bihar | 0.2554 | 0.2425 | 0.2465 | 0.048 | 0.2426 | 0.048 |
| North-west | 0.3815 | 0.3693 | 0.3728 | 0.14 | 0.3736 | 0.62 |
| Western Himalaya | 0.2866 | 0.2854 | 0.2875 | 0.095 | 0.2855 | 0.38 |
| North-east | 0.1785 | 0.1802 | 0.1799 | 0.71 | 0.1799 | 0.38 |
| All India | 0.3106 | 0.3064 | 0.3080 | 0.095 | 0.3068 | 0.048 |

**Reading.**
- The best evidence was Nepal rainfall for Uttar Pradesh and Bihar: it beat all 20 placebos. With 20 placebos,
  0.048 is the smallest p-value possible, and five regions were checked, so the pre-set bar is 0.01. The
  99-placebo check below does not clear that bar.
- The gain is not uniform: weak in 2010-12, and at lead 90 Nepal rain made 2013-15 and 2016-18 slightly worse.
- In the latest period (2016-18) the regional model was worse than B3 at leads 60 and 90.
- The north-east shows no gain. Tibetan heat is only a stand-in for melt, and flood data was not yet included.
- Nothing from this section is served.

**Nepal rainfall, 99 placebos** (run `f7fcab8f1033`; only the Nepal inputs move to wrong years, global
indices stay real; ratio MAE):

| Region | Global only | + Nepal rain | Placebo mean | Best placebo | p |
|---|---|---|---|---|---|
| Uttar Pradesh, Bihar | 0.2445 | 0.2426 | 0.2442 | 0.2417 | 0.05 |
| North-west | 0.3742 | 0.3736 | 0.3731 | 0.3714 | 0.69 |
| Western Himalaya | 0.2858 | 0.2855 | 0.2858 | 0.2849 | 0.37 |
| North-east | 0.1791 | 0.1799 | 0.1800 | 0.1791 | 0.38 |
| All India | 0.3074 | 0.3068 | 0.3072 | 0.3065 | 0.10 |

Four of 99 wrong-year placebos did as well as real Nepal rainfall for Uttar Pradesh and Bihar, so p = 0.05.
That misses the pre-set 0.01 bar (five regions, Bonferroni). The gain is about 0.8% of the error. The result
is suggestive, not proven, and Nepal rainfall is not used in the served model. Nepal rainfall did not help any
region it was not routed to, as expected.

**Global indices on their own, 99 placebos** (run `1463bb39371d`; ENSO, IOD, OLR, SOI and TNA move to
wrong years together; only B3 and B3 + global indices are fitted; ratio MAE):

| Region | B3 | + global indices | Placebo mean | Best placebo | p |
|---|---|---|---|---|---|
| Uttar Pradesh, Bihar | 0.2554 | 0.2445 | 0.2474 | 0.2422 | 0.12 |
| North-west | 0.3815 | 0.3742 | 0.3730 | 0.3658 | 0.64 |
| Western Himalaya | 0.2866 | 0.2858 | 0.2862 | 0.2835 | 0.36 |
| North-east | 0.1785 | 0.1791 | 0.1792 | 0.1780 | 0.54 |
| All India | 0.3106 | 0.3074 | 0.3081 | 0.3058 | 0.19 |

- **No region passes the 0.01 bar.** Most of the drop from adding the indices also appears with
  wrong-year indices: in Uttar Pradesh and Bihar real indices cut the error by 0.011, wrong-year ones
  by 0.008 on average. The gain is mostly from extra inputs the trees can split on, not from the
  real year-to-year climate signal.
- With the Nepal result above (p = 0.05), no climate driver tested in Phase 10 is proven to add skill
  to district yield forecasts. None is served. These indices remain the planned inputs of the
  Phase 10d seasonal rainfall and temperature outlook, a different question.
- Blocks 1-4 of this test ran with 12 LightGBM threads and blocks 5-12 with 6 (laptop thermal limit).
  LightGBM results with the same seed can differ slightly across thread counts.

## 4. River flow: no measurable skill

Modelled daily discharge from Copernicus GloFAS (through the Open-Meteo Flood API, non-commercial use) at 13
main-channel points for 1990-2024: Ghaghara, Rapti, Gandak, Kosi, the Ganga at Varanasi and Patna, the
Brahmaputra at Pasighat, Dibrugarh, Tezpur and Guwahati, and the Jhelum, Chenab and Sutlej. Several first
coordinates fell on side channels with near-zero flow; they were moved to the main-channel grid cell using 2015
mean flow. Monthly mean and highest-day flow are used as anomalies, a month only after a 30-day lag, and routed
to the regions each river affects. The test compares real flow with 20 wrong-year placebos while keeping the
global indices real. These are model estimates, and dams and barrages may not be fully represented.

Result (run `d98038796300`, ratio MAE; global indices real in every model):

| Region | Global only | + rivers | Placebo mean | p (rivers) |
|---|---|---|---|---|
| Uttar Pradesh, Bihar | 0.2445 | 0.2438 | 0.2440 | 0.48 |
| North-west | 0.3742 | 0.3738 | 0.3731 | 0.62 |
| Western Himalaya | 0.2858 | 0.2863 | 0.2870 | 0.33 |
| North-east | 0.1791 | 0.1803 | 0.1804 | 0.48 |
| All India | 0.3074 | 0.3072 | 0.3072 | 0.52 |

Real river flow did no better than flow taken from the wrong years in any region. A likely reason is the
30-day publication lag: at the season-start forecast, the flood months of the same season are not yet
visible. River inputs are not used further.

## 5. P1 self-supervised pretraining and P2 modality dropout

Both ran on a Colab T4 from `notebooks/phase10_yield_colab.ipynb`, with a bundle that holds only
the training and validation years (`notebooks/make_colab_bundle.py --yield`). A local check from the
same bundle reproduced the full-data scores exactly. B5 uses the settings chosen by its grid search
(hidden 64, dropout 0.3). Metric: mean over leads of tier-A median nMAE on 2016-18, 5 seeds.

**P1.** The GRU over weather and NDVI was pretrained on training-year inputs without yields
(masked reconstruction, cross-modal prediction, or both), then fine-tuned on a share of the training
district-seasons with the same number of optimizer steps (run `20f973a599b6`):

| Pretraining | 10% of labels | 25% | 50% | 100% |
|---|---|---|---|---|
| None | 0.2405 ± 0.0033 | 0.2386 ± 0.0019 | 0.2367 ± 0.0009 | 0.2359 ± 0.0010 |
| Masked reconstruction | 0.2410 | 0.2389 | 0.2368 | 0.2361 |
| Cross-modal prediction | 0.2407 | 0.2386 | 0.2365 | 0.2360 |
| Both | 0.2410 | 0.2392 | 0.2370 | 0.2364 |

- **Pretraining did not help (RQ1: no).** Every variant is within 0.0007 of no pretraining, inside the
  seed spread, and no variant beats it in more than 3 of 5 seeds at any label share.
- **The model needs few labels.** With 10% of the training labels it is only about 2% worse than with
  all of them. The static yield history carries most of the signal, which leaves little for a better
  sequence encoder to add.

**P2.** Weather, NDVI and yield history were each hidden for a sample with probability 0.25 during
training, and the models were scored with inputs missing (run `8a577ddc2da2`):

| Inputs at forecast time | No dropout | With dropout | Difference (seeds better) | Worst decile, no dropout / with | Tier B, no dropout / with |
|---|---|---|---|---|---|
| All | 0.2359 | 0.2390 | +0.0032 (0 of 5) | 0.3571 / 0.3595 | 0.2748 / 0.2813 |
| No NDVI | 0.2357 | 0.2367 | +0.0010 (1 of 5) | 0.3527 / 0.3559 | 0.2675 / 0.2743 |
| No weather | 0.2434 | 0.2422 | -0.0012 (3 of 5) | 0.3406 / 0.3584 | 0.2578 / 0.2754 |
| No yield history | 0.2726 | 0.2691 | -0.0035 (4 of 5) | 0.3842 / 0.3827 | 0.3754 / 0.3661 |
| History only | 0.2489 | 0.2386 | -0.0103 (4 of 5) | 0.3390 / 0.3508 | 0.2482 / 0.2618 |

- **Dropout trades full-input accuracy for robustness (RQ3).** It costs 0.0032 when all inputs are
  present and helps most when only yield history is left. It is worth using only where inputs are
  often missing at forecast time.
- **NDVI adds nothing to B5**, as with B3 in section 1: removing it changes the median by 0.0002.
- **Weather hurts the hardest crops in B5.** Without weather, the worst decile improves from 0.357 to
  0.341 and tier B from 0.275 to 0.258, at a small cost in the median. The sequence encoder appears
  to overfit for the difficult crops; B3 (worst decile about 0.331, tier B about 0.25) handles them better.
- **B5 still does not replace B3.** Its median (0.2359) is close to B3's (0.2371), but B3 remains
  better on the worst decile and tier B. Nothing from this section is served.

## 6. Held-out states and years (RQ4) and unseen crops (RQ5)

States were split into 5 groups balanced by rows. For each group B5 was trained without those
states and scored on their 2016-18 rows; the comparison model saw them. Both stopped early on the
other states' rows only (run `34354360f130`, mean over leads, 3 seeds):

| | State seen | State never seen | Change |
|---|---|---|---|
| Tier A median nMAE | 0.2410 | 0.2421 | +0.0011 |
| Tier A worst decile | 0.362 | 0.375 | +0.013 |
| Tier B median nMAE | 0.276 | 0.325 | +0.049 |

For tier-A crops B5 transfers to unseen states almost without loss; tier-B crops, with little data,
lose about 18%.

**B3 on the same state groups** (run `6e6a495c0874`, mean over leads, 3 seeds):

| | State seen | State never seen | Change |
|---|---|---|---|
| Tier A median nMAE | 0.2369 | 0.2415 | +0.0046 |
| Tier A worst decile | 0.333 | 0.354 | +0.021 |
| Tier B median nMAE | 0.251 | 0.341 | +0.090 |

B3 is better than B5 where the state was seen, but loses more in unseen states (tier B +36%
against +18% for B5). Unseen states end up about level between the two for tier A (0.2415 against
0.2421).

**Year gap** (run `bb69dfe28d9a`): a B3 model frozen with data up to 2009, against one refitted on
all years before each period (3 seeds):

| Period | Tier A frozen | Tier A refitted | Worst decile frozen | Worst decile refitted |
|---|---|---|---|---|
| 2010-12 | 0.2277 | 0.2277 | 0.298 | 0.298 |
| 2013-15 | 0.2471 | 0.2519 | 0.371 | 0.361 |
| 2016-18 | 0.2501 | 0.2415 | 0.375 | 0.352 |

For 2010-12 both models are the same model. Three and six years on, the frozen model is first
level (better median, worse worst decile), then clearly behind on both. **Refit the model at least once a
year**, when each season's new APY labels arrive.

**Unseen crops (RQ5, B5).** Ten tier-A crops, fixed before any result (every third crop ordered by
districts), each removed from training (k = 0) or kept for only 5 random districts (k = 5), and
scored on its own 2016-18 rows. All models stopped early on the other crops' rows (run
`f5ee494e6440`, 3 seeds; each crop's own nMAE):

| | Median over the 10 crops | Crops better than the district historical mean |
|---|---|---|
| District historical mean | 0.283 | n/a |
| B5, crop seen in training | 0.245 | 10 of 10 |
| B5, crop never seen | 0.249 | 9 of 10 |
| B5, crop seen in 5 districts | 0.251 | 9 of 10 |

- **The shared model transfers to crops it never saw**, losing about 2%, and still beats the
  historical mean for 9 of 10 crops (for example sesame 0.505 against 0.790, chilli 0.322 against
  0.405, sugarcane 0.216 against 0.282). The exception is soybean (0.231 against 0.228).
- **Five districts of data add nothing** over none: forecasting the ratio to each district's own
  history already carries most of what is crop-specific.
- RQ5 answer for B5: yes, a shared multi-crop model helps crops with little or no data.

**B3 on all 30 tier-A crops** (run `837b485f9102`, 3 seeds; leads 0 and 60 only, to keep the 60 fits
per seed affordable on the laptop):

| | Median, 30 crops | Median, B5's 10 crops | Crops better than the historical mean |
|---|---|---|---|
| District historical mean | 0.283 | 0.283 | n/a |
| B3, crop seen in training | 0.236 | 0.239 | 28 of 30 |
| B3, crop never seen | 0.250 | 0.252 | 28 of 30 |
| B3, crop seen in 5 districts | 0.248 | 0.248 | 28 of 30 |

- B3 also transfers to unseen crops and beats the historical mean for 28 of 30 (not for finger
  millet and soybean, both about level).
- On the same 10 crops, **B3 loses about 5% when a crop is unseen; B5 loses about 2%.** For
  never-seen crops the two are close (B3 0.252, B5 0.249), with different lead sets. B5's advantage
  for new crops is small.

## 7. Forecast ranges: calibration per tier

Widths were fitted on 2013-15 forecasts (model trained up to 2010) and checked on 2016-18 forecasts
(model trained up to 2013), so the checked years never set the widths (run `af450e064e14`, B3,
3 seeds; "crops close" = share of crops within 10 points of the target):

| Target | Tier A coverage | Tier A crops close | Tier B coverage | Tier B crops close |
|---|---|---|---|---|
| 50% | 51% | 71% | 47% | 40% |
| 80% | 80% | 90% | 73% | 42% |
| 90% | 90% | 89% | 84% | 67% |

- **Tier A is well calibrated** with the per-tier widths served since Phase 8.
- **Tier B ranges are too narrow** and uneven across crops. Per-crop widths and widths scaled by
  district variability do not fix it (the scaled version mostly widens every range).
- The ranges are wide: a tier-A 80% range spans about +/-48% of the district's usual yield.
- **No change to the widths.** Phase 8 already scored the served ranges once on the test years
  (run `37dc01be91cf`): tier-B 80% ranges covered about 87% in 2019-22 (85-86% on the spatial test),
  so there they were too wide, not too narrow. Tier B misses in opposite directions in different
  periods (73% in 2016-18, 87% in 2019-22): its calibration is unstable rather than biased one way.
  Widening it now would be tuned against a result already known from the test years. Tier-B ranges
  stay as served and are described as approximate; tier A (81-82% on test) is reliable.

## 8. Remaining Phase 10 work

All validation studies are done. What is left:

1. Fix the best configuration from the validation results above and score it on the 2019-22 test
   years once.
2. Swap it in behind the yield provider only if it beats B3 there. On validation no Phase 10
   variant (NDVI, B5, climate drivers, pretraining, modality dropout) beats plain B3 for tier-A
   crops with all inputs. B5's possible value is narrow: missing inputs (P2) and crops without data
   (RQ5).
