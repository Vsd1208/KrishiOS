# 🌾 KrishiOS

### The AI Operating System for Indian Agriculture

> From a farmer's question, in Telugu, Hindi or English, to an evidence-grounded agricultural decision. Powered by agentic AI, RAG, GraphRAG, official government data, district yield intelligence and human-in-the-loop verification.

[![Status](https://img.shields.io/badge/Status-Sprint%2011%20Phase%208-success)](docs/PROGRESS.md)
[![Backend](https://img.shields.io/badge/Backend-FastAPI-009688)](#)
[![Frontend](https://img.shields.io/badge/Frontend-React%20%2B%20TypeScript-61DAFB)](#)
[![AI](https://img.shields.io/badge/AI-Agentic%20%2B%20RAG%20%2B%20GraphRAG-purple)](#)
[![Languages](https://img.shields.io/badge/Languages-te%20%7C%20hi%20%7C%20en-orange)](#)
[![Database](https://img.shields.io/badge/Data-PostgreSQL%20%7C%20Qdrant%20%7C%20Neo4j-blue)](#)
[![Tests](https://img.shields.io/badge/Tests-422%20Passed-brightgreen)](#-tested--verified)
[![Docker](https://img.shields.io/badge/Deployment-Docker-2496ED)](#)
[![License](https://img.shields.io/badge/License-TBD-lightgrey)](#)

**Repository:** [github.com/Vsd1208/KrishiOS](https://github.com/Vsd1208/KrishiOS) · **Progress tracker:** [docs/PROGRESS.md](docs/PROGRESS.md) · **Decisions:** [docs/DECISIONS.md](docs/DECISIONS.md)

---

## 🚜 The Problem

Indian farmers rarely face a single agricultural problem.

A question such as:

> **"My chilli leaves are curling. What should I do?"**, or in Telugu, **"నా మిరప ఆకులు ముడుచుకుపోతున్నాయి, ఏమి చేయాలి?"**

may require understanding the crop and crop stage, pest and disease symptoms, local geography, weather, soil, season, trusted agricultural knowledge, official warnings in force, intervention safety and confidence in the recommendation. In uncertain cases it may also need human expert verification.

Most agricultural digital solutions solve only one part of this problem. **KrishiOS approaches agriculture as a connected intelligence problem.**

---

## 💡 What is KrishiOS?

KrishiOS is a unified agricultural intelligence platform designed around an **AI Operating System architecture**.

Instead of building independent weather apps, pest chatbots, market dashboards, scheme assistants and yield tools as disconnected products, KrishiOS provides a shared intelligence layer that all of them run on. It includes:

- one crop catalog;
- one LGD district/block directory;
- one provider layer that reports which model is actually running;
- one officer review workflow.

The architecture separates the orchestration runtime, specialist agents, AI services, the data layer and the integration layer, so each can evolve independently.

<p align="center">
<img width="777" height="1224" alt="architecture-diagram-cropped" src="https://github.com/user-attachments/assets/0f47a099-9ce3-410f-a4f0-11e4744a6c9c" />
</p>

---

## 🆕 Sprint 11: "KrishiOS Next Level" (status)

Sprint 11 turns the buildathon platform into a multilingual, government-connected system with district yield intelligence. Every number below comes from a logged run (`ml/experiments/*.jsonl`) and its report in [`ml/reports/`](ml/reports). **New to the project? Start with [`docs/HANDOVER.md`](docs/HANDOVER.md)**, then [`docs/Roadmap.md`](docs/Roadmap.md) and [`docs/PROGRESS.md`](docs/PROGRESS.md).

| Phase | What it delivered | Status | Report |
|---|---|---|---|
| 0 Orientation | Verified current state; sourcing of models, government data and licences | ✅ done | [00](ml/reports/00_orientation.md) |
| 1 Foundations | Fixed the red test baseline; fail-loud provider selection; crop catalog; LGD directory; worker service | ✅ done | [01](ml/reports/01_foundations.md) |
| 2 Multilingual core | STT / TTS / translation bake-offs on licence-checked te/hi sets | ✅ done | [02](ml/reports/02_multilingual_core.md) |
| 3 Multilingual bot | NLU, dialogue state, extension-worker mode, verified media, answer feedback | ✅ done, in review | [03](ml/reports/03_multilingual_bot.md) |
| 4 Govt Connect: publishing | Officer console, extraction with provenance, translation gates, targeted delivery, farmer inbox | ✅ done, in review | [04](ml/reports/04_govconnect_publishing.md) |
| 5 Govt Connect: automated | NDMA SACHET feeds, weather cross-check, official mandi prices, SMS/IVR/WhatsApp sandboxes, offline PWA | ✅ done, in review | [05](ml/reports/05_govconnect_automated.md) |
| 6 Yield label audit | APY + UPAg district yield labels, tiers, splits | ✅ done, awaiting scope freeze | [06](ml/reports/06_yield_label_audit.md) |
| 7 Yield predictors | District weather (NASA POWER), polygon crosswalk, leak-safe lead-time features, MODIS NDVI | ✅ done | [07](ml/reports/07_yield_predictor_pipeline.md) |
| 8 Yield baselines + integration | B1-B4 baselines, served forecasts, outlook page, bot yield card, shortfall drafts, insurance helper | ✅ done, in review | [08](ml/reports/08_yield_baselines.md) |
| 9 Real computer vision | Offline crop ID + disease model (ONNX), crop confirmation, field-photo evaluation, BioCLIP comparison, outbreak heatmaps | ✅ done | [09](ml/reports/09_vision.md) |
| 10 KrishiOS yield model | Shared neural model, NDVI, climate and river drivers, pretraining, modality dropout | 🔄 in progress | [10](ml/reports/10_yield_research.md) (interim) |
| 10b Farmer toolkit | Soil Health Card reader, fertilizer calculator, crop calendar, mandi insights, community, livestock | ⏳ planned | — |
| 11 Golden journeys + docs | End-to-end journeys, full docs, write-up | ⏳ planned | — |

---

## ✨ Capabilities

### 🤖 Agentic AI Runtime

KrishiOS is not a single LLM call. The platform uses an orchestrated agent pipeline:

```
Planner → Knowledge Retrieval Agent → Crop Advisory Agent → Response Validation → Farmer-facing response
```

The runtime provides task planning, agent delegation, tool execution, a shared execution context, structured agent contracts, execution policies, timeouts, validation, result merging and escalation paths. It is built around a **bounded Plan → Act → Observe → Respond loop**, not unrestricted autonomous behaviour, which makes it more predictable and auditable in a domain where wrong advice has real consequences.

The planner routes on NLU output, so Telugu, Hindi and code-switched questions reach the right agents. Agent tools include knowledge search, GraphRAG, live weather, mandi prices, government schemes and the **yield forecast tool** (Phase 8).

### 🗣️ Multilingual Bot: Telugu, Hindi, English

The farmer bot is multilingual end to end:

```
language ID → speech-to-text (voice) → NLU (intent + crop/district via catalog and LGD) → dialogue state
   → agents → translation back with safety checks → text-to-speech
```

| Component | Choice | Measured (run of record) |
|---|---|---|
| Speech-to-text | AI4Bharat IndicConformer (RNNT) | FLEURS CER **te 0.073 / hi 0.063** (`65d3ea90da08`); CPU median 2.2 s per utterance, RTF 0.25 (`3d65e68d0266`) |
| Translation | AI4Bharat IndicTrans2 | Agri test set, safety-check pass rate **te 0.550 / hi 0.644** (`2c5c6baf993a`), vs opus-mt 0.350 / 0.375 |
| NLU | Rule-based multilingual lexicon + catalog/LGD resolution | Intent accuracy **0.796**, crop F1 **0.968** (`b74f7a0eb8c7`, draft labels) |
| Dialogue | Clarify-and-resume, slot carry-over, re-ask | Task success **0.90** (`98898e7cfba1`, draft scripts) |

Other behaviour:

- **Clarifies instead of guessing:** ambiguous crops or districts become a clarifying question with choices from the catalog.
- **Blocks bad translations:** a translation that fails the number/unit/protected-term checks is never shown. The farmer sees the English answer with a notice, and the turn goes to an officer.
- **Extension workers** can act for a farmer with recorded consent (assisted mode).
- **Verified media:** videos are attached to answers only when they are verified and licensed.
- **Feedback loop:** every answer can be rated (thumbs up/down with a reason), and down-votes feed an officer triage queue and a regression export.

### 📚 Grounded Agricultural RAG

Answers are grounded in a curated knowledge layer, not only in the LLM's parametric memory:

| Crop | Knowledge |
|---|---|
| 🌾 Paddy / Rice | Pest, disease and crop-management guidance |
| 🌱 Cotton | Crop health, pest and disease management |
| 🌶️ Chilli | Pest, symptom and general management guidance |

Sources are ICAR, ICAR-IIRR, TNAU and Agriculture Department publications.

- **Filters:** retrieval supports semantic vector search with crop, state, district, season, language, authority and document-type filters.
- **Progressive relaxation:** a query starts with specific context and safely relaxes geographic constraints when authoritative documents aren't tagged that way.
- **Official bulletins:** approved bulletins are indexed with their validity window. Expired instructions are excluded, so the bot never cites them as current.

### 🧠 Enterprise Retrieval, Blue-Green Indexing and Evaluation

```
Farmer Query → Query Embedding → Metadata-aware Retrieval (Crop / State / District / Season)
             → Qdrant Vector Search → Ranking / Reranking → Verified Context → Advisory Agent
```

- **Separate from generation:** retrieval is a platform service with its own API, so its quality can be tested without the language model.
- **Safe updates:** knowledge updates build an immutable index version in the background and pass validation gates (Recall, Precision, MRR, nDCG, coverage, latency, chunk and embedding integrity) before blue-green promotion. Rollback is supported.

```
New Index ──┬── PASS ──→ Promote
            └── FAIL ──→ Keep current production index
```

### 🕸️ GraphRAG / Knowledge Graph

A Neo4j knowledge graph complements vector retrieval:

```
Crop ├── HAS_PEST ─────────► Pest
     ├── HAS_DISEASE ──────► Disease
     ├── DEFICIENCY ───────► Nutrient
     ├── HAS_SYMPTOM ──────► Symptom
     └── TREATED_BY ───────► Treatment
```

Graph reasoning paths are shown in the Intelligence Canvas. If Neo4j is not reachable, the runtime logs it and falls back to vector knowledge search.

### 🏛️ Govt–Farmer Connect

Official instructions reach farmers in their language, with the issuing authority always visible.

```
Officer upload / compose / SACHET feed → extraction with provenance (every field links to its source text)
   → translation (HIGH/CRITICAL need officer approval of the translated text) → approve / schedule
   → targeted delivery (district · block · crop · language · segment) → farmer inbox (listen · ask · acknowledge · flag)
   → analytics (delivered · read · acknowledged · questions)
```

- **Real government alerts:** NDMA SACHET CAP feeds (national and Telangana, public domain) are polled automatically. Extraction on 41 held-out real alerts: district **F1 0.836** (`bcf032c40563`).
- **Weather:** Open-Meteo district forecasts are cross-checked against NASA POWER and marked agree / disagree / unverified. There is also a spray-window indicator.
- **Official mandi prices:** AGMARKNET via data.gov.in, with 30-day trends (median across a district's markets), a staleness guard and sharp-move alerts. MSP comes only from the PIB release.
- **Grievances and schemes:**
  - grievance tickets with an SLA;
  - an officer-verified scheme catalog with eligibility Q&A (PM-KISAN and PMFBY are drafts until an officer verifies them). There is no scraping.
- **Channels:** SMS (GSM-7/UCS-2 segmenting, reply keywords), IVR scripts, WhatsApp and web push. Messaging runs on sandbox adapters until a provider and its cost are approved.
- **DPI:** AgriStack (consent-gated), Bharat-VISTAAR and Bhashini adapters exist as sandboxes. They return no data, with a reason; they never fabricate records.
- **Offline-first PWA:** the app shell, weather feed, inbox and crop list are readable offline, and questions asked offline are sent on reconnect.

### 📈 Yield Intelligence

District crop-yield forecasts with honest uncertainty, built inside this repository (`ml/` + `backend/app/forecasting/`).

- **Labels:** DES APY district statistics, 1997-2022, cross-checked against UPAg (97.6% agree within 5%). That gives **340,765** label rows across **43 crops** and **108 crop × season series**, keyed by LGD codes.
- **Crop tiers decide what is served:**
  - **A:** forecast;
  - **B:** forecast with a wide band and officer review;
  - **C:** no number ("insufficient data").
- **Predictors:**
  - NASA POWER daily weather (rain, temperature, humidity, solar radiation), 1997-2024, aggregated by area to **730 LGD districts**;
  - season features at lead times of 0/30/60/90 days, with a leakage test: no input on or after the forecast date can change a feature.
  - MODIS NDVI has been requested. Soil is a known missing input.

**Baselines** (tier-A median normalised MAE, lower is better; test sets scored **once** after tuning on validation only, 3 seeds):

| Model | Time test 2019-22 | Unseen districts |
|---|---|---|
| B1 historical mean | 0.273 | 0.267 |
| B2 ridge | 0.236-0.241 | 0.235-0.236 |
| **B3 multi-crop LightGBM (served)** | **0.236-0.242** | **0.221-0.223** |
| B4 weather only | 0.258-0.266 | 0.249-0.255 |
| Per-crop LightGBM (RQ5 reference) | 0.244-0.247 | 0.232-0.233 |

- **Accuracy:** the shared multi-crop model cuts error by about 11-14% on later years and about 17% on unseen districts, and it is at least as good as per-crop models.
- **Intervals:** its 80% intervals cover 81-85% of actual yields.
- **Weather:** in-season weather adds little over the yield history so far; the report discusses this honestly.

Runs: validation `ab9ba29db405`, test `37dc01be91cf`. Details: [report 08](ml/reports/08_yield_baselines.md).

How forecasts reach people:

- **Officers:** a **District Yield Outlook** page lists likely shortfalls first.
- **Shortfall drafts:** a likely shortfall becomes an **officer-review advisory draft**. It is never published automatically.
- **Farmers:** yield questions in the bot get a **yield card** in their language, labelled *"model estimate, not an official crop-cutting, YES-TECH or insurance figure"*.
- **Same source as training:** forecasts are produced offline from the same data source the model was trained on. Live weather apps are never fed into the model.

### 🛡️ Crop Insurance Helper (PMFBY)

Explains PMFBY premiums, enrolment windows and what to do quickly after crop damage, with the source of every item. It shows the district yield outlook as context only. The guidance is shown to farmers only after an officer verifies it against official sources, and the yield context is never presented as a claim estimate.

### 👁️ Multimodal Crop Intelligence

Farmers can ask with text, voice or a crop photo, and image findings combine with retrieval, graph reasoning and context in the **Vision Diagnostic Lab**.

> **Honest status:** the image model is still the **mock vision provider**. Real crop-identification and disease models, evaluated on field photos, are **Phase 9**. The provider badge in the UI always shows which provider answered.

### 🧾 Responsible AI and Guardrails

Every answer path has the same safeguards:

- grounded retrieval and structured agent contracts;
- response validation and confidence indicators;
- provenance surfaces and human-in-the-loop escalation;
- **visible provider and version** for every AI component, and mocks are a startup error in production;
- **DPDP-aware defaults:** farmer audio and text never go to third-party services unless enabled per provider;
- officer approval for high-severity translations;
- abstention instead of guessing.

When the system lacks verified information, it says so instead of presenting an unsupported recommendation as fact.

### 👨‍🌾 Farmer and 👨‍💼 Officer Workspaces

- **Farmer:**
  - dashboard (weather feed, active official warnings, mandi trend);
  - Ask KrishiOS (text, voice, photo) with rich answers;
  - Govt Updates inbox, Help (grievances and schemes) and the Insurance helper;
  - saved fields and locations.
- **Officer:**
  - review queue and bulletins (ingested and review);
  - publish advisory (compose → target → translation preview → approve or schedule);
  - Connect analytics, grievances and schemes, and **Yield Outlook**;
  - farmer feedback, extension assignments, the knowledge graph and evaluation.

```
AI Advisory → Confidence / Guardrail Check
   ├── Sufficient confidence → Farmer response
   └── Requires review → Officer Review Queue → Inspect provenance → Modify / Approve → Update alert status
```

**AI assists agricultural decision-making; humans stay in the loop when intervention is consequential.**

### 🎨 Intelligence Canvas

Makes the system's reasoning visible:

- GraphRAG reasoning chains, a telemetry matrix and a provenance explorer;
- the vision lab, confidence badges and stage-by-stage thinking indicators;
- a **Providers** tab showing exactly which model or provider answered.

### 🧪 Tested & Verified

Counts from the latest full runs (2026-11-15):

| Suite | Result |
|---|---|
| Backend (`pytest`, unit and API) | **307 passed** |
| Backend Postgres integration (`tests/integration`, migrated database) | **10 passed** |
| Frontend (`vitest`) | **75 passed** (32 files) |
| ML (`ml/tests`) | **30 passed** |
| Frontend production build | **1,772 modules** transformed |

---

## 🗄️ Data Architecture

| Layer | Technology | Purpose |
|---|---|---|
| Relational | PostgreSQL | Farmers, fields, bulletins, deliveries, grievances, schemes, mandi history, yield forecasts |
| Vector | Qdrant | Semantic agricultural retrieval (blue-green indexes) |
| Graph | Neo4j (optional) | Agricultural relationships and GraphRAG |
| Cache / queue | Redis | Cache, worker job queue, feed de-duplication |
| Worker | arq | Scheduled jobs: SACHET poll, weather feed, mandi history, forecast import, Govt Connect maintenance (health at `/api/v1/health/jobs`) |
| ML data | Versioned Parquet (`ml/data/`, not committed) | Yield labels, district weather and season features keyed by LGD code |

**Reference data** (committed in `ml/reference/`):

- the crop catalog (58 crops; te/hi names in draft review);
- LGD districts and blocks;
- district aliases;
- the polygon crosswalk with 60 reviewed overrides;
- MSP from PIB.

Every dataset's licence and access route is in [`ml/DATA_SOURCES.md`](ml/DATA_SOURCES.md).

---

## 🧩 Repository Structure

```
backend/app/
├── agents/          runtime, planner, specialist agents, tools (incl. yield_forecast)
├── retrieval/       enterprise retrieval, blue-green indexing, evaluation
├── graph/           GraphRAG / Neo4j
├── catalog/         shared crop catalog + LGD directory + multilingual resolver
├── nlu/             multilingual intent and entity extraction
├── conversation/    dialogue state, clarification, multilingual reply assembly
├── translation/     IndicTrans2 and others, glossary, safety checks, cache
├── voice/           speech-to-text / text-to-speech providers
├── govconnect/      bulletins, extraction, publishing, SACHET feeds, weather feed
├── channels/        SMS / IVR / WhatsApp (sandbox) adapters
├── notifications/   in-app + web push
├── dpi/             AgriStack / Bharat-VISTAAR / Bhashini (sandbox)
├── grievance/  schemes/    tickets with SLA; verified scheme catalog, PMFBY insurance helper
├── forecasting/     Yield Intelligence: contract, importer, providers, API
├── live_data/       weather, NASA POWER cross-check, AGMARKNET prices and history
├── proactive/       event processor and rules (incl. YieldShortfallRule)
├── extension/  feedback/  media/    assisted mode, answer feedback, verified media
├── worker/          scheduler, jobs, job health
└── providers/       provider registry, kinds (live/sandbox/mock), /providers listing
ml/
├── src/krishios_ml/ yield_labels/, yield_features/, yield_/ (baselines), evaluation harnesses
├── scripts/         reproducible runs (each logs config, seed, split, git commit, metrics)
├── reference/       committed reference tables
├── reports/         phase reports + run data (JSON)
└── experiments/     JSONL experiment logs
frontend/src/        farmer + officer apps, i18n (en / hi / te), PWA service worker
docs/                PROGRESS.md (living tracker), DECISIONS.md (ADRs)
```

---

## ⚙️ Technology Stack

**Frontend:** React 19 · TypeScript · Vite · React Router · TanStack Query · Tailwind CSS · i18next (en/hi/te) · lucide-react · Vitest · PWA service worker

**Backend:** Python 3.12 · FastAPI · Pydantic v2 · SQLAlchemy 2 · Alembic · arq · Pytest · Ruff · Loguru

**AI / Retrieval:** Gemini · AI4Bharat IndicConformer and IndicTrans2 · Sentence Transformers · Qdrant · Neo4j GraphRAG · agent orchestration runtime · grounded response validation

**ML:** pandas · geopandas · rasterio · scikit-learn · LightGBM · PyTorch (laptop GPU) · uv

**Infrastructure:** Docker · Docker Compose · PostgreSQL · Redis

---

## 🚀 Running KrishiOS Locally

### Prerequisites

- Docker Desktop, Git, Node.js, Python 3.12, [uv](https://docs.astral.sh/uv/)
- A Gemini API key (only used where enabled; farmer data is never sent to it by default)
- Optional keys, each placed in a git-ignored `.env` file and never committed:
  - `backend/.env`: `DATA_GOV_IN_API_KEY` for official mandi prices; a Hugging Face read token for AI4Bharat gated models; VAPID keys for web push;
  - `ml/.env`: an Earthdata login (MODIS via AppEEARS).

### Clone and configure

```bash
git clone https://github.com/Vsd1208/KrishiOS.git
cd KrishiOS
cp backend/.env.example backend/.env      # then fill in your own values
cp frontend/.env.example frontend/.env
```

Example frontend configuration:

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_DEFAULT_LANGUAGE=en
```

### Start the platform

```bash
docker compose up -d --build   # the backend entrypoint applies database migrations
docker compose ps
```

| Service | Port |
|---|---|
| Backend (FastAPI) | 8000 |
| Worker (arq scheduled jobs) | — |
| Frontend | 80 |
| PostgreSQL | 5432 |
| Redis | 6379 |
| Qdrant | 6333 / 6334 |

Neo4j (7474 / 7687) is optional and not part of the compose file. Without it, GraphRAG falls back to vector search.

### Run the tests

```bash
cd backend && uv run pytest tests -q --ignore=tests/integration
cd frontend && npx vitest run
cd ml && uv run pytest tests -q
```

Postgres integration tests use a disposable database; see the docstring in `backend/tests/integration/test_phase3_db.py`.

### Reproduce the yield pipeline (from `ml/`)

```bash
uv run python scripts/run_yield_label_audit.py                      # Phase 6 labels + tiers
uv run python scripts/download_power_grids.py --start 1997 --end 2024 # NASA POWER (polite, resumable)
uv run python scripts/build_yield_dataset.py --stage all             # polygons, weights, labels, weather, features
uv run python scripts/run_yield_baselines.py --phase val              # tune + freeze on validation
uv run python scripts/run_yield_baselines.py --phase test             # score once (re-runs are refused)
uv run python scripts/export_yield_forecasts.py --crop-year 2026 --target Kharif:90 --target Rabi:30
```

The backend `forecast_import` job, or **Import latest forecasts** on the officer Yield Outlook page, loads the newest artifact from `ml/artifacts/forecasts/`.

---

## 🧭 Demo Flow

1. **Farmer:** log in and open the dashboard: weather feed, official warnings, mandi trend.
2. **Ask in Telugu or Hindi:** for example *"వరి దిగుబడి అంచనా ఎంత?"*. The bot asks for the district if needed and answers with a yield card.
3. **Advisory:** ask a pest question. You get a grounded answer with citations, confidence, audio and a feedback button.
4. **Govt Updates:** an official SACHET warning in the farmer's language, with listen, ask about this, and acknowledge.
5. **Insurance:** the PMFBY helper with sources and the district yield context.
6. **Officer:** review queue → bulletins (including yield-shortfall drafts) → publish with a translation preview → Connect analytics.
7. **Officer Yield Outlook:** pick a district. Shortfalls are listed first, tier C shows "insufficient data", and a link opens the review drafts.
8. **Intelligence Canvas:** retrieval, GraphRAG paths, provenance and the providers actually used.

---

## 🏆 Why KrishiOS Is Different

Most agricultural AI systems ask: *"Can an LLM answer a farmer's question?"*

KrishiOS asks: **"Can an AI system turn fragmented agricultural information into a traceable, contextual, multilingual and human-verifiable decision?"**

```
                AGRICULTURAL INTELLIGENCE
                         │
   ┌──────────┬──────────┼──────────┬──────────────┐
   │          │          │          │              │
  RAG     GraphRAG   Multimodal  Official data  Yield intelligence
   │          │          │          │              │
   └──────────┴──────────┼──────────┴──────────────┘
                         │
          Agent Orchestration + Multilingual NLU
                         │
              Context + Guardrails
                         │
                  LLM Reasoning
                         │
                 Human Verification
```

The result is not simply a chatbot. It is an agricultural decision-intelligence platform.

---

## 🔭 Roadmap

Remaining Sprint 11 phases (see [docs/PROGRESS.md](docs/PROGRESS.md)):

- **Phase 9: Real computer vision.** Crop ID and disease models exported to ONNX, a field-photo test set, a Gemini zero-shot comparison, crop confirmation, and outbreak heatmaps with officer-approved alerts (F8).
- **Phase 10: KrishiOS yield model.** One shared multimodal model (weather, NDVI, soil, crop embedding, season token), self-supervised pretraining, modality dropout, held-out state/year gaps, leave-one-crop-out transfer and calibration per tier.
- **Phase 10b: Farmer toolkit.** Soil Health Card reader and fertilizer calculator (official tables), crop calendar and reminders, mandi insights, community Q&A, livestock and fisheries advisories, video queries.
- **Phase 11:** golden journeys (Playwright), complete docs and the write-up.

**Open items that need people, not code:**

- faculty sign-off on the yield scope freeze;
- native-speaker review of the Telugu/Hindi strings;
- officer verification of the PMFBY and PM-KISAN entries;
- an agronomist's crop × state sowing calendar;
- SMS/IVR provider and cost approval.

---

## 🧠 Engineering Principles

1. **Evidence before generation:** retrieve trusted agricultural knowledge before asking the LLM to reason.
2. **Context before recommendation:** crop, geography, season and farmer context matter.
3. **Explainability before trust:** a recommendation should be inspectable, including which model produced it.
4. **Human oversight before high-impact action:** AI assists experts; it does not silently replace them.
5. **Honest numbers:** every metric comes from a logged run, test sets are scored once, and missing data is reported as missing.
6. **Platform before features:** new capabilities plug into the shared catalog, LGD, provider and review layers.

---

## 👥 About

KrishiOS is an exploration of what an AI-native agricultural operating system could look like for India. The goal isn't to add an LLM to agriculture. It is to build the intelligence infrastructure around the LLM:

```
data → retrieval → graph → agents → reasoning → validation → action → human oversight
```

---

### ⭐ If this project interests you

Give the [repository](https://github.com/Vsd1208/KrishiOS) a star and follow the development of KrishiOS.

**Built with ❤️ for Indian Agriculture**
