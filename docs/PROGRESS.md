# KrishiOS Next Level: Progress Tracker

Read this file at the start of every session, and update it at the end of every session.

**Status values:** `todo` · `in-progress` · `done` · `blocked-on-approval` · `blocked`

**Last updated:** 2026-11-12. Phases 1 and 2 run back to back on the user's instruction.

## Phases

| Phase | Status | Branch | Evidence |
|---|---|---|---|
| 0 Orientation & sourcing | done | `feat/sprint-11-phase0-orientation` | [00_orientation.md](../ml/reports/00_orientation.md) |
| 1 Foundations | done | `feat/sprint-11-phase1-foundations` | [01_foundations.md](../ml/reports/01_foundations.md) |
| 2 Multilingual core | in-progress | `feat/sprint-11-phase2-multilingual` | — |
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
| Translation service | in-progress | Phase 2 |
| NLU | in-progress | Phase 2 |
| Real STT / TTS | in-progress | Phase 2. AI4Bharat models are **blocked-on-approval** (gated HF; no token on this machine) |
| Conversation / dialogue state | todo | Phase 3 |
| Govt Connect | todo | SACHET CAP preferred feed (ADR-004) |
| Yield Intelligence | todo | |
| Real vision | todo | Field-photo dataset gap |

## Known debt (tracked)

- About 15 frontend demo defaults (`'Paddy'`, `'Khammam'`) remain. Removed in Phase 3 via conversation state.
- About 430 pre-existing ruff findings in older backend code (new Sprint 11 code is clean).

## Test status (latest)

- **Backend:** 168 passed, 0 failed (Phase 1 end).
- **ml:** 9 passed.
- **Frontend:** 27 files / 53 tests passed; build OK.

## Pending approvals and actions

Orientation report §12. New since Phase 0:
- **Hugging Face access** for AI4Bharat gated models (IndicTrans2, IndicConformer, IndicF5, Indic Parler-TTS). There is no token on this machine.
