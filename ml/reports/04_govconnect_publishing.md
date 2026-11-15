# Phase 4: Govt–Farmer Connect, Publishing Side (+F2, F4)

- **Date:** 2026-11-14
- **Branch:** `feat/sprint-11-phase4-govconnect`
- **Scope:**
  - **Officer side:** bulletin ingestion with provenance, the publishing console (target, translate, approve, schedule, withdraw, supersede, audit), and delivery through `NotificationService`.
  - **Farmer side:** the Govt Updates inbox, and RAG indexing with validity.
  - **F2:** saved locations and block-level targeting.
  - **F4:** grievance tickets with SLA, and scheme eligibility Q&A.

**Integrity notes.**
- Extraction accuracy (§4) comes from logged runs on real SACHET alerts. Delivery and acknowledgement rates must come from real runs; there have been none, so none are reported.
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

## 4. Extraction accuracy on real government alerts

**Benchmark** (approved 2026-11-13):
- **Source:** 98 NDMA SACHET CAP alerts (feed marked public domain), fetched once at 1 request/s. 68 carry LGD district codes; split dev 27 / test 41 (seed 13).
- **Labels:** the official structured CAP fields (LGD codes, severity, expiry, event).
- **Input:** the extractor sees only the free text (headline, description, instruction).
- **Discipline:** tuned on dev only; test scored once (ADR-013).

**Dev-only changes** (dev F1 0.765 → 0.821, runs `7246691b38ff` → `d5e0ce889360`):
- **Directional names:** pure compass-direction names (Delhi's "East") match only when directly followed by "district".
- **State names:** district names inside a mentioned state name ("Jammu and Kashmir") are skipped.
- **Issuer location:** "Disaster Management Department" added as an authority, so the issuing office's place is excluded.
- **Spellings:** district names also match with spaces removed ("Coochbehar"), plus a 6-row sourced alias file (`reference/district_aliases.csv`: East Midnapore, East Burdwan, ...).
- **Dates:** time-before-date ("22:45, 10-11-2026") and hour ranges ("next 2-3 hours").

**Test result of record** (run `bcf032c40563`, n = 41):

| Metric | Value |
|---|---|
| District precision / recall / F1 | 0.868 / 0.807 / **0.836** |
| District exact-set match | 0.659 |
| District precision / recall vs headline-level gold* | **1.000** / 0.828 |
| Severity accuracy | 0.659 |
| Hazard accuracy (alerts with a mappable event, n = 25) | 0.800 |
| valid_to found and within 60 min of CAP `expires` | 0.244 |

\* IMD issues one multi-state headline as separate per-state alerts (e.g. Karaikal, Puducherry vs Tamil Nadu districts), so the strict score counts correctly named districts of the sibling alert as errors. The headline-level score uses the union of gold districts over alerts with identical text. This was defined on dev before test scoring.

**Remaining errors:**
- **Bengali alerts:** not supported; the extractor reads en/hi/te only.
- **Region-level names:** alerts naming "Andaman and Nicobar Islands" or "N districts of Assam" instead of districts.
- **Severity:** nowcast text rarely states the colour code; the CAP field carries it.
- **Expiry:** usually "next 3 hours" with no base time in the text.

**Feed adapter:** a SACHET adapter should read severity, LGD codes and expiry from the structured CAP fields and use text extraction only for advice sentences and crops.

## 5. Not done / pending

1. **LLM extractor:** not implemented (Gemini quota exhausted; ADR-021).
2. **Automated feeds** (SACHET adapter, IMD, Agmarknet) and **block-level weather:** Phase 5.
3. **SMS / voice channels:** sandbox adapters in Phase 5; real providers need cost approval.
4. **Indic-script names:** te/hi district names are missing from LGD; Bengali is not supported.

## 6. Approvals requested

1. **Commit:** Phase 4 is committed on `feat/sprint-11-phase4-govconnect`. Nothing is pushed.
2. **Native review:** of the new hi/te strings, and officer verification of the PM-KISAN draft.
