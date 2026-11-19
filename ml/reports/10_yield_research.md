# Phase 10: KrishiOS Yield Model and Research (interim)

- **Status:** in progress on `feat/sprint-11-phase10-yield-research`. Last updated 2026-11-19.
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
| Nepal rainfall vs 99 placebos | running | `scripts/run_yield_climate_tests.py --nepal-only --placebos 99` | pending |

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
- The best evidence is Nepal rainfall for Uttar Pradesh and Bihar: it beat all 20 placebos. With 20 placebos,
  0.048 is the smallest p-value possible, and five regions were checked, so the pre-set bar is 0.01. Proving it
  needs at least 99 placebos.
- The gain is not uniform: weak in 2010-12, and at lead 90 Nepal rain made 2013-15 and 2016-18 slightly worse.
- In the latest period (2016-18) the regional model was worse than B3 at leads 60 and 90.
- The north-east shows no gain. Tibetan heat is only a stand-in for melt, and flood data was not yet included.
- Nothing from this section is served.

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

## 5. Remaining Phase 10 work

1. Finish the 99-placebo check for Nepal rainfall in Uttar Pradesh and Bihar (running).
2. Experiment P1: self-supervised pretraining (masked reconstruction and cross-modal prediction, each ablated),
   with label-efficiency curves.
3. Experiment P2: modality dropout, scored per missing-input condition.
4. Held-out states and held-out years (RQ4).
5. Leave-one-crop-out and k-shot transfer (RQ5).
6. Uncertainty with a calibration check per tier.
7. Ablations with at least 3 seeds; then score the frozen best configuration on test once, and swap it in
   behind the yield provider only if it beats B3.
