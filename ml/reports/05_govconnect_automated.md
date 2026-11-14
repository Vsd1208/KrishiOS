# Phase 5: Govt–Farmer Connect, Automated Side (+F1, F3, F5)

- **Date:** 2026-11-14
- **Branch:** `feat/sprint-11-phase4-govconnect` (Phase 5 commits on top of Phase 4)
- **Scope:**
  - **Feeds:** automated official feeds, the district weather feed cross-checked against a second source, and the market and MSP data path.
  - **Delivery:** push notifications.
  - **Channels and DPI:** feature-phone channels (F5) and DPI adapters (F1).
  - **Offline:** the offline PWA (F3).
  - **Monitoring:** feed health.

**Integrity notes.**
- The live-run numbers below come from runs in this session against the real services, written to the test database.
- No farmer-facing delivery or acknowledgement rates are reported, because no real farmers exist yet.
- All hi/te strings are drafts pending native review.

## 1. Public sources reviewed (user request: more government sources for reliability)

| Source | Access checked 2026-11-14 | Terms | Decision |
|---|---|---|---|
| NDMA SACHET CAP, national feed | 200, RSS + CAP 1.2 | Feed declares "public domain" | **In use**, primary warnings source |
| NDMA SACHET CAP, Telangana feed (`rss_telangana.xml`) | 200 | Same | **In use**. Other state names vary (e.g. `rss_andhra_pradesh.xml` returns 404), so states are added one by one after a check |
| Open-Meteo forecast | 200, no key | CC BY 4.0 | **In use**, primary forecast |
| NASA POWER daily point API | 200, no key; about 2-day lag; `-999` fill value | NASA open data | **In use**, independent cross-check |
| PIB MSP release, Kharif 2026-27 | 200 | Government press release | **In use**: 17 MSP rows transcribed with URL |
| data.gov.in AGMARKNET | 400 without a key | GODL-India | **Adapter ready; needs your API key** |
| IMD API (`api.imd.gov.in`) | 401 | Key / IP whitelist | Not used: request access from IMD |
| IMD agromet district bulletins | Interactive form, no stable links | MoES copyright, reuse not stated | Not automated; officer upload |
| CWC flood forecasts (`ffs.india-water.gov.in`) | No public API documented (partner API via nodal officer) | — | Not used |
| UPAg portal | No public API found | — | Not used |
| myScheme | — | Terms forbid bots | Not used |

## 2. What was built

| Component | Where | Notes |
|---|---|---|
| SACHET adapter + job | `govconnect/feeds/sachet.py`, `worker/jobs/feeds.py::sachet_poll` | Uses official CAP fields; skips exercises, expired alerts, unsupported languages and out-of-area alerts. Rejected URLs are cached in Redis (1–3 days). Idempotent by CAP URL. Requests 1/s, at most 50 new per run. Officer review by default; opt-in auto-publish for LOW/MEDIUM |
| Weather feed + job | `govconnect/weather_feed.py`, `live_data/providers/nasa_power.py`, `live_data/services/crosscheck.py` | Hourly per farmer district: forecast, then cross-check (agree / disagree / unverified), then a `district_weather_snapshot` (migration 0013). Heavy-rain (≥ 40 mm) and extreme-heat (≥ 39 °C) events go to the proactive engine with the verdict |
| Reliability fixes | `live_data/providers/weather_provider.py`, `market_provider.py` | Missing values are no longer invented; spray window computed from the forecast; mock prices no longer labelled "Agmarknet"; MSP only from the PIB-sourced file (old code had paddy ₹2,300; official KMS 2026-27 is ₹2,441); real data.gov.in adapter |
| Farmer weather feed | `GET /govconnect/weather-feed`, `WeatherFeedCard` | Official warnings first, then the 5-day forecast, cross-check badge, spray window, data age and attribution |
| Feed health | `GET /govconnect/feeds/status`, Connect analytics panel | Weather success rate, cross-check verdicts, latest run, and feed bulletins by status (real runs only) |
| Channels (F5) | `app/channels/` | SMS segmenting (GSM-7 160/153, UCS-2 70/67, at most 3 parts) with reply-keyword footer. Inbound HELP / WEATHER / ALERTS / STOP, with free text going to the bot. IVR call scripts and menu. WhatsApp. Sandbox adapters with pseudonymised outbox. ADR-024 |
| Web push | `notifications/webpush.py`, `notifications/api.py`, `PushOptIn` | VAPID Web Push (sandbox until keys are set); subscriptions (migration 0014); gone subscriptions removed |
| DPI (F1) | `app/dpi/providers.py` | AgriStack (consent-gated), Bharat-VISTAAR, Bhashini: sandbox adapters return no data with a reason; listed under `/providers` |
| Offline PWA (F3) | `public/sw.js`, `manifest.webmanifest` | App shell cached; weather feed, inbox and crop list readable offline; questions queued on the device and sent on reconnect |

Already delivered in Phase 4 and reused here: deduplication, expiry, quiet hours with the critical override, and the Connect analytics page.

## 3. Live runs (job reliability)

| Run | Result |
|---|---|
| SACHET poll, national + Telangana, all districts, at most 5 new | Both feeds OK; 108 alerts seen; 4 bulletins created; 72 expired and 31 without LGD code skipped; 1 CAP file timed out (recorded, retried next run). Took 285 s because every rejected alert had to be fetched once. The skip-cache added afterwards means later runs fetch each alert at most once |
| Weather feed, test DB districts Khammam (509) and Warangal (522) | 2 of 2 OK; cross-check **agree** for both. Tmax MAE 1.42 / 0.61 °C over 5 overlapping days; 5-day rain 1.0 vs 3.3 mm and 1.0 vs 4.3 mm (Open-Meteo vs NASA POWER). No events (no heavy rain or heat forecast) |

These are single runs. A job-reliability rate over time (success rate, freshness lag) is collected by `/govconnect/feeds/status` once the worker runs on a schedule.

## 4. Extraction accuracy

See the Phase 4 report §4 (SACHET benchmark, test district F1 0.836, run `bcf032c40563`). In the live adapter, severity, districts and validity come from structured CAP fields, so the text-extraction errors measured there apply only to advice and crops.

## 5. Tests

- **Backend:** 279 passed, 8 skipped. New tests cover:
  - CAP parsing and skip rules, and the skip-cache;
  - cross-check verdicts, event thresholds and the spray rule;
  - SMS segmenting and keywords, IVR scripts, sandbox outbox pseudonyms;
  - push sandbox and DPI sandboxes;
  - the Agmarknet parser and its keyless failure;
  - MSP only from the reference.
- **Postgres integration:** 8 of 8 pass. New flows: SACHET poll idempotency with one feed down; inbound SMS WEATHER / ALERTS / STOP / unknown number, and the IVR menu.
- **Frontend:** 31 files / 70 tests pass. New tests cover the weather card (official first, "sources disagree" shown, spray, data age) and the offline question queue. Typecheck and lint clean; build OK; `sw.js` and the manifest ship in `dist`.
- **Migrations** 0013 and 0014: up/down/up verified on Postgres 16.

## 6. Needs from you

1. **data.gov.in API key** (free) for official mandi prices: register on data.gov.in and put the key in `backend/.env` as `DATA_GOV_IN_API_KEY`.
2. **VAPID keys** for real push: generate with `uv run vapid --gen` and set `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY` and `VAPID_SUBJECT` (a contact URI).
3. **SMS / IVR / WhatsApp provider:** choice and cost approval. Sandboxes stand in until then.
4. **More SACHET state feeds:** which states to add after Telangana (each URL is checked first).
5. **Rabi MSP:** should I add the Rabi MSP release (wheat etc.) the same way?
6. **Native review:** of the new hi/te strings.
