# Phase 3: Multilingual Bot Report (+F6, F7, F13)

- **Date:** 2026-11-13
- **Branch:** `feat/sprint-11-phase3-bot`
- **Scope:** the conversation manager (text and voice), assisted mode for extension workers (F6), verified how-to media (F7), the answer feedback loop (F13), the Ask page and officer UIs, and a cross-lingual retrieval decision.

**Integrity notes.**
- Every number here comes from code run in this session and is logged in `ml/experiments/*.jsonl` under its `run_id`, with artifacts in `ml/reports/data/`.
- Dialogue scripts and all hi/te UI strings are **drafts** that have not been reviewed by native speakers.

## 1. What was built

| Component | Where | Notes |
|---|---|---|
| Conversation manager | `backend/app/conversation/` | Turn loop: NLU → required slots per intent → clarification with catalog/LGD choices → resume the original question → agent runtime (English) → translate out. Re-asks when a reply does not fill the slot. Optional TTS. Every turn is audited in `conversation_turn`. State in Redis (24 h) or memory. ADR-016 |
| API | `/conversation/turns`, `/voice-turns`, `/{id}`, `/audio/{uuid}` | Voice: STT with a language hint feeds the same flow; the response returns the transcript |
| Assisted mode (F6) | `backend/app/extension/`, `pages/officer/ExtensionPage.tsx` | `extension_worker` role. Assignment plus recorded consent (method and evidence) is required to act for a farmer. Review-before-share queue. Batch registration of up to 50 farmers. ADR-017 |
| Media (F7) | `backend/app/media/` | Licence required to verify an asset. Matching needs crop and topic; at most 2 per answer. A verified transcript is ingested as a knowledge document. ADR-018. **No assets loaded yet.** |
| Feedback (F13) | `backend/app/feedback/`, `pages/officer/FeedbackDashboardPage.tsx` | Thumbs up/down with a reason. A down-vote puts the turn in officer review. Summary by language and intent, triage, and JSONL regression-case export |
| Ask page | `frontend/src/features/conversation/`, `pages/farmer/AskPage.tsx` | The chat is the default view; the old workspace is one click away. te/hi/en switcher (the UI language follows it), voice in, spoken replies, clarification chips, citations, media cards, feedback, and notices for an unverified translation or a pending review |
| Demo defaults removed | farmer pages, AI components | No more `'Paddy'`, `'Khammam'`, `'Kharif'` or `'Telangana'` fallbacks; a new `usePrimaryCropName()` hook supplies the farmer's crop |
| Model preload | `backend/app/providers/preload.py` | `PRELOAD_MODELS=true` loads the configured local models in a background thread at startup (cold load was about 78 s). Failures do not stop startup |
| Migration | `0011_sprint_11_phase3_bot.py` | Creates `conversation_turn`, `extension_assignment`, `answer_feedback` and `media_asset`; up/down/up verified on Postgres 16 |

## 2. Dialogue evaluation

- **Harness:** `ml/scripts/run_dialogue_eval.py`, running 30 scripted dialogues (10 each in te, hi and en; 42 turns).
- **What it measures:** dialogue management only (intent, slots, clarification, resumption, carry-over, refusal). The agent runtime is replaced by a fixed grounded answer, so answer quality is not measured here.
- **Pass rule:** a dialogue passes only if every turn meets every expectation.

| Run | Status | Task success | te | hi | en | Turn accuracy |
|---|---|---|---|---|---|---|
| `98898e7cfba1` | **result of record** | **0.900** | 0.9 | 0.9 | 0.9 | 0.929 |
| `8db2250e2287` | post-hoc, after the re-ask fix | 0.933 | 0.9 | 1.0 | 0.9 | 0.952 |

The post-hoc run is not an independent estimate, because the fix was prompted by failures on this same set (ADR-013).

Failures in the result of record:
- **te04:** the Telugu-script district reply "ఖమ్మం" is not in the LGD reference, so the pending clarification was lost and the turn was refused.
  - After the fix, the bot re-asks instead, but the dialogue still fails.
  - Fixing it needs native-reviewed te/hi district names.
- **hi07:** the ambiguous "Bilaspur" reply lost the yield question. This is fixed by the re-ask, which now offers the district choices.
- **en09:** "agriculture department … rains" was classified as `weather` instead of `govt_bulletin`. This is the known lexicon gap; fixing it needs a dev set.

## 3. Cross-lingual retrieval decision (ADR-019, proposed)

- **Run:** `bf4365b06b28`.
- **Benchmark:** FLEURS test parallel sentences (CC BY 4.0). The corpus is 350 English sentences; each te (302) or hi (265) query has exactly one correct English match.

| Strategy | te R@1 | te R@10 | hi R@1 | hi R@10 | te / hi MRR | Translate ms/query |
|---|---|---|---|---|---|---|
| A all-MiniLM-L6-v2 (current) | 0.146 | 0.232 | 0.008 | 0.091 | 0.183 / 0.033 | — |
| B paraphrase-multilingual-MiniLM-L12-v2 | 0.258 | 0.378 | 0.993 | 0.996 | 0.299 / 0.995 | — |
| C multilingual-e5-small | 0.993 | 1.000 | 0.996 | 1.000 | 0.996 / 0.998 | — |
| D IndicTrans2 → all-MiniLM | 0.997 | 1.000 | 0.996 | 1.000 | 0.998 / 0.998 | 3413 / 2284 |

What the results show:
- The current setup (A) **cannot serve Indic queries at all**.
- B handles Hindi but not Telugu.
- C and D are both near ceiling. **Recommendation: C**, because it avoids D's 2–3 s CPU translation per query and keeps 384-dimension vectors.

Caveats:
- **The data is general-domain.** An agricultural te/hi query set is still needed to confirm the choice.
- **Embedding latency is noisy.** The CPU was shared with other jobs during the run.
- **First attempt aborted.** Run 1 stopped after strategy A when a model download dropped mid-transfer (network). This run is a complete rerun with the same configuration.

## 4. Tests

- **Backend:** 251 passed, 3 skipped. Postgres integration tests 3/3 passed. New tests cover the re-ask behaviour, an ambiguous-district resume and preload outcomes.
- **Frontend:** 29 files / 63 tests passed. Typecheck clean, lint 0 errors, build OK. New tests cover the chat (language, chips, notices, feedback, media) and the extension and feedback pages (consent gating, review blocks sharing, triage, line parser).
- **Ruff:** Phase 3 files are clean. Older code still has about 430 pre-existing findings.

## 5. Not done / known gaps

- **Deployable TTS** (IndicF5 / Indic Parler-TTS) was not evaluated. MMS-TTS remains demo-only (CC BY-NC).
- **F7 has no media yet.** No media assets are loaded, so the matching path is tested only with fixtures.
- **Retrieval switch** (re-embed the knowledge base with e5-small) is **awaiting approval**.
- **Native review** is needed for the hi/te UI strings, the dialogue scripts, and te/hi district names.

## 6. Approvals requested

1. Adopt ADR-019 and re-embed the knowledge base with multilingual-e5-small. This is local and reversible through index versions.
2. Commit Phase 3 on `feat/sprint-11-phase3-bot`. Nothing will be pushed.
