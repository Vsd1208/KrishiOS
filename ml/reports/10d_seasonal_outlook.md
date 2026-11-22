# Phase 10d: District Seasonal Outlook (interim)

- **Status:** research result on `feat/sprint-11-phase10d-seasonal-outlook`; no product screen yet. Last
  updated 2026-11-22.
- **Question:** before each IMD season, can KrishiOS give each district the chance of below-, near- or
  above-normal rainfall and temperature, better than "one third each"?
- **Answer so far:** yes for **temperature** (clear skill in every season), barely for **monsoon rainfall**,
  and **no** for rainfall in the other seasons. **El Nino / IOD analog years add no skill at district scale.**
- **Role:** a research outlook alongside IMD's official forecasts, never a replacement; an officer approves
  anything before it reaches farmers. Crop suggestions are not built (they need agronomist-reviewed
  calendars).

## Runs of record

| Experiment | Run id | Script | Output |
|---|---|---|---|
| District seasons from IMD grids, 1951-2024 | `c52a27e374f6` | `scripts/build_imd_district_seasons.py` | `district_seasons.parquet` (git-ignored) |
| Dev, El Nino / IOD analogs, 36 settings | `c9c6c9d5f781` | `scripts/run_seasonal_outlook.py --stage dev --grid v1` | `seasonal_outlook_dev_c9c6c9d5f781.json` |
| Dev, analogs vs recent-years normals vs blend, 30 settings | `8f5bc6a3189e` | `... --stage dev --grid v2` | `seasonal_outlook_dev_8f5bc6a3189e.json` |
| **Test, chosen settings, scored once** | `7ffb0cc22c5f` | `... --stage test` | `seasonal_outlook_test_7ffb0cc22c5f.json` |

## 1. Data

IMD gridded daily rainfall (0.25 deg) and Tmax/Tmin (1 deg), 1951-2024, aggregated to **727 LGD districts**
by overlap area: seasonal rainfall total and mean Tmax/Tmin for JJAS (monsoon), OND (post-monsoon), JF
(winter) and MAM (pre-monsoon). A district-season uses only cells with every day present. All-India
district-mean JJAS rainfall per decade: 996 mm (1950s) to 937 mm (2000s, the driest) and 1002 mm (2020s).

## 2. Method and honesty rules

- **No look-ahead:** each target year is forecast from earlier years only (expanding window, from 1981).
  Tercile limits come from those earlier years. Climate indices are read two months before the issue date
  (issue: 1 June for JJAS, 1 October for OND, 1 January for JF, 1 March for MAM).
- **Methods compared:**
  - *Analog:* years in the same ENSO state (ONI, +/-0.5) and optionally the same IOD state (DMI, +/-0.4).
  - *Recent normals ("optimal climate normals"):* how the last 10 or 15 years fell into the terciles.
    This carries trends such as warming.
  - *Blend* of the two.
  Probabilities are shrunk toward 1/3 each (prior strength k) and optionally toward the state mean.
- **Score:** ranked probability skill score (RPSS) against 1/3 each; 0 = no better than climatology.
- **Selection:** settings chosen on **1981-2005** only; **2006-2024** scored once (the script refuses a
  second run).

## 3. Development results (1981-2005)

- **Analogs:** every one of 36 settings scored below climatology (mean RPSS -0.007 to -0.027). The least
  bad was the most shrunk toward 1/3; adding the IOD and detrending temperature both made it worse. Only
  JJAS temperature was positive (+0.03).
- **Recent normals:** positive (best mean RPSS +0.023 with the last 15 years, k = 12, no state mean).
- **Blend:** below recent normals alone, so the analogs add nothing.
- Chosen: recent normals, 15 years, k = 12.

## 4. Test results (2006-2024, scored once)

RPSS against 1/3 each (165,237 district-season forecasts; overall **+0.091**):

| Season | Rainfall | Tmax | Tmin |
|---|---|---|---|
| JJAS (monsoon) | +0.038 | +0.192 | +0.216 |
| OND (post-monsoon) | -0.009 | +0.171 | +0.177 |
| JF (winter) | +0.003 | +0.094 | +0.050 |
| MAM (pre-monsoon) | +0.006 | +0.046 | +0.091 |

**Reliability** (forecast chance of "above normal" against how often it happened):

- **Temperature: under-confident.** JJAS Tmin forecast 0.56 -> observed 0.82; forecast 0.44 -> 0.65.
  Warming ran faster in 2006-2024 than the 1981-2005 tuning assumed; the strong shrinkage (k = 12) holds the
  probabilities too close to 1/3.
- **JJAS rainfall: well calibrated** (forecast 0.21 -> 0.21, 0.43 -> 0.49) but rarely far from 1/3.
- **OND rainfall: no relationship** (observed about 0.3 whatever the forecast).

## 5. What this means for the product

- A **temperature outlook** (e.g. "warmer than usual is likely this kharif") has real, tested skill and could
  be offered to officers, with the probabilities described as conservative.
- **Rainfall:** only the monsoon outlook carries a small signal; for other seasons KrishiOS should say it has
  no reliable seasonal signal and point to IMD's official outlook.
- Farmer messages need officer approval; crop suggestions need agronomist-reviewed calendars first.

## 6. Limits and next steps

- Settings were tuned jointly for rain and temperature; temperature would likely benefit from weaker
  shrinkage. Choosing that needs a fresh, untouched evaluation period (e.g. a rolling-origin design), since
  2006-2024 is now used.
- Index-based predictors were simple categories; dynamical forecasts (IMD/NMME) were not used.
- Next: decide with the project owner whether to build the officer-facing temperature outlook.
