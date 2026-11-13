# Phase 4: Govt–Farmer Connect, Publishing Side (+F2, F4)

- **Date:** 2026-11-14
- **Branch:** `feat/sprint-11-phase4-govconnect`
- **Scope:**
  - **Officer side:** bulletin ingestion with provenance, the publishing console (target, translate, approve, schedule, withdraw, supersede, audit), and delivery through `NotificationService`.
  - **Farmer side:** the Govt Updates inbox, and RAG indexing with validity.
  - **F2:** saved locations and block-level targeting.
  - **F4:** grievance tickets with SLA, and scheme eligibility Q&A.

**Integrity notes.**
- No extraction-accuracy, delivery or acknowledgement numbers are reported here.
  - The labelled set of real bulletins is not built yet (see §4).
  - Delivery and acknowledgement rates must come from real runs; there have been none.
- Every hi/te string is a **draft** pending native review. So is the PM-KISAN catalog entry, which is hidden from farmers until an officer verifies it.

## 1. What was built

| Component | Where | Notes |
|---|---|---|
| Data model | `app/models/govconnect.py`, migration `0012` | Bulletins (fields, provenance, extraction, lifecycle, supersede chain, RAG state), per-language translations with approval, deliveries (match level, notification status, read/ack/flag), audit log, farmer locations, grievance tickets and events, scheme catalog. Additive only; up/down/up verified on Postgres 16 |
| Extraction | `app/govconnect/extraction.py`, `lexicon.yaml` | `rules-v1`: authority and level, IST dates with cue words in en/hi/te and "next N hours", LGD districts and blocks (issuer office excluded, collision guard), catalog crops, hazard, severity from IMD colour codes, advice sentences. Character-span provenance for every value; low-confidence flags. ADR-021 |
| Lifecycle | `app/govconnect/service.py` | Create (upload via the existing parsers/OCR, or compose) → edit (re-extracts provenance) → translate (ADR-011 gates; HIGH/CRITICAL need approval; edits re-checked) → readiness → approve now or schedule → publish → withdraw / supersede / expire. Every step audit-logged |
| Targeting and delivery | `app/govconnect/targeting.py` | District, block, crop, segment and language rules (ADR-020). `NotificationService` handles preferences and quiet hours; CRITICAL bypasses quiet hours only if configured; overlapping same-hazard alerts are de-duplicated |
| RAG | `app/govconnect/indexing.py`, `api/routes/documents.py` | Published bulletins become `govt_bulletin` documents with `effective_from` / `effective_until` / `bulletin_uuid` on every chunk. Withdraw or supersede expires them in Postgres and Qdrant (`set_document_payload`) |
| Worker | `app/worker/jobs/govconnect.py` | `govconnect_maintenance` (every 5 min): publishes due items, expires old ones, retries index work |
| API | `/govconnect/*` (19 routes) | Officer console, analytics (recipients, notified, held back, read / ack / flag rates, questions per bulletin), flag queue; farmer inbox (read, ack, flag, listen via TTS). `/conversation/turns` accepts `bulletin_uuid` for "ask about this" |
| F2 | `/farmers/me/locations`, `LocationsCard` | Up to 10 places; the block must belong to its district (LGD); a primary place. `/catalog/districts?prefix=true` for pickers |
| F4 | `/grievances/*`, `/schemes/*` | Ticket state machine with SLA due and breach (configurable hours), public vs internal notes, farmer notified on updates, farmer close/reopen. Scheme catalog with sourced criteria; drafts hidden until verified; eligibility = guidance only plus an official-portal link. ADR-022 |
| Frontend | `pages/farmer/GovtUpdatesPage`, `GrievancePage`; `pages/officer/BulletinsPage`, `PublishAdvisoryPage`, `ConnectAnalyticsPage`, `GrievanceQueuePage`; `features/govconnect/*` | Official content visually distinct; translated label plus the official original; listen / ask / acknowledge / flag; dashboard warnings card; officer editor with provenance highlights, side-by-side translations with back-translation, readiness gating, schedule, withdraw, supersede and audit. en/hi/te |

## 2. Fixes made along the way

- **Media ranking ties:** equal-score media were ordered arbitrarily, so the Phase 3 integration test became flaky as verified assets built up in the test DB. Ties are now broken by most recent verification.
- **API errors:** structured API errors (`{message, reasons}`) are flattened by the frontend client, so officers see why a bulletin is not publishable.

## 3. Tests

- **Backend:** 264 passed, 6 skipped. New unit tests cover:
  - extraction: en/te/hi, provenance offsets, issuer exclusion, collision guard, IST;
  - targeting: block / district / crop / segment / language;
  - alert category and priority, readiness;
  - eligibility rules, and the grievance lifecycle and SLA.
- **Postgres integration:** 6 of 6 pass (3 new). New flows:
  - compose → translate → refused bad edit → approve → publish → farmer inbox → ack / flag → ask-about-this → analytics → withdraw (index expired) → inbox shows "withdrawn";
  - supersede and schedule;
  - locations (block validation), grievance round-trip with internal notes hidden, scheme draft → verify → eligibility.
- **Frontend:** 30 files / 68 tests. New tests cover:
  - the inbox: official labelling, original toggle, ack, flag, ask navigation;
  - the editor: provenance marks, publish blocked until the translation is approved;
  - highlight segmentation, and scheme eligibility.
- Typecheck clean; lint 0 errors; build OK. Phase 4 Python files are ruff-clean.

## 4. Not done / pending

1. **Extraction accuracy benchmark (needs your OK).** The best labelled source is NDMA SACHET CAP alerts: their structured fields (LGD district codes, severity, effective/expires, event) are official labels, and the extractor would see only the free-text headline and description.
   - Fetching a one-time sample means polling the public RSS feed, which Phase 0 flagged for your confirmation.
   - State agriculture and KVK PDFs would need manual labelling.
2. **The LLM extractor** is not implemented (Gemini quota exhausted; ADR-021).
3. **Automated feeds** (SACHET, IMD, Agmarknet) and **block-level weather**: Phase 5.
4. **SMS / voice channels:** sandbox adapters in Phase 5; real providers need cost approval.
5. **te/hi district names** are missing from LGD, so Indic-script district mentions are not extracted.

## 5. Approvals requested

1. **SACHET sample:** may I fetch a one-time sample of the public SACHET CAP RSS feed to build the extraction benchmark?
2. **Commit:** Phase 4 is committed on `feat/sprint-11-phase4-govconnect`. Nothing is pushed.
3. **Native review:** of the new hi/te strings and of the PM-KISAN draft (officer verification).
