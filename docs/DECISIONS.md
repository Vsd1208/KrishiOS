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
