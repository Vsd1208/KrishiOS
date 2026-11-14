# Data sources and licences

Every dataset or reference table used by KrishiOS ML is listed here **before** it is used.
Raw data is never committed.

| Dataset | Used for | Licence / terms | Access | Committed? | Status |
|---|---|---|---|---|---|
| Local Government Directory (LGD): districts, blocks | `reference/lgd_districts.csv`, `reference/lgd_blocks.csv` | GODL-India (Ministry of Panchayati Raj); attribution required | Daily Parquet mirror https://ramseraph.github.io/opendata/lgd/ (source date recorded per row in `source_observed_on`) | Yes (derived, small) | In use (snapshot 2026-11-12) |
| Crop catalog | `reference/crop_catalog.csv` | Authored for KrishiOS; names drafted, **native-speaker review pending** (`review_status=draft`) | — | Yes | Draft |
| DES APY district statistics (India Data Portal mirror, retrieved 2026-02-26) | Yield labels (Phase 6), 1997-2022, 455,359 rows | Open Data Commons Attribution (ODC-By); source MoA&FW | `ckandev.indiadataportal.com` dataset `area-production-yield-apy`, resource `f980409d…` (56.2 MB; sha256 prefix `fe10fbf129b3501b`) | No (`data/raw/apy/20261114/`) | **In use** |
| UPAg crop-wise APY (India Data Portal mirror) | Label cross-check, 2013-2024, 156,189 rows | ODC-By; source MoA&FW | same dataset, resource `6f70d961…` (16.9 MB) | No | **In use** (cross-check) |
| ICRISAT–TCI DLD | Secondary yield labels (Phase 6) | **Conflict**: CC BY 4.0 (CY-Bench README) vs CC BY-NC 3.0 (ICAR KRISHI record). Treated as **non-commercial** until resolved | ICRISAT Dataverse (login); `data.icrisat.org` unreachable 2026-11-14 | No | Not ingested (scope-freeze decision) |
| CY-Bench (India = ICRISAT DLD) | Baseline sanity check only | CC BY 4.0 | Zenodo | No | Not downloaded |
| NDMA SACHET CAP alerts (snapshot 2026-11-13, 98 items, 68 with LGD codes) | Bulletin-extraction benchmark (`evaluation_sets/govconnect/sachet_20261113.jsonl`, dev 27 / test 41) | Feed declares `<copyright>public domain</copyright>`; C-DOT CAP document says subscribers may disseminate the warnings | `https://sachet.ndma.gov.in/cap_public_website/rss/rss_india.xml`, one CAP XML per item, fetched sequentially at 1 request/s by `scripts/fetch_sachet_sample.py` (user approved 2026-11-13) | Derived JSONL yes; raw XML no (`data/raw/sachet/`) | In use |
| NDMA SACHET CAP feeds, live (national + Telangana) | Govt Connect warnings (`sachet_poll` job) | Public domain (feed declaration) | `rss_india.xml`, `rss_telangana.xml`; 1 CAP request/s, rejected alerts cached 1–3 days | No (stored as bulletins with source URL) | In use (Phase 5) |
| Open-Meteo forecast API | District forecasts, spray window | CC BY 4.0, attribution shown in the UI; free non-commercial use | `api.open-meteo.com/v1/forecast` (district coordinates only) | No | In use |
| NASA POWER daily point API | Independent cross-check of recent rainfall / temperature | NASA open data, free use with attribution | `power.larc.nasa.gov/api/temporal/daily/point` | No | In use (Phase 5) |
| PIB: MSP for Kharif crops, marketing season 2026-27 | `reference/msp.csv` (17 rows) | Government press release | https://www.pib.gov.in/PressReleasePage.aspx?PRID=2260618 (retrieved 2026-11-14) | Yes (transcribed values with URL) | In use; Rabi MSP not yet added |
| AGMARKNET via data.gov.in | Official daily mandi prices (`agmarknet-v1`) | Government Open Data Licence – India | Resource `9ef84268-d588-465a-a308-a864a43d0070` (current daily, about 488 Telangana rows per day); history in `35985678-0d79-46b4-9ed6-6f13308a1d24`; key in `backend/.env`, 1,000 requests/day | No | **In use** since 2026-11-14 |
| District alias list | `reference/district_aliases.csv` (English exonyms / spellings → LGD code) | Authored for KrishiOS; each row names its LGD target and where the spelling was seen | — | Yes | 6 rows (from the SACHET dev split) |
| FLEURS (te_in, hi_in) | STT evaluation (Phase 2) | CC BY 4.0 | Hugging Face `google/fleurs` | No | See Phase 2 report |
