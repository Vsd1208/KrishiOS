# Data sources and licences

Every dataset or reference table used by KrishiOS ML is listed here **before** it is used.
Raw data is never committed.

| Dataset | Used for | Licence / terms | Access | Committed? | Status |
|---|---|---|---|---|---|
| Local Government Directory (LGD): districts, blocks | `reference/lgd_districts.csv`, `reference/lgd_blocks.csv` | GODL-India (Ministry of Panchayati Raj); attribution required | Daily Parquet mirror https://ramseraph.github.io/opendata/lgd/ (source date recorded per row in `source_observed_on`) | Yes (derived, small) | In use (snapshot 2026-11-12) |
| Crop catalog | `reference/crop_catalog.csv` | Authored for KrishiOS; names drafted, **native-speaker review pending** (`review_status=draft`) | — | Yes | Draft |
| DES APY district statistics | Yield labels (Phase 6) | Government data; portal may need login | data.desagri.gov.in | No | Not downloaded |
| ICRISAT–TCI DLD | Secondary yield labels (Phase 6) | **Conflict**: CC BY 4.0 (CY-Bench README) vs CC BY-NC 3.0 (ICAR KRISHI record). Treated as **non-commercial** until resolved | ICRISAT Dataverse | No | Not downloaded |
| CY-Bench (India = ICRISAT DLD) | Baseline sanity check only | CC BY 4.0 | Zenodo | No | Not downloaded |
| NDMA SACHET CAP alerts (snapshot 2026-11-13, 98 items, 68 with LGD codes) | Bulletin-extraction benchmark (`evaluation_sets/govconnect/sachet_20261113.jsonl`, dev 27 / test 41) | Feed declares `<copyright>public domain</copyright>`; C-DOT CAP document says subscribers may disseminate the warnings | `https://sachet.ndma.gov.in/cap_public_website/rss/rss_india.xml`, one CAP XML per item, fetched sequentially at 1 request/s by `scripts/fetch_sachet_sample.py` (user approved 2026-11-13) | Derived JSONL yes; raw XML no (`data/raw/sachet/`) | In use |
| District alias list | `reference/district_aliases.csv` (English exonyms / spellings → LGD code) | Authored for KrishiOS; each row names its LGD target and where the spelling was seen | — | Yes | 6 rows (from the SACHET dev split) |
| FLEURS (te_in, hi_in) | STT evaluation (Phase 2) | CC BY 4.0 | Hugging Face `google/fleurs` | No | See Phase 2 report |
