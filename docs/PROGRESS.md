# KrishiOS Next Level: Progress Tracker

Read this file at the start of every session, and update it at the end of every session.

**Status values:** `todo` · `in-progress` · `done` · `blocked-on-approval` · `blocked`

**Last updated:** 2026-11-15. **Phase 8 is complete (awaiting review).** Phases 0-7 are merged to `main`; Phase 8 onward is on `feat/sprint-11-phase8-yield-models`. Next: Phase 9 (real computer vision).

## Phases

| Phase | Status | Branch | Evidence |
|---|---|---|---|
| 0 Orientation & sourcing | done | `feat/sprint-11-phase0-orientation` | [00_orientation.md](../ml/reports/00_orientation.md) |
| 1 Foundations | done | `feat/sprint-11-phase1-foundations` | [01_foundations.md](../ml/reports/01_foundations.md) |
| 2 Multilingual core | done | `feat/sprint-11-phase2-multilingual` | [02_multilingual_core.md](../ml/reports/02_multilingual_core.md) |
| 3 Multilingual bot (+F6, F7, F13) | done (awaiting review) | `feat/sprint-11-phase3-bot` | [03_multilingual_bot.md](../ml/reports/03_multilingual_bot.md) |
| 4 Govt Connect: publishing (+F2, F4) | done (awaiting review) | `feat/sprint-11-phase4-govconnect` | [04_govconnect_publishing.md](../ml/reports/04_govconnect_publishing.md) |
| 5 Govt Connect: automated (+F1, F3, F5) | done (awaiting review) | `feat/sprint-11-phase4-govconnect` | [05_govconnect_automated.md](../ml/reports/05_govconnect_automated.md) |
| 6 Yield label audit | done (**awaiting scope freeze**) | `feat/sprint-11-phase4-govconnect` | [06_yield_label_audit.md](../ml/reports/06_yield_label_audit.md) |
| 7 Yield predictor pipeline | done (weather); **NDVI pending at NASA**; scope-freeze defaults need sign-off | `feat/sprint-11-phase4-govconnect` | [07_yield_predictor_pipeline.md](../ml/reports/07_yield_predictor_pipeline.md) |
| 8 Yield baselines & integration (+F15) | done (awaiting review) | `feat/sprint-11-phase8-yield-models` | [08_yield_baselines.md](../ml/reports/08_yield_baselines.md) |
| 9 Real computer vision (+F8) | todo | — | — |
| 10 KrishiOS yield model & research | todo | — | — |
| 10b Farmer toolkit (F9–F12, F14, F7 video) | todo | — | — |
| 11 Golden journeys, docs, write-up | todo | — | — |

## Adopted features

| # | Feature | Phase | Status | Notes |
|---|---|---|---|---|
| F1 | DPI interoperability adapters | 0 → 5 | done (sandbox) | AgriStack (consent-gated), Bharat-VISTAAR, Bhashini interfaces; sandbox until access (ADR-024) |
| F2 | Block / GP locations | 4–5 | in-progress | Saved farmer locations with LGD block validation; block-level bulletin targeting (Phase 4). Block-level weather feeds: Phase 5 |
| F3 | Offline-first PWA | 5 | done | Service worker: app shell + weather feed / inbox / crop list readable offline; questions queued offline and sent on reconnect |
| F4 | Scheme assistant + grievance tickets | 4 | done | Grievance tickets with SLA; officer-verified scheme catalog + eligibility Q&A (PM-KISAN draft awaiting officer verification). No public scheme API; no scraping |
| F5 | IVR / SMS / WhatsApp channels | 5 | done (sandbox) | SMS segmenting + keywords, IVR scripts, WhatsApp; sandbox adapters; real providers need cost approval (ADR-024) |
| F6 | Extension-worker assisted mode | 3 | done | Assignment + recorded consent, act-as, review-before-share, batch registration (ADR-017) |
| F7 | Video / how-to answers + video queries | 3, 10b | in-progress | Verified, licensed media matched to answers (ADR-018); no assets loaded yet; video queries in 10b |
| F8 | Outbreak surveillance heatmaps | 9 | todo | |
| F9 | SHC reader + fertilizer calculator | 10b | todo | |
| F10 | Crop calendar + reminders | 10b | todo | Spray-window golden test fixed in Phase 1 |
| F11 | Mandi price intelligence | 10b | todo | Needs data.gov.in key |
| F12 | Community Q&A | 10b | todo | |
| F13 | Answer feedback loop | 3 | done | Thumbs + reasons, down-vote to officer review, dashboard, triage, regression export |
| F14 | Livestock / fisheries advisories | 10b | todo | Catalog has a `domain` column ready |
| F15 | Insurance helper | 8 | done (draft content) | PMFBY draft scheme entry + sourced guidance (`app/schemes/insurance_guidance.yaml`), shown to farmers only after officer verification; yield context labelled not YES-TECH/claim. 72-hour / 14-day items still need an official source |

## Pillar components

| Component | Status | Notes |
|---|---|---|
| Crop catalog (`catalog/`) | done (data in draft review) | 53 crops; te/hi names need native review |
| LGD crosswalk | done | LGD districts and blocks; APY carries LGD codes (Phase 6); district polygons 730/735 coded (Phase 7, 60 reviewed overrides) |
| Provider selection + visible provider/version | done | `/api/v1/providers`, canvas Providers tab |
| Worker service + job health | done | arq; `/api/v1/health/jobs`; verified on real Redis |
| Translation service | done | IndicTrans2 recommended: test check pass te 0.550 / hi 0.644 (run 2c5c6baf993a), vs opus-mt 0.350 / 0.375 (a839daa3ac6c); failures blocked to officer review |
| NLU | done | Rule-based: intent acc 0.796, crop F1 0.968 (run b74f7a0eb8c7; draft labels); planner routes on NLU |
| Real STT / TTS | done | IndicConformer RNNT recommended: FLEURS CER te 0.073 / hi 0.063 (65d3ea90da08); CPU median 2.2 s/utterance, RTF 0.25 (3d65e68d0266). MMS-TTS demo-only (CC BY-NC); deployable voice in Phase 3 |
| Conversation / dialogue state | done | Clarify-and-resume, carry-over, re-ask; dialogue task success 0.90 (run 98898e7cfba1, result of record; draft scripts); text + voice turns; optional preload (`PRELOAD_MODELS`) |
| Govt Connect | in-progress | Publishing side done (Phase 4): upload/compose → extraction with provenance → translate → approve/schedule → targeted delivery → inbox (listen / ask / ack / flag) → RAG with validity → analytics. Automated feeds: Phase 5 (SACHET CAP preferred, ADR-004) |
| Yield Intelligence | in-progress | B3 multi-crop LightGBM serving: test median nMAE 0.237-0.242 vs 0.273 historical mean; unseen districts 0.222 vs 0.267 (run 37dc01be91cf); 80% intervals cover 0.81-0.85. Forecast import, outlook page, bot card, shortfall drafts. NDVI pending at NASA |
| Real vision | todo | Field-photo dataset gap |

## Known debt (tracked)

- Frontend demo defaults (`'Paddy'`, `'Khammam'`, `'Kharif'`, `'Telangana'`) removed from farmer-facing code in Phase 3. The officer broadcast form keeps an editable example template.
- Telugu/Hindi-script district names are not in the LGD reference, so a reply like "ఖమ్మం" is re-asked instead of resolved (dialogue te04). Needs a native-reviewed name list.
- `govt_bulletin` vs `weather` lexicon gap (dialogue en09, NLU test set). Fix needs a dev set (ADR-013).
- About 430 pre-existing ruff findings in older backend code (new Sprint 11 code is clean).

## Test status (latest)

- **Backend:** 279 passed, 8 skipped (Phase 5); Postgres integration 8 passed.
- **ml:** 13 passed.
- **Frontend:** 31 files / 70 tests passed; typecheck, lint (0 errors) and build OK.

## Pending approvals and actions

Orientation report §12 and Phase 2 report §7. Status:
- Hugging Face access: **granted**; all models downloaded (2026-11-13).
- Gemini key is free tier and quota-exhausted: billed key decision pending.
- Native reviewers (NLU labels, MT references, TTS ratings): pending.
