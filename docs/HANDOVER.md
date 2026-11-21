# KrishiOS: Team Handover

Start here. This file says what KrishiOS is, the plan, what has been built so far, where each piece lives and
what comes next. Last updated 2026-11-19.

## 1. In one paragraph

KrishiOS is an AI system for Indian agriculture: a multilingual farmer assistant (Telugu, Hindi, English, text
and voice), a Govt-Farmer Connect channel for official bulletins, schemes and grievances, district-level yield
forecasts, and offline crop and disease recognition from photos. It is a **non-commercial academic research
project**. Work is organised as "Sprint 11: KrishiOS Next Level", Phases 0-11 with features F1-F15. Phases 0-9
are merged to `main`; Phase 10 is in progress.

## 2. Where to read

| You want | Read |
|---|---|
| Phase status, features, test counts | [`docs/PROGRESS.md`](PROGRESS.md) |
| The full plan, phase by phase | [`docs/Roadmap.md`](Roadmap.md) |
| Why things are built the way they are (ADR-001 to ADR-028) | [`docs/DECISIONS.md`](DECISIONS.md) |
| Evidence for each phase, with run ids | [`ml/reports/`](../ml/reports) (`00_` to `10_`) |
| Every dataset, its licence and status | [`ml/DATA_SOURCES.md`](../ml/DATA_SOURCES.md) |
| Running the platform and the tests | [`README.md`](../README.md#-running-krishios-locally) |

`docs/AI.md`, `API.md`, `Architecture.md`, `Database.md` and `PRD.md` are still empty placeholders; Phase 11
fills them.

## 3. Repository layout

| Path | What it holds |
|---|---|
| `backend/` | FastAPI app, Alembic migrations (through `0017`), arq worker jobs, providers, tests |
| `frontend/` | React 19 + TypeScript + Vite app (farmer and officer workspaces), i18n en/hi/te |
| `ml/` | Separate `uv` project: data pipelines, training, evaluation, reports, experiment logs |
| `ml/reference/` | Single source of truth for crops (`crop_catalog.csv`) and LGD codes (ADR-008) |
| `ml/experiments/*.jsonl` | One record per run: config, metrics, run id |
| `ml/reports/` | Phase reports; `ml/reports/data/` holds full results per run |
| `docs/` | Progress, decisions, this handover and the roadmap |

The backend only loads exported artifacts from `ml/artifacts/` (git-ignored); it never trains (ADR-001).

**Everything is kept inside the project folder, so it can be moved as one folder.** Git-ignored
parts that are not on GitHub:

| Path | What it holds |
|---|---|
| `ml/data/` | Raw and processed data (yield labels, weather, MODIS, IMD, Indian field photos) |
| `ml/artifacts/` | Trained models (vision ONNX, yield runs) |
| `models_cache/huggingface/` | Downloaded open models (IndicTrans2, IndicConformer, MMS-TTS, Whisper, BioCLIP and others). Both `backend/app` and `krishios_ml` use it automatically when it exists |
| `backups/` | Docker volume archives (Postgres, Neo4j, Qdrant, Redis, documents); restore steps in `backups/README.md` |

After moving the folder, rebuild the environments: `uv sync` in `backend/` and `ml/`, and `npm ci`
in `frontend/` (the `.venv` and `node_modules` folders are tied to the old paths).

## 4. What has been built

| Phase | Delivered | Report |
|---|---|---|
| 0 Orientation | Current-state audit; sourcing of models, government data and licences | [00](../ml/reports/00_orientation.md) |
| 1 Foundations | Green test baseline, fail-loud provider selection, crop catalog, LGD directory, worker service | [01](../ml/reports/01_foundations.md) |
| 2 Multilingual core | STT, TTS and translation bake-offs on te/hi; IndicConformer and IndicTrans2 chosen | [02](../ml/reports/02_multilingual_core.md) |
| 3 Multilingual bot (F6, F7, F13) | NLU, dialogue state with clarify-and-resume, extension-worker mode, verified media, answer feedback | [03](../ml/reports/03_multilingual_bot.md) |
| 4 Govt Connect publishing (F2, F4) | Officer console, extraction with provenance, translation gates, targeted delivery, farmer inbox, grievances, schemes | [04](../ml/reports/04_govconnect_publishing.md) |
| 5 Govt Connect automated (F1, F3, F5) | NDMA SACHET feeds, weather cross-check, mandi prices, SMS/IVR/WhatsApp sandboxes, offline PWA, DPI adapters | [05](../ml/reports/05_govconnect_automated.md) |
| 6 Yield label audit | APY + UPAg district yield labels, crop tiers, splits | [06](../ml/reports/06_yield_label_audit.md) |
| 7 Yield predictors | NASA POWER district weather, polygon crosswalk, leak-safe lead-time features, MODIS NDVI pipeline | [07](../ml/reports/07_yield_predictor_pipeline.md) |
| 8 Yield baselines (F15) | B1-B4 baselines; B3 multi-crop LightGBM served; outlook page, bot yield card, shortfall drafts, insurance helper | [08](../ml/reports/08_yield_baselines.md) |
| 9 Real vision (F8) | Offline EfficientNet-B0 crop + disease model (ONNX), crop confirmation, photo turns, BioCLIP comparison, outbreak heatmaps | [09](../ml/reports/09_vision.md) |
| 10 Yield research | **In progress:** NDVI, B5 neural model, climate and river drivers | [10](../ml/reports/10_yield_research.md) |

### Headline numbers (all from logged runs)

- **Yield (Phase 8, B3):** test median nMAE 0.236-0.242 against 0.273 for the historical mean; unseen districts
  0.222 against 0.267 (run `37dc01be91cf`).
- **Vision (Phase 9):** crop accuracy 86.0% on PlantDoc (web field-proxy photos), 98.9% on India rice field
  photos; disease accuracy 79.4% on field photos when the crop is known; BioCLIP zero-shot reaches 64.7% crop and
  49.2% disease (runs `560b033f785d`, `75a953a61436`). After field recalibration, auto-accepted crops on PlantDoc
  are 97.8% correct (run `6e5a127ea6ea`). Auto-accept is enabled only for paddy, tomato, maize and grapes.
- **Phase 10 so far:** MODIS NDVI and B5 do not beat B3; Nepal rainfall shows promising but unproven gains for
  Uttar Pradesh and Bihar. Details in the Phase 10 report.

## 5. Current state (2026-11-19)

| Item | State |
|---|---|
| Branch | `feat/sprint-11-phase10-yield-research` (from `main` after the Phase 9 merge) |
| Serving yield model | Phase 8 B3 (unchanged) |
| Vision provider | `VISION_PROVIDER` defaults to `mock-v1`; set `onnx-crop-classifier` and `ML_ARTIFACTS_DIR` to use the real model |
| Vision crop auto-accept | `VISION_AUTO_ACCEPT_CROP` defaults to `false`: the farmer confirms the crop on every photo, because the current model mistook wheat for maize and chilli for tomato on Indian field photos ([report](../ml/reports/09_vision.md), section 8) |
| Running experiment | River-flow permutation test (`scripts/run_yield_river.py`) |
| Indian field photo download | Partial: 653 photos, about 1.0 GB of a 5 GB limit (`scripts/download_india_vision.py`, resumable) |
| Tests | ml 55 passed; backend 322 passed + 11 database tests; frontend 33 files passed (Phase 9 run) |

## 6. Next steps

1. Phase 10: finish the river test and a 99-placebo check for Nepal rainfall; then P1 self-supervised
   pretraining, P2 modality dropout, held-out states and years, leave-one-crop-out and k-shot transfer,
   uncertainty per tier, ablations; score the frozen best model on test once; serve it only if it beats B3.
2. Vision: once the Indian photos are complete, test the current model on them as an independent field test,
   then retrain.
3. Phase 10b: Soil Health Card reader and fertilizer calculator (F9), crop calendar (F10), mandi insights (F11),
   community Q&A (F12), livestock and fisheries (F14), video queries (F7).
4. Phase 11: end-to-end golden journeys, the empty docs, and the write-up.

Open decisions waiting on people: scope-freeze sign-off for crop tiers (ADR-026), native Hindi/Telugu review,
officer verification of PM-KISAN and PMFBY content, agronomist crop calendars.

## 7. Working rules

- **Secrets:** API keys live only in git-ignored `backend/.env` and `ml/.env`. Never commit, log or paste them.
- **Farmer data is personal data (DPDP):** `ALLOW_OFF_DEVICE_PROVIDERS=false`; farmer audio, text and photos are
  never sent to external AI services.
- **Offline models only:** no Gemini or pay-as-you-go APIs; local open-source models (for example BioCLIP).
- **Non-commercial data:** some sources (for example the Open-Meteo free tier) are allowed only because the
  project is non-commercial. Recheck them in `ml/DATA_SOURCES.md` if that changes.
- **Branches:** one branch per phase from `main`; merge with `--no-ff` when the phase is reviewed; branches are
  kept, not deleted.
- **Evidence:** every number comes from a logged run id. Choices are made on validation only, each test set is
  scored once per frozen configuration (scripts refuse a second test run), and key comparisons use at least 3
  seeds.
- **Approvals:** ask before downloads over 5 GB, paid services, Google Earth Engine, scraping government sites,
  heavy backend dependencies or schema changes to existing tables.
