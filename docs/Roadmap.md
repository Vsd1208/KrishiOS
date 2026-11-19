# KrishiOS Next Level: Roadmap

The Sprint 11 plan, phase by phase, with what each phase must deliver and where it stands. Each phase runs on
its own branch from `main` and stops for review before the next starts. Status details and test counts are in
[`PROGRESS.md`](PROGRESS.md); the reasons behind each choice are in [`DECISIONS.md`](DECISIONS.md). Last updated
2026-11-19.

## Principles that apply to every phase

- One shared crop catalog and LGD directory for yield, vision, NLP and retrieval; no hard-coded crop strings.
- Yield forecasts are district x crop x season, multi-crop, India only, and never presented as field-level.
- Crop tiers decide what is served: tier A is evaluated per crop, tier B is served with wide uncertainty, tier C
  abstains.
- Uncertain AI output is never presented as certain: the farmer confirms the crop, findings are possibilities,
  outbreak alerts and shortfall advisories reach farmers only after an officer approves them.
- Offline, open-source models; farmer data stays on our own system.
- Every reported number has a run id; choices are made on validation; each test set is scored once.

## Phases

| Phase | Goal and deliverables | Status |
|---|---|---|
| 0 Orientation & sourcing | Audit the codebase; source models, government data and licences | Done |
| 1 Foundations | Fix the test baseline; provider selection; crop catalog; LGD directory; worker service | Done |
| 2 Multilingual core | Real STT, TTS and translation chosen by bake-off on te/hi | Done |
| 3 Multilingual bot | NLU, dialogue state, voice turns; F6 extension-worker mode, F7 verified media, F13 answer feedback | Done, in review |
| 4 Govt Connect: publishing | Officer console, bulletin extraction, translation, targeted delivery, inbox; F2 block locations, F4 schemes and grievances | Done, in review |
| 5 Govt Connect: automated | Scheduled official feeds, weather cross-check, mandi prices, push; F1 DPI adapters, F3 offline PWA, F5 SMS/IVR/WhatsApp | Done, in review |
| 6 Yield label audit | APY and UPAg labels, crop catalog entries, tiers and splits | Done, awaiting scope freeze |
| 7 Yield predictor pipeline | District weather, vegetation and soil features with leak-safe lead windows | Done (soil unavailable) |
| 8 Yield baselines | B1-B4 and per-crop LightGBM; batch export and import; outlook page and bot card; shortfall drafts; F15 insurance helper | Done, in review |
| 9 Real computer vision | Crop ID and disease models in ONNX; crop confirmation; photo to crop to yield, advice and bulletins; field-photo evaluation; F8 outbreak heatmaps | Done, merged |
| 10 KrishiOS yield model | B5 shared model; P1 self-supervised pretraining; P2 modality dropout; held-out states and years; leave-one-crop-out and k-shot transfer; calibrated uncertainty per tier; ablations; serve the best model if it beats B3 | **In progress** |
| 10b Farmer toolkit | F9 Soil Health Card reader and fertilizer calculator, F10 crop calendar and reminders, F11 mandi insights, F12 community Q&A, F14 livestock and fisheries, F7 video queries | To do |
| 11 Golden journeys and docs | End-to-end journeys, the remaining docs, the write-up | To do |

## Phase 10 in detail

Research questions: RQ1 self-supervised pretraining, RQ2 fusion against single inputs, RQ3 modality dropout,
RQ4 held-out states and years, RQ5 whether a shared multi-crop model helps low-data crops.

| Step | Status | Evidence |
|---|---|---|
| MODIS NDVI processed and tested in B3 | Done: no reliable gain | Runs `44b6f843e847`, `3f1421c9270e` |
| B5 shared neural model (dekad timeline, masks, crop, season, state and lead embeddings) | Done: does not beat B3 yet | Runs `58b91d618aaa`, `6df72643cd82` |
| Global and region-routed climate drivers | Done: partial support | Run `8d35785e0f9f` |
| Permutation tests, including Nepal rainfall for Uttar Pradesh and Bihar | Done with 20 placebos: promising, not proven | Run `14ead9935125` |
| River-flow drivers (GloFAS, 13 points) | Done: no measurable skill | Run `d98038796300` |
| 99-placebo check for Nepal rainfall | Running | |
| P1 pretraining with label-efficiency curves | To do | |
| P2 modality dropout per missing-input condition | To do | |
| Held-out states and years | To do | |
| Leave-one-crop-out and k-shot transfer | To do | |
| Uncertainty and calibration per tier | To do | |
| Single test scoring of the frozen best model; serving swap if better | To do | |

The full results are in [`ml/reports/10_yield_research.md`](../ml/reports/10_yield_research.md).

## Parallel tracks

- **Indian field photos for vision:** a resumable, size-limited sample (5 GB overall) of potato, chilli, tomato,
  soybean and wheat field photos. When complete: an independent field test of the current model, then retraining.
- **Heavier experiments:** full satellite-map models and many-seed runs may be prepared as Colab notebooks with
  public or project research data only.

## Waiting on people

- Scope-freeze sign-off for crop tiers and windows (ADR-026).
- Native review of Hindi and Telugu text.
- Officer verification of PM-KISAN and PMFBY content.
- Agronomist-reviewed crop calendars.
