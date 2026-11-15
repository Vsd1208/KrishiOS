# Phase 0: Orientation and Sourcing Report

- **Date:** 2026-11-12
- **Branch:** `feat/sprint-11-phase0-orientation` (from `main` @ `b743526`)
- **Scope:** Phase 0 makes no code changes. This report, `docs/PROGRESS.md` and `docs/DECISIONS.md` are the only files added.

**Evidence convention.** Lines tagged **[run]** were executed in this session; the command is given. Lines tagged **[web]** come from published sources, cited inline. Lines tagged **[unverified]** could not be confirmed, and you should not rely on them yet. This report contains no measured ML metrics, because no model was run in Phase 0. Every quality and latency figure for STT, TTS, MT, NLU and vision is still **to be measured** in later phases.

---

## 1. Summary

1. **Most of the "current state" brief is accurate.** These 12 points need correcting or adding:
   - The repo is nested at `c:\KrishiOS\KrishiOS`.
   - The proposal was in `~/Downloads`, not in the repo.
   - `AgmarknetMarketProvider` makes **no HTTP calls**.
   - Every live-data provider **defaults to a mock**.
   - The provider registry **silently falls back to the mock**.
   - The voice pipeline **hard-codes the mock LLM** and **defaults the crop to "Paddy"**.
   - The embedding model is **English-only**.
   - The backend test baseline is **red**: 112 passed, 6 failed, 1 module fails to collect.
   - The rest are listed in §2.
2. **The proposal contradicts the brief on scope.** It says: *"Start with one crop and one primary benchmark. Do not expand to rice, disease diagnosis, crop mapping, and yield prediction simultaneously."* The brief wins for engineering, but the faculty-approved scope is now different. **Faculty sign-off is needed before Phase 6, not at Phase 11.**
3. **Best government-data finding:** NDMA's **SACHET CAP 1.2 RSS feed** is public. It carries IMD warnings with **LGD district codes**, severity, urgency and expiry, so it maps straight onto `GovtBulletin` and the LGD crosswalk. **[run]**
4. **Access to other sources:**
   - IMD's own APIs need an **API key** (`api.imd.gov.in`) or **IP whitelisting** (`mausam.imd.gov.in/api`). **[run]**
   - The Agmarknet open-data API needs a data.gov.in key. **[run]**
   - I found **no public API** for AgriStack production, Bharat-VISTAAR, Meghdoot, PM-KISAN, Kisan e-Mitra, myScheme or PMFBY. **[web]**
5. **Yield-label caveat:** CY-Bench's India data **is** the ICRISAT DLD (1990–2017, unapportioned). A CY-Bench sanity check is therefore **not independent** of our secondary label source. **[web]**
6. **Vision-data gap:** I found **no permissively licensed, multi-crop, ground-level field-photo dataset for crop identification in India**. The field-photo test set will probably have to be **collected by us, with consent**. Collection takes calendar time and should start early.
7. **Hardware limits the ML plan:**
   - RTX 2050 with **4 GB VRAM**, 15.6 GB RAM, **34 GB free disk** (93% used). **[run]**
   - Raw ERA5-Land or MODIS tiles for all of India will not fit.
   - Phase 7 must use server-side aggregation: NASA POWER, AppEEARS, or Earth Engine on approval.
8. **Effort estimate:** Phases 1–11 total about **108–158 focused working days** (§11). The proposal's 12-week schedule covered only the yield research. **This scope gap must go to faculty.**

---

## 2. Verification of the "current state" brief

| # | Claim in brief | Status | Evidence |
|---|---|---|---|
| 1 | Repo is "this repository"; proposal in repo root or `docs/research/` | **Correction.** The repo is at `c:\KrishiOS\KrishiOS`; `c:\KrishiOS` itself is *not* a git repo and holds 3 stray files (`cotton_graph_test.txt`, `cotton_test.txt`, `graph_metadata.json`). The proposal was found only at `~/Downloads/AgriFormer_X_Minor_Project_Research_Proposal.docx`. | [run] `git status`, `find … -iname "*agriformer*"` |
| 2 | Vision is a mock keyed on `crop_hint` | **Confirmed.** `vision/providers/` holds only `base.py`, `mock_provider.py`, `registry.py`. The mock branches on `metadata["crop_hint"]` (paddy/cotton/tomato/other) and sleeps 0.5 s. Config is `VISION_MODEL_NAME="mock-v1"`; there is no `VISION_PROVIDER` setting yet. | [run] `vision/providers/mock_provider.py:25-75`, `config/settings.py:105` |
| 3 | Voice is a mock keyed on filename | **Confirmed, with a bug.** `mock_stt.py` matches the substring `"te"` in the filename, so any file named e.g. `test.wav` or `note.wav` is "Telugu". `voice_service.py:49-50` defaults to `MockSTTProvider()`/`MockTTSProvider()`. | [run] `voice/providers/mock_stt.py:27-49` |
| 3a | *(new)* Voice pipeline LLM | **New finding.** `voice_service.py:171` constructs `MockLocalLLMProvider()` **unconditionally**, so voice answers never use Gemini even when `LLM_PROVIDER=gemini`. Line 169 sets `crop=norm_res.resolved_crop or "Paddy"`, a **silent crop guess** that Decision 8's no-silent-guess rule forbids. | [run] `voice/services/voice_service.py:160-172` |
| 4 | Planner routes on English keywords; "forecast" goes to weather | **Confirmed.** `planner.py:37-40`. Also, `"district"` is in `_OFFICER_KEYWORDS`, so any farmer question naming a district triggers the officer path. The crop list has `paddy`/`wheat` but no `cotton` or `chilli`. | [run] `agents/planner/planner.py:37-56` |
| 5 | Open-Meteo is real, fetched on request; no scheduler anywhere | **Confirmed**, with a note. `OpenMeteoWeatherProvider` uses `httpx` (live call returned HTTP 200 [run]). But `WEATHER_PROVIDER_NAME` **defaults to `mock-weather-v1`** (`settings.py:140`). A grep for apscheduler/arq/celery/crontab/`create_task` in `app/` finds nothing. `httpx` is only a *dev* dependency; it is installed transitively through `fastapi[standard]`. | [run] |
| 6 | Agromet advisory and scheme providers are mocks | **Confirmed.** `AgrometAdvisoryProvider(MockAdvisoryProvider)` only renames the mock; only `MockGovernmentSchemeProvider` exists. | [run] |
| 7 | Agmarknet provider "verify whether it works" | **It does not.** `AgmarknetMarketProvider` subclasses the mock and only stores `api_base_url`. It has **no HTTP code, no API-key setting**, and `MARKET_PROVIDER_NAME` defaults to mock. The data.gov.in resource `9ef84268-…` exists and returns `{"error":"Authorization field missing"}` without a key. | [run] `market_provider.py:78-88`; `curl` |
| 7a | *(new)* Registry fallback | **New finding.** `LiveDataProviderRegistry.get_*_provider` **silently falls back to the mock** with only a log warning when a provider name is unknown. That breaks the rule that nothing may be presented as real while it is a mock. To be fixed in Phase 1: fail loudly, or surface the active provider. | [run] `live_data/providers/registry.py` |
| 8 | Officer broadcast exists | **Confirmed.** `BroadcastEventModal.tsx` (posts through the `onEmitEvent` prop from `AnalyticsPage.tsx:146`). | [run] |
| 9 | Notifications: in-memory, console, mock-SMS only | **Confirmed.** `notifications/providers.py`. | [run] |
| 10 | No translation service; en/hi/te static i18n only | **Confirmed.** One `common.json` (96 lines) per locale. | [run] |
| 11 | KB covers paddy, cotton, chilli | **Unverifiable from the repo.** No corpus is committed; documents live in Docker volumes (`documents_data`, `qdrant_data`, `neo4j_data`) and no containers were running. `graph/ontology/dictionaries.py` already has **multilingual crop aliases** (e.g. `ప్రత్తి`, `మొక్కజొన్న`, `dhaan`, `gehun`), which is a useful seed for `crop_catalog`. | [run] `docker ps` (empty) |
| 11a | *(new)* Embeddings | **New finding.** `EMBEDDING_MODEL_NAME="all-MiniLM-L6-v2"` is an English-only model, so Telugu and Hindi queries will not embed meaningfully today. This raises the stakes of the cross-lingual retrieval decision in Phase 3. | [run] `settings.py:60` |
| 12 | Patterns to copy (providers, tools, rules, events) | **Confirmed.** Tools present: `govt_scheme, graph_knowledge, knowledge_search, live_advisory, live_weather, mandi_price, vision_analysis, stubs`. `EventType` already has `PEST_RISK_DETECTED`, `AGRICULTURAL_ADVISORY_UPDATED`, `GOVERNMENT_SCHEME_UPDATED`. | [run] |
| 13 | Domain: `District` has no LGD code | **Confirmed.** `District(state, district_name, latitude, longitude)`. `Farmer.preferred_language` is a free `String(50)`. | [run] |
| 14 | Routers "Sprint N"; migrations 0001–0008 | **Confirmed.** The last block is "Sprint 10"; the migrations are `0001`–`0008` (`0008_sprint_10_proactive_intelligence`). | [run] |
| 15 | Python 3.12 + uv; ruff 100; pytest asyncio | **Confirmed.** `requires-python >=3.12,<3.13`, uv 0.12.7, `asyncio_mode="auto"`. | [run] |
| 16 | docker-compose: backend, frontend, postgres, redis, qdrant, neo4j | **Confirmed** (qdrant v1.15.5, neo4j 5-community, postgres 16, redis 7). | [run] |
| 17 | Frontend stack, no chart or map library | **Confirmed.** React 19, TanStack Query 5, i18next, react-router 7, Tailwind 3, Vitest. No chart, map or PWA libraries. | [run] |
| 18 | `docs/*.md` empty | **Confirmed** (1–2 bytes each). | [run] |
| 19 | Stray / debug files | **Confirmed, and there are more.** Tracked in git: the root file `e -File  Select-String -Pattern "Rice-1850740689"` (its name contains private-use Unicode and a trailing ESC byte; it was added in commit `b743526`), `cotton_health.txt`, `rag-body.json`, `metadata.json`, **`openapi.json` (2.1 MB)**, `backend/{debug_live_retrieval,inspect_delta,reindex_documents,verify_index,verify_retrieval}.py`, `backend/walkthrough.md`, `frontend/walkthrough.md`. Outside the repo: the 3 files in `c:\KrishiOS`. `backend/.env` is **not** tracked (good). **Nothing deleted, as you asked.** | [run] `git ls-files` |
| 20 | "All existing tests pass" | **False today.** **Backend:** `test_sprint3_enterprise_retrieval.py` cannot be collected (`ModuleNotFoundError: psutil`; it is imported by `retrieval/monitoring/observability.py` but not declared in `pyproject.toml`). Excluding that file: **112 passed, 6 failed**. **Frontend:** **26 files / 50 tests passed**, and `npm run build` succeeded. | [run] see §2.1 |

### 2.1 Backend test baseline (before any change)

Command: `cd backend && uv run pytest -q --ignore=tests/test_sprint3_enterprise_retrieval.py`. Result: **6 failed, 112 passed in 78.95 s**.

| Failing test | One-line cause |
|---|---|
| `live_data/test_golden_scenarios.py::test_scenario_2_agricultural_spray_decision` | `result.grounded is True` fails: the spray-window answer is not grounded. **This matters for F10, which reuses the spray-window logic.** |
| `test_repositories.py::test_farmer_repository_filters_by_phone` | Test mock is not awaited: an `AsyncMock` coroutine is compared to the result. |
| `test_sprint4_agent_runtime.py::test_runtime_engine_health_check` / `test_api_list_agents` / `test_api_runtime_status` | `assert 7 == 6`: the agent count drifted after an agent was added. |
| `test_sprint6_graph.py::test_relationship_extraction_and_validation` | Expected `('Blast','HAS_SYMPTOM','Leaf Lesions')` was not extracted. |

**Proposal:** Phase 1 fixes these. The fixes are: declare `psutil`, fix the stale test expectations, and investigate the grounding and extraction regressions. Each change will be explained.

---

## 3. Proposal vs. brief: conflicts to record

| Proposal says | Brief says (wins) | Action |
|---|---|---|
| "AgriFormer-X" | Name retired → "KrishiOS Yield Intelligence" / `krishios_yield` | Applied everywhere from Phase 1. |
| One crop, one benchmark; explicit guardrail against adding disease diagnosis etc. | About 100 crop–season series, plus CV, voice, NLU and Govt Connect | **Faculty sign-off needed before Phase 6 scope freeze.** |
| CY-Bench as *primary* label source | DES APY primary, ICRISAT DLD secondary, CY-Bench sanity check only | Note: CY-Bench India = ICRISAT DLD (§6.1), so the "sanity check" is not independent. |
| South Asia (IN/PK/BD/NP) | India only | Recorded. |
| 12-week schedule | 12 phases (§11) | Effort gap goes to faculty. |
| RQ1–RQ4 | Adds RQ5 (multi-crop transfer) | Recorded. |

---

## 4. Voice (STT/TTS), translation and NLU options

**Nothing here has been measured.** Licences and availability come from published sources. The pick is a *recommendation*, to be confirmed by the Phase 2 bake-off (WER/CER per language and code-switched, chrF++, number/unit preservation, CPU latency on this machine).

### 4.1 Speech-to-text

| Candidate | Licence / terms | Te / Hi | Access | Off-device? | Risks |
|---|---|---|---|---|---|
| **AI4Bharat IndicConformer**: per-language `indicconformer_stt_{te,hi}_hybrid_ctc_rnnt_large` (≈120M params) or `indic-conformer-600m-multilingual` | MIT [web: [GitHub](https://github.com/AI4Bharat/IndicConformerASR), [HF 600M](https://huggingface.co/ai4bharat/indic-conformer-600m-multilingual), [AIKosh te](https://aikosh.indiaai.gov.in/home/models/details/ai4bharat_indicconformer_stt_te_hybrid_ctc_rnnt_large_telugu_automatic_speech_recognition_model.html)]. The Hindi card's licence line was **[unverified]** (gated). | Yes | **Gated on Hugging Face**: you must accept the terms with your account. Needs AI4Bharat's NeMo fork. | No | NeMo is a **heavyweight dependency**, so propose a separate inference container (needs approval). Code-switched English words come out in native script, so transliteration normalisation is needed. |
| **Whisper family** (openai/whisper, faster-whisper; IndicWhisper fine-tunes) | MIT for OpenAI weights; check the licence of each fine-tune | Yes (zero-shot quality on Telugu is reported as weak; IndicWhisper scored best on 39/59 Vistaar benchmarks [web: [Vistaar](https://arxiv.org/pdf/2305.15386)]) | Not gated | No | CPU latency for medium/large models; Telugu quality unknown until measured. |
| **Bhashini (ULCA / Dhruva)** | Self-serve ULCA registration and API key [web: [onboarding](https://bhashini.gitbook.io/bhashini-apis/pre-requisites-and-onboarding)]. **API terms on commercial use and retention not found [unverified].** | Yes | Registration | **Yes** (government servers) | Terms unclear; latency and uptime unknown. |
| **Gemini audio** (already a dependency) | Gemini API terms. The **free tier may use prompts to improve Google products**; paid (billed Cloud project) does not [web: [Gemini API terms](https://ai.google.dev/gemini-api/terms)] | Telugu transcription quality **[unverified]** | Key already in `.env` | **Yes** | DPDP: farmer audio leaves the device. Needs your explicit approval and a paid tier. |

**Recommendation (pending bake-off):** primary is **IndicConformer per-language (te, hi) behind `STT_PROVIDER`**; fallback is **faster-whisper** (local) or Bhashini/Gemini (off-device, approval needed). Eval sets: FLEURS te/hi, Kathbath, IndicVoices. Each set's licence will be checked before download. A **hand-recorded code-switched set** is also needed (te-en, hi-en).

### 4.2 Text-to-speech

| Candidate | Licence | Notes |
|---|---|---|
| **AI4Bharat IndicF5** | MIT [web: [AIKosh](https://aikosh.indiaai.gov.in/home/models/details/aibharat_indicf5.html)] | 11 languages incl. te/hi. A flow-matching model, so **CPU latency is a real risk** and must be measured. |
| **AI4Bharat Indic Parler-TTS** | Apache-2.0 per aggregators; **gated**; the commercial terms say "confirm with AI4Bharat" **[unverified]** | te/hi supported. |
| Google Cloud TTS (Chirp 3 HD) | Paid | `te-IN` appears in some doc versions **[unverified]** ([docs](https://docs.cloud.google.com/text-to-speech/docs/chirp3-hd)); off-device. |
| Bhashini TTS | See above | Off-device. |

**Recommendation:** bake off IndicF5 against Indic Parler-TTS on CPU, judging latency per sentence and native-speaker MOS-style ratings. Use a hosted fallback only on approval.

### 4.3 Machine translation

| Candidate | Licence | Notes |
|---|---|---|
| **IndicTrans2 distilled** (`indictrans2-en-indic-dist-200M`, `indictrans2-indic-en-dist-200M`; ≈211M params each) | MIT (checkpoints); data CC0 [web: [paper](https://arxiv.org/pdf/2305.16307), [HF](https://huggingface.co/ai4bharat/indictrans2-en-indic-dist-200M/commits/main/LICENSE)] | Authors report about 36% lower inference time than the 1B model, at slightly lower quality. Runs locally. |
| Gemini | API terms as above | Off-device. Useful for back-translation checks. |
| Bhashini NMT | Terms **[unverified]** | Off-device. |

**Recommendation:** primary is **IndicTrans2-dist-200M (local)**, with protected-term masking (placeholders for chemicals, doses, numbers, units, scheme and district names) before translation and restoration after, plus the number/unit post-check. Fallback is Gemini, on approval. Eval: at least 100 hand-checked agri sentences per language from real advisories (SACHET, AAS and CRIDA bulletins are good sources), with **native-speaker reviewers (please recruit)**.

### 4.4 NLU approach

- **Primary:** Gemini structured output (JSON schema → `NLUResult{intent, entities, language, confidence}`), reusing the existing `GeminiLLMProvider`.
- **Deterministic fallback**, always available offline: language ID by script detection plus a tiny lexicon, then alias lookup against `crop_catalog`, which is seeded from `graph/ontology/dictionaries.py`. That file already has te/hi aliases. Districts resolve through LGD names plus aliases. The existing keywords are rewritten as **intent rules**, with yield phrases taking priority over weather's `"forecast"`.
- **Cross-lingual retrieval** (Phase 3): compare (a) a multilingual embedder (candidates: `intfloat/multilingual-e5-small`, `paraphrase-multilingual-MiniLM-L12-v2`, LaBSE; licences to be checked) against (b) translating to English with IndicTrans2 and then retrieving with the current English index. Choose by recall@k on a te/hi query set. Option (a) needs a full **re-index through the existing blue-green pipeline**.
- **Eval:** at least 150 hand-labelled utterances (te/hi/en/code-switched). **You review the labels.**

---

## 5. Official government sources

| Source | Machine-readable? | Update cadence | Reuse terms | Recommendation |
|---|---|---|---|---|
| **NDMA SACHET CAP feed** (IMD + SDMA alerts) | **Yes, public RSS + CAP 1.2 XML.** [run] `rss_india.xml` returned 98 items at the time of the check, mostly IMD regional centres. One sampled alert had `cap:geocode` **"LGD District Code" = 575**, plus severity, urgency, certainty, `effective`/`expires` and a polygon URL. | Near-real-time (nowcasts valid about 3 h) | A government document says RSS subscribers (e.g. news agencies) "can further disseminate/broadcast the warning" [web: [CDOT CAP](https://cdot.in/cdotweb/assets/docs/products/dms/cap.pdf)]. **Formal reuse licence not found [unverified].** | **Primary automated warnings source (Phase 5).** Polling a published RSS feed is not scraping, but please confirm you are comfortable with it. Ask NDMA for written terms in parallel. |
| **IMD API v1** (`api.imd.gov.in/api/v1/…`: `districtwarning`, `districtnowcast`, `districtrainfall`, `state_district_rainfall_forecast`, `cityforecast`, `aws_data`, …) | Yes, JSON | Daily / sub-daily | Not stated on the [reference page](https://api.imd.gov.in/public/api_reference.html) | [run] returns `401 {"error":"API key missing"}`. **You need to request a key from IMD.** The legacy `mausam.imd.gov.in/api/*` returns "IP … needs to be whitelisted" [run]. |
| **IMD Agromet Advisory Service (AAS)** district/block bulletins | **PDF / HTML only**; no API found | **Tuesdays and Fridays** [web: [CGIAR on Meghdoot](https://www.cgiar.org/news-events/news/inside-meghdoot-the-app-delivering-weather-based-agricultural-advice-to-farmers-across-india)]. Block-level advisories for about 3,100 blocks (2023 note) [web: [CGSpace](https://cgspace.cgiar.org/server/api/core/bitstreams/7ed1f609-b38f-4ac1-9ea7-a3ae7f020067/content)] | Not found | **Officer upload (guaranteed path).** Automated fetching of state PDFs (e.g. `mausam.imd.gov.in/amaravati/mcdata/APAgromet.pdf`) would count as scraping, so it **needs your approval** and IMD's terms. Also ask IMD whether the "Agromet Advisory" entry in the API index has an endpoint. |
| **ICAR-CRIDA National AAS bulletin** | PDFs at predictable dated URLs (e.g. `icar-crida.res.in/WDU/2026/AUG_2026/NAAS-Bulletin-24-August-2026.pdf`) | Weekly | Not found | Officer upload. Automated download needs approval. National-level, so targeting is coarse. |
| **State agriculture departments** (Telangana, AP and others) | Notices/PDFs; **no feeds found** (not researched per state) | Ad hoc | Varies | Officer upload. Survey the priority states in Phase 4. |
| **KVK / ICAR advisories** | Not found in this search | Ad hoc | — | Officer upload plus KVK staff accounts (F6). |
| **Scheme portals**: myScheme, PM-KISAN, PMFBY | **No public API.** myScheme terms **restrict bots and scrapers** [web: [myScheme terms](https://www.myscheme.gov.in/ta/terms-of-use)]. API Setu requires the provider's approval [web: [API Setu SOP](https://cdn.apisetu.gov.in/portal/assets/sop-apisetu-v0.pdf)] | — | — | A curated, officer-maintained scheme catalog with source links (F4). Request API Setu access. **No scraping.** |
| **Agmarknet** (data.gov.in resource `9ef84268-d588-465a-a308-a864a43d0070`) | Yes, JSON, **needs an API key** [run] | Daily, with a reported 2–7 day lag [web, third-party] | **GODL-India**: commercial reuse allowed **with attribution** [web: [GODL summary](https://www.wikipedia.org/wiki/GODL)] | **Usable now** once you register a data.gov.in key. Implement the real HTTP adapter in Phase 5. |
| **mKisan** | Government-internal SMS/IVR portal for officers; **no public API** | — | — | Out of reach for us; note it as the route a real deployment would use. |
| **LGD directory** | Bulk download (CSV/XML) from [lgdirectory.gov.in](https://lgdirectory.gov.in/downloadDirectory.do); no API. Mirror tables under ODC-By on India Data Portal. | Changes on reorganisation | Government data | Phase 1: commit a reviewed `district_crosswalk.csv` (state → district → block → GP codes). |

---

## 6. Yield labels and predictors

### 6.1 Labels

| Source | Coverage | Licence | Access | Caveats |
|---|---|---|---|---|
| **DES APY (MoA&FW)**: `data.desagri.gov.in/website/crops-apy-report-web` | District × crop × season. Mirrors list 1997–2021 and last-updated 14-12-2023 [web: [India Data Portal](https://ckandev.indiadataportal.com/dataset/area-production-yield-apy)] | Government data (GODL where on data.gov.in) | The source is listed as `data.desagri.gov.in/login`, so **a login may be required [unverified]** | District boundaries change over time, so the LGD crosswalk is essential. Units vary by crop (e.g. cotton in bales). |
| **ICRISAT–TCI DLD** | 1966–2017, about 20 states, 571–592 districts depending on version; apportioned and unapportioned variants [web: [TCI](https://tci.cornell.edu/data)] | **Conflict:** CC BY 4.0 per CY-Bench's README [web: [CY-Bench IN README](https://github.com/WUR-AI/AgML-CY-Bench/blob/main/data_preparation/crop_statistics_IN/README.md)] vs **CC BY-NC 3.0** per an ICAR KRISHI record [web: [KRISHI](https://krishi.icar.gov.in/ohs-2.3.1/index.php/record/view/182215)] | Dataverse download | **Resolve the licence on the Dataverse landing page before use.** Never commit raw data either way. |
| **CY-Bench (India)** | Maize and wheat, district level, **1990–2017, sourced from ICRISAT DLD, unapportioned (2015 boundaries)**, CC BY 4.0 | CC BY 4.0 | Zenodo | **Not independent of DLD.** Use only to reproduce published baselines, as the brief says. |

### 6.2 Predictors

| Source | Licence | Disk-aware access plan |
|---|---|---|
| **NASA POWER** (daily weather) | Free, open [web, proposal ref 8] | Point/regional API, no key. **Recommended primary**, because district-centroid or sampled-point aggregation keeps it to MBs. |
| **ERA5-Land** | CC BY 4.0 with Copernicus attribution [web: [EQC](https://eqc.climate.copernicus.eu/node/9944)] | Use the CDS daily-statistics subset over India. Hourly downloads for all of India would exceed the 34 GB free. Optional, secondary. |
| **MODIS NDVI/EVI** (MOD13Q1) | NASA open data policy **[unverified in this session]** | Use **AppEEARS** area requests for zonal stats (free Earthdata login) instead of raw tiles; GEE only on approval. |
| **SoilGrids** | CC BY 4.0 **[unverified in this session]** | Download district zonal summaries (WCS subset), not global tiles. |
| **Cropland mask**: ESA WorldCereal / WorldCover | Licence **[unverified in this session]** | 10 m India-wide is large, so aggregate server-side or use a coarser mask. |
| **District polygons with LGD codes** | Candidates: DataMeet (CC BY 2.5 IN, census codes, not LGD) [web: [DataMeet](https://projects.datameet.org/maps/districts/)]; geoBoundaries (HDX, 2022; licence to check); SHRUG (PC11 vintage) | No official open LGD-coded shapefile was found, so build an LGD ↔ census ↔ polygon crosswalk by hand and review it. |

---

## 7. Computer-vision datasets

| Dataset | Content | Field or lab | Licence | Use |
|---|---|---|---|---|
| **PlantVillage** | About 54k leaf images, 14 crops | **Lab** (uniform backgrounds) | Varies by mirror **[unverified]** | Pre-training only. One study reports accuracy dropping from 98.2% (lab) to 71.6% (field) for models trained on lab data [web: [UTM study](https://libmast.utm.my/Record/doaj.art-ce05adf923584281a2d0c6d3d7657246)]. |
| **PlantDoc** | About 2.6k images, 13 species, 17 disease classes | Partly field (web-sourced) | CC BY 4.0 [web: [GitHub](https://github.com/pratikkayal/PlantDoc-Dataset)] | Disease fine-tune and test. |
| **Paddy Doctor** | 16,225 images, 13 classes (v2) | **Field** (smartphone, India) | **CC BY-SA 4.0 per arXiv vs "CC Attribution" on IEEE DataPort [unverified]** | Paddy disease. Share-alike may affect redistribution of derived weights, so check. |
| **AgriPath-LF16** | 111k images, 16 crops, 41 diseases, explicit lab/field split; 30k balanced subset on HF | Both | **Not found [unverified]** | Strong candidate *if* the licence allows. |
| **Pl@ntNet-300K** | 306k images, 1,000+ species | Field (citizen science) | **Per-image CC BY-SA / BY-NC / BY-NC-SA** [web: [Zenodo](https://zenodo.org/records/4726653/latest)] | Possible crop-ID pre-training. Filter to crop taxa and permissive licences only. |
| **Crop identification, multi-crop, India field photos** | — | — | **None with a clear permissive licence found** | **Gap.** Proposal: a consented field-photo collection through KVK/extension partners, with a written protocol (EXIF/GPS stripping, retention). This must start early because it takes calendar time. |

Also the training budget: **4 GB VRAM** means compact backbones (MobileNetV3, EfficientNet-B0/V2-S, ConvNeXt-Atto/Femto via `timm`) with AMP and small batches. That fits Decision 12's CPU inference requirement anyway.

---

## 8. DPI interoperability (F1): what is legally usable now

| System | Public API / sandbox? | Usable now | Needs MoU or approval |
|---|---|---|---|
| **AgriStack** (UFSI, consent manager) | A **sandbox with sample registry data exists for "authorised stakeholders"** [web: [agristack.gov.in](https://agristack.gov.in/)]. No public developer self-signup found. | Sandbox adapter (ours) only | Sandbox onboarding and production access need authorisation. Farmer consent goes through the consent manager. |
| **Bharat-VISTAAR** | **No developer API documentation found** [web] | Sandbox adapter (ours); link out to the 155261 helpline and app | Partner route through MoA&FW. |
| **Meghdoot / IMD** | No Meghdoot API. IMD API needs a key or IP whitelist [run] | **SACHET CAP feed (IMD alerts)** [run] | IMD API key request. |
| **Bhashini** | ULCA self-registration plus API key [web] | Yes once registered, *if* the terms allow our use (**not yet read**) | Your approval (sends farmer data off-device). |
| **PM-KISAN / Kisan e-Mitra** | **No public API** [web] | Link out to the official status page and 155261 only. **Never scrape.** | MoU. |
| **myScheme / API Setu** | API Setu needs the provider's approval [web] | Curated catalog | API Setu request. |
| **Agmarknet** | data.gov.in key [run] | **Yes** (GODL, attribution) | Free key registration by you. |

---

## 9. Notification channels and cost

All figures are **vendor-published estimates, not quotes** (excluding 18% GST).

| Channel | Cost | Prerequisites | Notes |
|---|---|---|---|
| In-app inbox | ₹0 | — | Build first. |
| Web Push / FCM | No per-message fee for FCM **[unverified in this session]** | Firebase project (or VAPID keys for Web Push) | Ties in with the PWA (F3). |
| SMS (DLT) | About **₹0.10–0.28 / SMS**, plus about **₹5,900 one-time DLT registration** [web: [Gupshup analysis](https://codingclave.com/blog/gupshup-sms-pricing-india-2026), [MessageCentral](https://www.messagecentral.com/en-in/blog/a2p-sms-pricing-india)] | DLT principal-entity, header and template registration (templates for every language) | Telugu/Hindi need Unicode SMS, which has shorter segments and so costs more per message. |
| WhatsApp Business | Utility about **₹0.115–0.145 / msg** (sources disagree); marketing ₹0.8631 from 1 Jan 2026 [web: [Meta pricing](https://developers.facebook.com/documentation/business-messaging/whatsapp/pricing.md), [baat.ai](https://baat.ai/blog/whatsapp-api-pricing-india)] | Meta Business verification, template approval | Per-message billing since 1 Jul 2025. |
| IVR / voice | **Quote-based** (Exotel publishes no per-minute rate); generic market about ₹0.30–1.20/min; watch pulse size [web: [Exotel guide](https://exotel.com/blog/voice-call-api-in-india/)] | Virtual number, KYC | Get a written quote. |

---

## 10. Competitor feature comparison (published sources only)

✅ = documented · ◐ = partial or limited · — = not found in sources · *KrishiOS column = today, verified in repo (planned in brackets)*

| Capability | Bharat-VISTAAR | Meghdoot | Kisan e-Mitra | Farmer.Chat | Plantix | mKisan | YES-TECH | **KrishiOS today (planned)** |
|---|---|---|---|---|---|---|---|---|
| Multilingual chatbot | ◐ text chatbot **en+hi at launch**; regional "gradually" ([TechObserver](https://techobserver.in/news/egov/bharat-vistaar-ai-platform-farmers-launched-321400/)) | — | ✅ 11 languages incl. te ([IndiaAI](https://indiaai.gov.in/article/exploring-pradhan-mantri-kisan-ai-chatbot)) | ✅ RAG, WhatsApp/Telegram ([OpenAI case](https://openai.com/index/digital-green)) | — | — | — | ◐ mock voice, English keyword routing (→ te/hi/en evaluated) |
| Voice / IVR | ✅ "Bharati" on 155261, hi+en at launch ([PIB](https://www.pib.gov.in/PressReleseDetailm.aspx?PRID=2228842&reg=3&lang=2)) | — | ✅ voice; IVRS 155261 | ◐ audio messages | — | ✅ IVRS ([mKisan](https://mkisan.gov.in/Home/About)) | — | — mock (→ STT/TTS + IVR adapter) |
| Video queries | ◐ one report only ([FPJ](https://www.freepressjournal.in/tech/bharat-vistaar-agriculture-ai-powered-tool-to-launch-in-india-tomorrow-how-can-farmers-use-it)) | — | — | ◐ links to its training-video library | — | — | — | — (→ F7) |
| Block/district weather + agromet | ✅ via IMD integration ([IMPRI](https://www.impriindia.com/insights/policy-update/bharat-vistaar-multilingual-ai/)) | ✅ block forecasts ~6,970 blocks, Tue/Fri advisories, push, offline | ◐ planned | — | — | ✅ weather alerts by SMS | — | ◐ on-request Open-Meteo (default mock) (→ SACHET + scheduled feeds, F2) |
| Officer → farmer targeted publishing with ack | — | — | — | ◐ human review stage | — | ✅ officer SMS push to block level, 12 languages | — | ◐ broadcast modal (→ full Govt Connect) |
| Scheme info / personal status | ✅ ~10 central schemes | — | ✅ PM-KISAN status + grievance | — | — | — | — | mock (→ F4, link-out for status) |
| Photo diagnosis | ◐ pests-diseases listed | — | — | ◐ photo via extension agents | ✅ | — | — | mock (→ Phase 9) |
| Outbreak surveillance | — | — | — | — | ✅ district-level, anonymised ([Stork](https://www.stork.ai/en/plantix)) | — | — | — (→ F8) |
| Fertilizer calculator | ◐ soil listed | — | — | — | ✅ ([FAO](https://agritechobservatory.review.fao.org/en/plantix-crop-doctor)) | — | — | — (→ F9, official tables only) |
| Community Q&A | — | — | — | — | ✅ | — | — | — (→ F12) |
| Extension-worker mode | — | — | — | ✅ main users | — | — | — | — (→ F6) |
| Yield estimation | — | — | — | — | — | — | ✅ RS-based, ≥30% weight in PMFBY ([CSE](https://www.cseindia.org/content/downloadreports/13110)) | — (→ district outlook with uncertainty; **not** a YES-TECH or claim estimate) |
| Offline mode | — | ✅ | — | — | — | ✅ (SMS) | — | — (→ F3) |

Readings to note:
- Bharat-VISTAAR's **Telugu support was not available at launch** per press coverage. That supports the "evaluated Telugu" differentiator, but must be re-checked before any claim, since it was expected to expand.
- "Krishi Saathi" and video queries appear in only one source; the brief's description is not fully confirmed.

---

## 11. Refined phase plan and effort estimates

These estimates are **rough, in focused working days** (one developer with Claude). They will be revised after each phase.

| Phase | Changes vs. the brief | Estimate |
|---|---|---|
| **1 Foundations** | Add: **fix baseline tests** (psutil + 6 failures); **remove silent mock fallbacks** and show the active provider; LGD district/block crosswalk and the `crop_catalog` seed (from `dictionaries.py`); fix the voice LLM and "Paddy" default; repo hygiene (after your OK); worker service. | 6–9 |
| **2 Multilingual core** | STT/TTS/MT **bake-off harness first** (licence-checked eval sets, native-speaker sets), then providers; consider a separate `inference` container for NeMo/torch-heavy models (**approval: heavyweight dependency**). | 10–14 |
| **3 Bot + F6/F7/F13** | Cross-lingual retrieval decision (may trigger a blue-green re-index). | 10–14 |
| **4 Govt Connect publish + F2/F4** | — | 12–16 |
| **5 Govt Connect automated + F1/F3/F5** | **SACHET CAP adapter first** (structured, LGD-coded); real Agmarknet HTTP adapter; IMD API once a key exists. | 12–18 |
| **6 Yield label audit** | Can run **in parallel** from Phase 2 onward in a separate worktree (ml/ only); needs your OK. Resolve the ICRISAT licence first. | 5–7 |
| **7 Predictors** | Disk-aware: NASA POWER + AppEEARS/SoilGrids zonal stats; ERA5-Land and GEE optional, on approval. | 7–10 |
| **8 Baselines + integration + F15** | — | 8–12 |
| **9 Vision + F8** | **Start consented field-photo collection in Phase 1–2** so a field test set exists by Phase 9. | 10–15 |
| **10 Yield model research** | 4 GB VRAM: compact encoders, AMP, ≥3 seeds. | 10–15 |
| **10b Toolkit (F9–F12, F14, F7 video)** | F9 needs real SHC photos for OCR evaluation (collect with consent). | 12–18 |
| **11 Golden journeys + docs** | Add Playwright (new dev dependency). | 6–10 |
| **Total** | | **≈108–158** |

---

## 12. Open questions and requests (need your decision or action)

1. **Faculty sign-off** on the expanded scope and schedule (§3, §11), *before Phase 6*.
2. **Hugging Face access:** accept AI4Bharat's gated-model terms (IndicConformer te/hi, Indic Parler-TTS) on your account, and provide a read token through `.env` (never committed).
3. **API keys / registrations you need to make:** data.gov.in key (Agmarknet; free); IMD API key request; Bhashini ULCA (optional); DES APY login if required.
4. **SACHET CAP feed polling:** OK to poll this public RSS in Phase 5? (It is not scraping, but please confirm.)
5. **Gemini with farmer data:** approve or decline Gemini for NLU, vision fallback and MT fallback. If approved, confirm the API key sits on a **billed (paid) Cloud project**, so the free-tier data-use terms do not apply.
6. **Native-speaker reviewers** (te, hi) for the MT set (100+ sentences/language), the NLU labels (150+ utterances) and TTS ratings.
7. **Field-photo and SHC-photo collection:** approve a consented collection protocol through KVK/extension partners, and name any partners you have.
8. **ICRISAT DLD licence conflict** (CC BY 4.0 vs CC BY-NC 3.0): OK for me to treat it as non-commercial until the Dataverse page is checked?
9. **Disk space:** only 34 GB free. Can you free space or attach external storage before Phases 6–7 and 9?
10. **Repo hygiene:** may I delete these (Phase 1)? The stray root `e -File … Rice-1850740689…` file, `cotton_health.txt`, `rag-body.json`, `metadata.json`, the backend debug scripts (`debug_live_retrieval.py`, `inspect_delta.py`, `verify_index.py`, `verify_retrieval.py`; and `reindex_documents.py` could move to `backend/scripts/`), the 3 files in `c:\KrishiOS\` outside the repo. Should `openapi.json` (2.1 MB) be regenerated in CI instead of committed?
11. **Separate inference container** for heavy speech/translation models: OK in principle (decided in Phase 2 with measurements)?
12. **Proposal location:** may I copy the proposal `.docx` to `docs/research/`? It contains blank student/mentor name fields only.

---

## 13. Evidence index

| What | Command / location |
|---|---|
| Repo state | `git status`, `git log --oneline`, `git ls-files` (585 files tracked) |
| Proposal text | Extracted with `python-docx` to the session scratchpad (not committed) |
| Frontend tests/build | `npx vitest run` → 26 files / 50 tests passed; `npm run build` → success |
| Backend tests | `uv run pytest -q` → collection error (psutil); with `--ignore=tests/test_sprint3_enterprise_retrieval.py` → 112 passed, 6 failed, 78.95 s |
| Endpoint probes | `curl` to `api.imd.gov.in/api/v1/districtwarning` (401 key missing), `mausam.imd.gov.in/api/warnings_district_api.php` (401 IP whitelist), `api.data.gov.in/resource/9ef84268-…` (400 auth missing), `api.open-meteo.com` (200), `sachet.ndma.gov.in/cap_public_website/rss/rss_india.xml` (200, 98 items) |
| Hardware | `nvidia-smi` (RTX 2050, 4096 MiB), RAM 15.6 GB, `df -h /c` (34 GB free), Docker 29.6.2 |
