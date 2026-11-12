# Phase 1: Foundations Report

- **Date:** 2026-11-12
- **Branch:** `feat/sprint-11-phase1-foundations`
- **Ran:** without a stop between Phase 1 and Phase 2, on the user's instruction ("go with the next 2 phases unasked").
- **Approval gates:** reversible defaults were taken in place of asking. They are listed in §5.

## 1. What was done

| Item | Result | Where |
|---|---|---|
| Green test baseline | Fixed the uncollectable module (undeclared `psutil`) and the 6 failures. 3 were stale tests (agent count 7, an `AsyncMock` misuse, a mock hit missing `similarity`/`metadata`). 1 was a real gap: the graph extractor missed "the disease …" anaphora. | `5aae772` |
| `ml/` uv project | Separate project containing: seeding, logging, JSONL experiment log (config, seed, split, git commit, metrics, wall-clock, artifact), catalog validator, LGD builder, and tests. | `ml/`, `d4fbb81` |
| Crop catalog | 53 crops with en/te/hi names, multilingual aliases, groups, seasons, yield units and APY names. `tier=unassigned` until Phase 6. `review_status=draft`: **native-speaker review pending**. | `ml/reference/crop_catalog.csv` |
| LGD reference | 790 districts and 7,327 blocks (latest block version kept; 16 superseded versions dropped) from the LGD snapshot observed 2026-11-12, licence GODL. Includes Census 2001/2011 codes for crosswalks. | `ml/reference/lgd_*.csv` |
| Backend `catalog/` | Multilingual resolver: token-based, Indic suffix-aware, plural-aware, longest match. Shared aliases (e.g. *gobhi*) give `ambiguous` and a picker, never a guess. LGD lookup by code, name and state. API under `/api/v1/catalog`. | `app/catalog/` |
| Migration 0009 | Additive only: `crop_catalog` table; nullable `lgd_district_code`/`lgd_state_code`/`census_2011_code` on `district`; `catalog_canonical` on `crop`. | `migrations/versions/0009_…` |
| Seed / backfill | Idempotent upsert of the catalog, plus LGD and catalog backfill. Ambiguous or unmatched rows are reported, never guessed. | `scripts/seed_reference_data.py` |
| Provider selection | `ProviderSelector` and `ProviderInfo` (live / sandbox / mock, off-device flag). New settings `VISION_/STT_/TTS_/TRANSLATION_/NLU_/YIELD_PROVIDER`; old env names still accepted. **Unknown names raise** (the registry no longer falls back silently). Agmarknet/Agromet placeholders are now labelled **mock**. `GET /api/v1/providers`. Startup guard: mocks and off-device providers are policy violations, and fatal in `production`. | `app/providers/` |
| UI provider badges | "Providers" tab in the Intelligence Canvas, with live/sandbox/mock badges and an off-device disclosure, in en/hi/te. The canvas no longer shows a silent "Paddy (Khammam)". | `frontend/…/ProviderTransparencyPanel.tsx` |
| Voice fixes | Respects `LLM_PROVIDER` (was hard-coded to the mock LLM). No silent `"Paddy"` crop. The mock STT matches whole filename tokens, so `test.wav` is no longer Telugu. | `app/voice/` |
| Worker service | arq on Redis. `JobSpec` and `run_job` give per-slot idempotency (`SET NX`), slot release on failure (so arq retries), skip vs. failure, and run records. Health classes: ok / stale / failing / never_run, with freshness lag. `GET /api/v1/health/jobs`. Added a `worker` service to docker-compose; `ml/reference` and `ml/artifacts` are mounted read-only. | `app/worker/`, `docker-compose.yml` |
| Repo hygiene | `git rm` of the garbled root file, `cotton_health.txt`, `rag-body.json` and `metadata.json` (recoverable from history). Debug scripts moved to `backend/scripts/dev/`. Untracked files outside the repo were **not** touched. | `9d9ab94` |

## 2. Evidence

All of the following were run in this session.

| Check | Command | Result |
|---|---|---|
| Backend tests | `cd backend && uv run pytest -q` | **168 passed, 0 failed** (105 s) |
| ml tests | `cd ml && uv run pytest -q` | 9 passed |
| Frontend tests | `cd frontend && npx vitest run` | 27 files / 53 tests passed |
| Frontend build | `npm run build` | success |
| Lint (new code) | `uv run ruff check <sprint-11 files>`; `npx eslint <new files>` | clean. The pre-existing backend code still has ~430 ruff findings; they are untouched and out of scope. |
| Migrations on real Postgres 16 | throwaway container; `alembic upgrade head` → `downgrade 0008` → `upgrade head` | all succeeded |
| Seed on real Postgres | `python -m scripts.seed_reference_data`, run twice | Run 1: 53 catalog upserts; Khammam → LGD 509; Bilaspur (Chhattisgarh) → 375; "Nowhere" unmatched; "Gobhi" left unlinked (ambiguous). Run 2: no new links (idempotent). |
| Worker on real Redis 7 | `arq app.worker.main.WorkerSettings` for 75 s | heartbeat `runs_ok=2`; `/health/jobs` → `status=ok`, `freshness_lag_seconds≈62` |
| Bug found by the real run | The seed script hit a **circular import** (`app.catalog.models` ↔ `app.models`) | fixed in `c23c5b0`, plus a regression test |

## 3. Test results

- **Backend:** 168 passed, 0 failed. The baseline was 112 passed / 6 failed / 1 uncollectable.
- **ml:** 9 passed.
- **Frontend:** 53 passed.

## 4. Known gaps, carried forward

- **Frontend demo defaults:** about 15 places still default to `'Paddy'`/`'Khammam'` (Ask page, dashboard, alerts, toolkit modals). These are removed in **Phase 3**, when the conversation state supplies the farmer's crop and district.
- **Not yet built:** `district_crosswalk.csv` (APY/ICRISAT names → LGD) and `crop_calendar.csv`. Both depend on the Phase 6 label audit.
- **Native review:** the catalog's te/hi names need native-speaker review.
- **Windows logging:** arq's own log lines contain arrows that the Windows `cp1252` console can't encode. Logging still works, and the Linux container is unaffected.

## 5. Decisions taken without asking (all reversible)

| Gate in the brief | What I did |
|---|---|
| "Ask before deleting files" | `git rm` of 4 tracked junk files only (recoverable), and a `git mv` of debug scripts. Did **not** touch `openapi.json`, the `walkthrough.md` files, or the 3 untracked files in `c:\KrishiOS`. |
| "Schema changes to existing tables" | Additive, nullable columns only (migration 0009). Downgrade tested. |
| "New heavyweight backend dependencies" | Added `arq` (pure Python, uses the existing `redis` client) and `psutil` (already imported by existing code). Nothing heavy. |
| Data downloads | LGD Parquet snapshot (≈0.1 MB). |
