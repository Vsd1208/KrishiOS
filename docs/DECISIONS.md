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
