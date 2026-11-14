# Architecture Decision Log

Format: **ADR-NNN, title.** Each entry has a status (proposed / accepted / superseded), context, decision and consequences.

## ADR-001: Single repository, `ml/` as a separate uv project
- **Status:** accepted (project brief, decision 1)
- **Decision:** All work lives in KrishiOS. Training and research code goes in `ml/`, which has its own `pyproject.toml`. The backend only loads exported artifacts from `ml/artifacts/`, mounted read-only.
- **Consequences:** Heavy training dependencies stay out of the backend image.

## ADR-002: "AgriFormer-X" name retired
- **Status:** accepted (brief)
- **Decision:** The research is named "KrishiOS Yield Intelligence", and the model is `krishios_yield`.

## ADR-003: Brief overrides the research proposal's scope guardrail
- **Status:** accepted for engineering; **faculty sign-off pending**
- **Context:** The proposal limits scope to one crop and one benchmark, and warns against adding disease diagnosis. The brief expands scope to multi-crop yield, CV, voice, NLU and Govt Connect.
- **Decision:** Follow the brief, and raise the scope change for faculty sign-off before the Phase 6 scope freeze.

## ADR-004: SACHET CAP feed as the preferred automated weather-warning source
- **Status:** proposed (needs your OK to poll)
- **Context:** The IMD APIs need an API key or IP whitelisting. The NDMA SACHET CAP 1.2 RSS feed is public and includes LGD district codes, severity and expiry.
- **Decision:** Build the SACHET adapter first in Phase 5, and add the IMD API adapter once a key is granted.

## ADR-005: No silent fallback to mock providers
- **Status:** accepted and implemented (Phase 1, `app/providers/`, `GET /api/v1/providers`)
- **Context:** `LiveDataProviderRegistry` falls back to mocks with only a log warning.
- **Decision:** Resolve providers from config. An unknown name is a startup error. Every response carries the active provider name and version.

## ADR-006: Separate inference container for heavy speech and translation models
- **Status:** proposed (decide in Phase 2 with measurements; heavyweight dependency, needs approval)
- **Context:** IndicConformer needs a NeMo fork. Keeping it out of the backend image protects build time and image size.

## ADR-007: arq on Redis for the worker
- **Status:** accepted (Phase 1)
- **Context:** No scheduler existed. Redis is already in the stack. Celery would be heavier than needed.
- **Decision:** Use arq cron jobs. Each `JobSpec` sets its interval, timeout and retries. Idempotency is a per-slot Redis `SET NX` key; health is stored in Redis and exposed at `/api/v1/health/jobs`.
- **Consequences:** One extra container (`worker`). Jobs must be async and idempotent.

## ADR-008: `ml/reference/*.csv` is the single source of truth for crops and LGD
- **Status:** accepted (Phase 1)
- **Decision:** The hand-reviewable CSV is canonical. The backend loads it into memory, so resolution never needs the database. Postgres `crop_catalog` is a seeded mirror used for foreign keys. Docker mounts `ml/reference` read-only.
- **Consequences:** Editing a crop is a reviewed CSV change followed by re-running the seed script. There are no hard-coded crop strings in modules.

## ADR-009: Ambiguity is surfaced, never resolved by guessing
- **Status:** accepted (Phase 1)
- **Decision:** Shared aliases (e.g. *gobhi*), duplicate district names (e.g. Bilaspur in HP and CG) and unmatched rows return `ambiguous` or `not_found`. The UI shows a picker, and the seed script leaves the row unlinked and logs it.

## ADR-010: Reversible defaults when running phases "unasked"
- **Status:** accepted (user instruction, 2026-11-12, Phases 1–2)
- **Decision:** Where the brief says "ask first", take the reversible option and record it in the phase report:
  - git-tracked deletions only;
  - additive, nullable schema changes;
  - third-party providers built but disabled by default (`ALLOW_OFF_DEVICE_PROVIDERS=false`);
  - no paid services;
  - no gated downloads on the user's behalf.

## ADR-011: Translation safety by span protection plus independent checks
- **Status:** accepted (Phase 2)
- **Decision:** Quantities, glossary-protected terms and catalog crop names are masked as `<i>` placeholders before MT and restored afterwards. The `<i>` format was chosen by measured survival through opus-mt: hi 11/11, te 10/11, versus 5/11 for `[i]`. An independent checker (numbers in three digit systems, units in en/hi/te, protected terms, leftover placeholders) gates delivery. Failing output is `blocked`, and HIGH/CRITICAL content needs officer approval.
- **Consequences:** Doses and units are always shown in Latin digits and units in te/hi text. A native-review item is open on whether that is acceptable to farmers.

## ADR-012: Interim providers while gated models await access
- **Status:** accepted (Phase 2), **revisit when Hugging Face access is granted**
- **Context:** AI4Bharat IndicTrans2, IndicConformer, IndicF5 and Indic Parler-TTS are gated on Hugging Face, and no token exists on this machine. The Gemini key is **free tier** and its quota is exhausted, and free-tier prompts may be used by Google.
- **Decision:** Defaults stay mock or rule-based; nothing becomes the default silently.
  - **Interim options, selectable by config:** opus-mt (MT, Apache-2.0), faster-whisper (STT, MIT), MMS-TTS (TTS, CC BY-NC: demo only).
  - **Off-device providers:** stay disabled (`ALLOW_OFF_DEVICE_PROVIDERS=false`).
  - **Recommended primaries once access exists:** IndicTrans2 (MT), IndicConformer (STT), IndicF5 or Indic Parler-TTS (TTS), each pending measured comparison.

## ADR-013: Evaluation sets are test-only; no tuning against them
- **Status:** accepted (Phase 2)
- **Decision:** `ml/evaluation_sets/nlu/utterances_v1.jsonl` and `mt/source_en.tsv` are test sets, scored once per configuration. Lexicon or glossary improvements require a separate dev set. Errors seen on the test set are reported, not patched.

## ADR-014: IndicTrans2 protects terms and crop names, not quantities
- **Status:** accepted (Phase 2, decided on the dev split only)
- **Context:** IndicTrans2 has no `>` in its vocabulary and drops about half of all placeholders. Masking numbers also makes it substitute vague words ("next <n> hours" became "next few hours").
- **Evidence (dev split, 41 sentences, check pass rate te/hi):**

  | Strategy | te | hi | Run |
  |---|---|---|---|
  | All kinds masked | 0.171 | 0.146 | `b5ac92146c7c` |
  | Terms and crops only | **0.317** | **0.488** | `8b5381fbede6` |
  | No masking | 0.341 | 0.415 | `61627640c410` |

- **Decision:** `IndicTrans2Provider.protect_kinds = {protected, crop}`, with placeholder format `<ID{i}>`.
- **Consequence:** fewer than half of the dev outputs pass the checks. Most IndicTrans2 translations of advisories will therefore go to officer review (`blocked` or `pending_review`), which is the intended safety behaviour.

## ADR-015: Local CUDA PyTorch only in `ml/` as an opt-in extra
- **Status:** accepted (2026-11-13, user request)
- **Context:** The laptop has an RTX 2050 (4 GB, driver CUDA 13.3). Training phases (9, 10) need a GPU. The backend container serves on CPU, and IndicConformer CPU latency was measured as acceptable (RTF 0.25, run `3d65e68d0266`).
- **Decision:** `ml/` has a `gpu` extra (torch 2.14.x from PyTorch's cu130 index, torchvision, timm), with `scripts/check_gpu.py` to verify it. The backend keeps CPU torch. Providers already honour `ML_DEVICE=auto|cpu|cuda`.
- **Consequences:**
  - The 4 GB of VRAM limits training to compact models with AMP.
  - GPU scripts must use `uv run --extra gpu`.
- **Update (2026-11-13, user request):** the backend also gets an opt-in `gpu` extra (`uv sync --extra local-ml --extra gpu`, torch 2.14.1+cu130). Without it, torch stays the PyPI CPU build, which is what the container uses. Measured on the RTX 2050 against the same dev configuration on the laptop CPU:

  | Model | CPU ms/sentence (`8b5381fbede6`) | GPU ms/sentence (`eee4fcb9d0c8`) | Speed-up | Check pass rate |
  |---|---|---|---|---|
  | IndicTrans2 en→te | 5217 | 1356 | 3.8× | 0.317, identical |
  | IndicTrans2 en→hi | 4101 | 771 | 5.3× | 0.488, identical |

  IndicConformer STT is an ONNX export run by ONNX Runtime on the CPU, so the CUDA PyTorch build does not accelerate it. Run `be5141cad716` (local, `ML_DEVICE=cuda`) gave the same CER as the CPU run but slower latency (te 9.2 s / hi 8.0 s median versus 2.2 / 2.3 s), which points to CPU contention during that run rather than a device effect. Using the GPU for STT would need `onnxruntime-gpu` (not installed).

## ADR-016: Conversation = deterministic dialogue manager around the agent runtime
- **Status:** accepted (Phase 3)
- **Context:** Farmers ask short, partial questions ("leaves have spots") in te/hi/en and answer clarifications with one word, a district name or a tap. LLM-only dialogue state would be unauditable and would need farmer text sent off-device.
- **Decision:** `app/conversation/` runs the turn loop: NLU, then required slots per intent (`REQUIRED_SLOTS`), then a clarification with catalog/LGD choices, then the original question resumed, then the agent runtime in English, then the answer translated back. State (crop, district, season, pending clarification) lives in Redis (24 h TTL) or memory. A reply that does not fill the pending slot and is not a new farming question (smalltalk / out of scope) re-asks the same slot and keeps the original question. Untranslatable or ungrounded answers are shown in English with a notice and go to officer review. Every turn is persisted (`conversation_turn`) with providers, slots and citations.
- **Evidence:** dialogue eval `98898e7cfba1` (result of record) task success 0.90; after the re-ask fix, post-hoc run `8db2250e2287` 0.933. The fix came from failures seen on that set, so the second number is not an independent estimate.

## ADR-017: Assisted mode requires an assignment and recorded consent; answers are reviewed before sharing
- **Status:** accepted (Phase 3, F6)
- **Decision:** an `extension_worker` may act for a farmer only with an active `extension_assignment` and `consent_status=granted`, recorded with a method (`verbal_recorded | signed_form | otp | in_app`) and evidence (DPDP). Act-as turns are stored with `acting_for_farmer_id` and `shared_with_farmer=false`. The worker shares or discards each answer, and the UI does not allow sharing an answer that still needs officer review.

## ADR-018: How-to media is attached only when verified and licensed
- **Status:** accepted (Phase 3, F7)
- **Decision:** `media_asset` rows are created by officers and stay `pending` until verified. Verification requires a licence. Matching needs a crop match (for crop-specific assets) and topic overlap, prefers the farmer's language, and attaches at most 2 assets, only to answered turns. A verified transcript is ingested as a knowledge document so the same content is citable.

## ADR-019: Cross-lingual retrieval with a multilingual embedder (multilingual-e5-small)
- **Status:** proposed (Phase 3). Adopting it requires re-embedding the knowledge base, which waits for approval.
- **Context:** the knowledge base is English, but farmers ask in te/hi. The current embedder (all-MiniLM-L6-v2) cannot match Indic queries.
- **Evidence:** run `bf4365b06b28` on FLEURS test parallel sentences: 350-sentence English corpus, te 302 / hi 265 queries, CPU.

  | Strategy | te R@1 | hi R@1 | te MRR | hi MRR | Translate ms/query |
  |---|---|---|---|---|---|
  | A all-MiniLM-L6-v2 (current) | 0.146 | 0.008 | 0.183 | 0.033 | — |
  | B paraphrase-multilingual-MiniLM-L12-v2 | 0.258 | 0.993 | 0.299 | 0.995 | — |
  | C multilingual-e5-small | 0.993 | 0.996 | 0.996 | 0.998 | — |
  | D IndicTrans2, then all-MiniLM | 0.997 | 0.996 | 0.998 | 0.998 | 3413 / 2284 |

- **Decision (proposed):** use C for retrieval. It matches D within noise, with no 2–3 s translation step per query, and it keeps the current 384-dimension vectors, so no schema change. Passages are indexed with the `passage: ` prefix and queries use `query: `. Keep D (translate-first) available as a fallback.
- **Caveats:**
  - FLEURS is general-domain and near ceiling, so it does not separate C from D. An agricultural te/hi query set (pending native review) must confirm the choice before it is final.
  - Embedding times in this run are noisy because other jobs shared the CPU; only the translation cost is a reliable latency difference.

## ADR-020: Govt Connect targeting, delivery and lifecycle
- **Status:** accepted (Phase 4)
- **Decision:**
  - **Targeting:** a farmer matches by registered district or any saved location (F2). Block-targeted bulletins match farmers with a saved location in a listed block (`block`), and farmers in the district whose block is unknown (`district`, so a warning is never missed for missing data). Farmers whose known blocks are all outside the list are excluded. Crop filters exclude only farmers whose recorded crops do not overlap; farmers with no recorded crops are included. Language: preferred if a deliverable translation exists, else English, else the original.
  - **Delivery:** through `NotificationService`, so preferences and quiet hours apply. CRITICAL maps to URGENT priority (bypasses quiet hours) only when `GOVCONNECT_CRITICAL_BYPASS_QUIET_HOURS` is true. A farmer who already holds an active same-hazard bulletin for an overlapping district gets the new one in the inbox without a second notification.
  - **Lifecycle:** draft → needs_review → approved → scheduled → published → withdrawn / superseded / expired. Published bulletins are immutable: corrections go through supersede. Every action writes `govconnect_audit`.
  - **RAG:** published bulletins are indexed with `effective_from` / `effective_until` (retrieval already drops expired chunks). Withdrawn and superseded bulletins are expired in Postgres and Qdrant at once; the maintenance job retries failures.
  - **Authority:** the inbox always shows the issuing authority, issue date and validity, and the official original is one tap away. AI only translates; it never rewrites an instruction.

## ADR-021: Bulletin extraction is rule-based first, with character-span provenance
- **Status:** accepted (Phase 4)
- **Context:** the brief asks for LLM extraction, but the free Gemini tier is exhausted and bulletins pasted by officers may contain farmer context.
- **Decision:** `rules-v1` (local, deterministic) extracts:
  - authority and level, issue and validity dates (IST, cue words in en/hi/te, "next N hours");
  - LGD districts and blocks (issuer office names and word-collision names excluded) and catalog crops;
  - hazard (first mentioned is primary), severity from IMD colour codes (yellow MEDIUM, orange HIGH, red CRITICAL), and advice sentences.

  Every value links to the exact source spans. Values below 0.7 confidence are flagged, and uploads always go to officer review. An LLM extractor can implement the same protocol and be compared on the same labelled set.
- **Known gap:** te/hi district names are not in the LGD reference, so Indic-script district mentions are not resolved (same gap as dialogue te04).

## ADR-022: Grievances and schemes: configurable SLA, officer-verified eligibility, no scraping
- **Status:** accepted (Phase 4, F4)
- **Decision:**
  - **Grievances:** tickets follow open → assigned → in_progress → resolved / rejected → closed, and the farmer can reopen once. Resolve and reject need a note. SLA hours per category come from `GRIEVANCE_SLA_HOURS`; these are configurable defaults, not official service standards. Public updates notify the farmer; internal notes stay hidden. Ticket text is personal data and stays on the device.
  - **Schemes:** the catalog is officer-maintained, and every eligibility criterion cites its source. Bundled entries (PM-KISAN) are DRAFTS, invisible to farmers until an officer verifies each criterion against `source_url`. Results are labelled "guidance only". Personal status is a link to the official portal; nothing is looked up or scraped.

## ADR-023: Automated official feeds, and cross-checking values across sources
- **Status:** accepted (Phase 5; source use approved by the user on 2026-11-13 and 2026-11-14)
- **Decision:**
  - **SACHET:** NDMA SACHET CAP feeds (national plus Telangana; public domain) are polled every 10 min.
    - **Fields:** official structured CAP fields (severity, LGD districts, validity, sender) are used as-is; the text extractor only adds advice and crops.
    - **Skipped:** exercises, expired alerts, unsupported languages and alerts outside the service area (cached so they are not refetched).
    - **Review:** feed bulletins go to officer review by default. `GOVCONNECT_FEED_AUTO_PUBLISH` publishes only LOW/MEDIUM alerts whose translations pass the checks.
  - **Weather:** the district forecast (Open-Meteo, CC BY 4.0) is cross-checked hourly against NASA POWER (independent; about 2-day lag) on the last 7 days.
    - **Verdict:** `agree` when max-temperature MAE ≤ 2.5 °C and rainfall totals differ by ≤ max(10 mm, 30%); otherwise `disagree`, or `unverified` with fewer than 3 overlapping days.
    - **Display:** the verdict travels with every snapshot, event and SMS. Official warnings always outrank model forecasts in the UI.
  - **No invented values:** missing provider fields are dropped or reported, never filled with defaults (Open-Meteo previously returned 25 °C / 50% / 1013 hPa when fields were missing). The spray window is computed from the forecast (wind ≤ about 15 km/h, rain chance < 40%), not hard-coded.
  - **Prices:** MSP comes only from `ml/reference/msp.csv`, transcribed from the PIB release (Kharif 2026-27) with its URL; a crop without a row shows no MSP. Mock market data is labelled synthetic. The real Agmarknet adapter (data.gov.in) fails loudly without a key.
- **Rejected:**
  - **IMD agromet district bulletins:** an interactive form with MoES copyright and no stated reuse terms, so they stay on officer upload.
  - **IMD API:** needs a key or IP whitelisting.
  - **CWC flood forecasts and UPAg:** no public API found.
  - **myScheme:** its terms forbid bots.

## ADR-024: Feature-phone channels, web push and DPI behind sandbox adapters
- **Status:** accepted (Phase 5, F1/F5)
- **Decision:**
  - **Channels:** SMS (GSM-7/UCS-2 segmenting, at most 3 parts, localized reply-keyword footer), IVR (provider-neutral call scripts) and WhatsApp sit behind `NotificationService`. Only sandbox adapters exist: they compose the exact message into an outbox with pseudonymised recipients and send nothing. Real providers need a contract and cost approval.
  - **Inbound:** inbound SMS/IVR webhooks are officer-only harnesses until a provider with signed callbacks is chosen.
  - **Web push:** uses VAPID. It sends only when keys are configured; payloads are end-to-end encrypted, so the push service only relays ciphertext.
  - **DPI:** AgriStack (consent-gated), Bharat-VISTAAR and Bhashini are interfaces with sandbox adapters that return no data with a reason, never fabricated records.
