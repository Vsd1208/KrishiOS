# KrishiOS Next Level: Progress Tracker

Read this file at the start of every session, and update it at the end of every session.

**Status values:** `todo` · `in-progress` · `done` · `blocked-on-approval` · `blocked`

**Last updated:** 2026-11-13. All AI4Bharat models are downloaded (IndicTrans2 x2, IndicConformer-600M, MMS te/hi). Benchmarks were stopped by the user, to be restarted later.

### Resume here (benchmarks, in order; run from `backend/`)
1. **Fix first:** IndicTrans2 destroys `<i>` placeholders (survival 1/533 in an *unlogged, stopped* run). With protection only 1.3% of te outputs passed checks; without protection 84.2% kept numbers. Make the placeholder format per provider: try IndicTrans2's native `<ID{n}>` on a 6-sentence probe, then re-run.
2. `HF_HUB_OFFLINE=1 uv run --extra local-ml --with sacrebleu python ../ml/scripts/run_mt_eval.py --providers indictrans2 --targets te hi` (about 45 min)
3. `HF_HUB_OFFLINE=1 uv run --extra local-ml --with jiwer python ../ml/scripts/run_stt_eval.py --provider indicconformer-600m-rnnt --languages te hi --n 30 --seed 13` (about 20-30 min)
4. `HF_HUB_OFFLINE=1 uv run --extra local-ml --with jiwer python ../ml/scripts/run_tts_eval.py --tts mms-tts --stt faster-whisper-small --languages te hi --n 20 --seed 13` (about 20-30 min)
5. Add the results to `ml/reports/02_multilingual_core.md` §3 and choose the default providers from the numbers.

## Phases

| Phase | Status | Branch | Evidence |
|---|---|---|---|
| 0 Orientation & sourcing | done | `feat/sprint-11-phase0-orientation` | [00_orientation.md](../ml/reports/00_orientation.md) |
| 1 Foundations | done | `feat/sprint-11-phase1-foundations` | [01_foundations.md](../ml/reports/01_foundations.md) |
| 2 Multilingual core | done (AI4Bharat benchmarks pending download) | `feat/sprint-11-phase2-multilingual` | [02_multilingual_core.md](../ml/reports/02_multilingual_core.md) |
| 3 Multilingual bot (+F6, F7, F13) | todo | — | — |
| 4 Govt Connect: publishing (+F2, F4) | todo | — | — |
| 5 Govt Connect: automated (+F1, F3, F5) | todo | — | — |
| 6 Yield label audit | todo | — | — |
| 7 Yield predictor pipeline | todo | — | — |
| 8 Yield baselines & integration (+F15) | todo | — | — |
| 9 Real computer vision (+F8) | todo | — | — |
| 10 KrishiOS yield model & research | todo | — | — |
| 10b Farmer toolkit (F9–F12, F14, F7 video) | todo | — | — |
| 11 Golden journeys, docs, write-up | todo | — | — |

## Adopted features

| # | Feature | Phase | Status | Notes |
|---|---|---|---|---|
| F1 | DPI interoperability adapters | 0 → 5 | in-progress (investigated) | Orientation §8 |
| F2 | Block / GP locations | 4–5 | in-progress | LGD blocks reference (7,327) + `/catalog/districts/{code}/blocks` done in Phase 1 |
| F3 | Offline-first PWA | 5 | todo | |
| F4 | Scheme assistant + grievance tickets | 4 | todo | No public scheme API; no scraping |
| F5 | IVR / SMS / WhatsApp channels | 5 | todo | Real providers blocked-on-approval (cost) |
| F6 | Extension-worker assisted mode | 3 | todo | |
| F7 | Video / how-to answers + video queries | 3, 10b | todo | |
| F8 | Outbreak surveillance heatmaps | 9 | todo | |
| F9 | SHC reader + fertilizer calculator | 10b | todo | |
| F10 | Crop calendar + reminders | 10b | todo | Spray-window golden test fixed in Phase 1 |
| F11 | Mandi price intelligence | 10b | todo | Needs data.gov.in key |
| F12 | Community Q&A | 10b | todo | |
| F13 | Answer feedback loop | 3 | todo | |
| F14 | Livestock / fisheries advisories | 10b | todo | Catalog has a `domain` column ready |
| F15 | Insurance helper | 8 | todo | |

## Pillar components

| Component | Status | Notes |
|---|---|---|
| Crop catalog (`catalog/`) | done (data in draft review) | 53 crops; te/hi names need native review |
| LGD crosswalk | in-progress | LGD districts and blocks done; APY/ICRISAT name crosswalk is Phase 6 |
| Provider selection + visible provider/version | done | `/api/v1/providers`, canvas Providers tab |
| Worker service + job health | done | arq; `/api/v1/health/jobs`; verified on real Redis |
| Translation service | done | Protection + checks + approval; opus-mt measured (fails checks on ~2/3 of sentences); IndicTrans2 built, measurement pending download |
| NLU | done | Rule-based: intent acc 0.796, crop F1 0.968 (run b74f7a0eb8c7; draft labels); planner routes on NLU |
| Real STT / TTS | in-progress | Whisper-small measured (te CER 0.987: unusable); IndicConformer built, pending 2.56 GB download; MMS-TTS demo-only (CC BY-NC) |
| Conversation / dialogue state | todo | Phase 3 |
| Govt Connect | todo | SACHET CAP preferred feed (ADR-004) |
| Yield Intelligence | todo | |
| Real vision | todo | Field-photo dataset gap |

## Known debt (tracked)

- About 15 frontend demo defaults (`'Paddy'`, `'Khammam'`) remain. Removed in Phase 3 via conversation state.
- About 430 pre-existing ruff findings in older backend code (new Sprint 11 code is clean).

## Test status (latest)

- **Backend:** 219 passed, 0 failed (Phase 2 end).
- **ml:** 13 passed.
- **Frontend:** 27 files / 53 tests passed; build OK.

## Pending approvals and actions

Orientation report §12 and Phase 2 report §7. Status:
- Hugging Face access: **granted** 2026-11-12. Downloads (about 4.9 GB) are in progress at about 0.2 MB/s.
- Gemini key is free tier and quota-exhausted: billed key decision pending.
- Native reviewers (NLU labels, MT references, TTS ratings): pending.
