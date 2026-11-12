# KrishiOS Next Level: Progress Tracker

Read this file at the start of every session, and update it at the end of every session.

**Status values:** `todo` · `in-progress` · `done` · `blocked-on-approval` · `blocked`

**Last updated:** 2026-11-12. Phase 0 is complete and awaiting approval.

## Phases

| Phase | Status | Branch | Evidence |
|---|---|---|---|
| 0 Orientation & sourcing | done (awaiting approval) | `feat/sprint-11-phase0-orientation` | [ml/reports/00_orientation.md](../ml/reports/00_orientation.md) |
| 1 Foundations | todo | — | — |
| 2 Multilingual core | todo | — | — |
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
| F1 | DPI interoperability adapters | 0 → 5 | in-progress (investigated) | See orientation report §8 |
| F2 | Block / GP locations | 4–5 | todo | |
| F3 | Offline-first PWA | 5 | todo | |
| F4 | Scheme assistant + grievance tickets | 4 | todo | No public scheme API; no scraping (myScheme terms) |
| F5 | IVR / SMS / WhatsApp channels | 5 | todo | Real providers blocked-on-approval (cost) |
| F6 | Extension-worker assisted mode | 3 | todo | |
| F7 | Video / how-to answers + video queries | 3, 10b | todo | |
| F8 | Outbreak surveillance heatmaps | 9 | todo | |
| F9 | SHC reader + fertilizer calculator | 10b | todo | Needs real SHC photos (consent) |
| F10 | Crop calendar + reminders | 10b | todo | Spray-window golden test currently failing |
| F11 | Mandi price intelligence | 10b | todo | Needs data.gov.in key |
| F12 | Community Q&A | 10b | todo | |
| F13 | Answer feedback loop | 3 | todo | |
| F14 | Livestock / fisheries advisories | 10b | todo | |
| F15 | Insurance helper | 8 | todo | |

## Pillar components

| Component | Status | Notes |
|---|---|---|
| Crop catalog (`catalog/`) | todo | Seed from `graph/ontology/dictionaries.py` |
| LGD crosswalk | todo | |
| Provider selection by config + visible provider/version | todo | Registry silently falls back to mocks today |
| Worker service + job health | todo | |
| Translation service | todo | |
| NLU | todo | |
| Real STT / TTS | todo | Gated HF models need your account |
| Conversation / dialogue state | todo | |
| Govt Connect: bulletins, publishing, delivery, analytics | todo | SACHET CAP is the preferred warnings feed |
| Yield Intelligence | todo | |
| Real vision (crop ID + disease) | todo | Field-photo dataset gap |

## Baseline health (before Phase 1)

- **Backend:** 1 module fails to collect (`psutil` missing). Excluding it: 112 passed, 6 failed.
- **Frontend:** 26 files / 50 tests passed; build OK.

## Pending approvals and actions

See orientation report §12. All 12 items are open.
