# KrishiOS Next Level: Roadmap

The Sprint 11 plan, phase by phase, with what each phase must deliver and where it stands. Each phase runs on
its own branch from `main` and stops for review before the next starts. Status details and test counts are in
[`PROGRESS.md`](PROGRESS.md); the reasons behind each choice are in [`DECISIONS.md`](DECISIONS.md). Last updated
2026-11-21.

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
| 10c KrishiOS AI assistant | Local open language model (4-bit, chosen by a Hindi/Telugu/English agriculture bake-off), fine-tuned on Kisan Call Centre Q&A; answers grounded in vetted documents (RAG) with citations and abstention; uploaded-document analysis: a structured brief for officers, a plain-language summary with actions for farmers; replaces the mock local LLM | Built, under review (`ml/reports/10c_ai_assistant.md`): on-device Qwen2.5-7B, vetted-guide RAG with citations and declines, document briefs/summaries; KCC fine-tune not done |
| 10d Seasonal weather outlook | IMD 1951-2024 rainfall and temperature; El Nino / IOD analog-year outlook per district (chance of below, near and above normal) for kharif, rabi and zaid, scored against one-third each; crop suggestions from agronomist-reviewed calendars; officer approval before farmers see it; shown alongside IMD's official forecasts | To do (data downloading) |
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
| Global indices alone vs 99 placebos | Done: no region passes (best p = 0.12); not used | Run `1463bb39371d` |
| River-flow drivers (GloFAS, 13 points) | Done: no measurable skill | Run `d98038796300` |
| 99-placebo check for Nepal rainfall | Done: p = 0.05, misses the 0.01 bar; not used | Run `f7fcab8f1033` |
| P1 pretraining with label-efficiency curves | Done: no gain at any label share (5 seeds) | Run `20f973a599b6` |
| P2 modality dropout per missing-input condition | Done: helps when inputs are missing, costs 0.003 with all inputs | Run `8a577ddc2da2` |
| Held-out states and years | Done: tier A transfers to unseen states (B3 0.237 to 0.241, B5 0.241 to 0.242); tier B worse; refit yearly | Runs `34354360f130`, `6e6a495c0874`, `bb69dfe28d9a` |
| Leave-one-crop-out and k-shot transfer | Done: never-seen crops beat the historical mean (B3 28 of 30, B5 9 of 10); 5-shot adds nothing | Runs `f5ee494e6440`, `837b485f9102` |
| Uncertainty and calibration per tier | Done: tier A calibrated; tier B unstable, widths unchanged | Run `af450e064e14` |
| Single test scoring of the frozen best model; serving swap if better | To do | |

The full results are in [`ml/reports/10_yield_research.md`](../ml/reports/10_yield_research.md).

## Parallel tracks

- **Indian field photos for vision:** 4,281 checked photos of potato, chilli, tomato, soybean and wheat (4.26 GB
  of the 5 GB limit). The independent test (run `07389f462bb7`) found the current model mistakes wheat for
  maize and chilli for tomato, so crop auto-accept is now off. Next: retrain with these photos.
- **Heavier experiments:** full satellite-map models and many-seed runs may be prepared as Colab notebooks with
  public or project research data only.

## Waiting on people

- Scope-freeze sign-off for crop tiers and windows (ADR-026).
- Native review of Hindi and Telugu text.
- Officer verification of PM-KISAN and PMFBY content.
- Agronomist-reviewed crop calendars.
