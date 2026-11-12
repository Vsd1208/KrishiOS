# Phase 2: Multilingual Core Report

- **Date:** 2026-11-12
- **Branch:** `feat/sprint-11-phase2-multilingual`
- **Scope:** translation service, NLU and NLU-based planner routing, real STT/TTS providers, and evaluation sets and reports.

**Integrity notes.**
- Every number below comes from code run in this session. Each is logged in `ml/experiments/*.jsonl` under the cited `run_id`, with JSON artifacts in `ml/reports/data/`.
- "Proxy" metrics are labelled as proxies.
- Nothing here has been reviewed by native speakers yet.

## 1. What was built

| Component | Where | Notes |
|---|---|---|
| Translation service | `backend/app/translation/` | Providers: mock, opus-mt (local, Apache-2.0), IndicTrans2 (local, MIT, **gated**), Gemini (off-device, opt-in). Agri glossary (protected active ingredients, formulations, schemes, agencies; en/hi/te unit spellings). Span protection with `<i>` placeholders. Independent number/unit/protected-term checker. Policy: provider chain, `blocked` on failed checks, `pending_review` for HIGH/CRITICAL. Cache keyed by content hash, provider and glossary version. `translation_record` audit table (migration 0010). Officer approve endpoint that re-checks edits. |
| NLU | `backend/app/nlu/` | Rule-based multilingual provider: script language ID, romanised hi/te markers, code-switch flag, intent lexicon with explicit priorities. Entities are resolved only via the crop catalog and LGD (with a guard for words that collide with district names, e.g. *Mandi*). Gemini structured-output provider (off-device; entities re-validated locally). `POST /api/v1/nlu/parse`. |
| Planner routing | `backend/app/agents/planner/planner.py` | Routes on NLU intents, not English keywords. Steps receive intent, language, crop and district parameters. |
| STT | `backend/app/voice/providers/whisper_stt.py`, `gemini_stt.py` | faster-whisper (local, MIT, CPU int8; LID restricted to en/hi/te). Gemini STT (off-device, opt-in). |
| TTS | `backend/app/voice/providers/mms_tts.py` | Meta MMS-TTS (local). **CC BY-NC 4.0, non-commercial**, disclosed in provider info; demo only. |
| Frontend | `frontend/src/services/api/translation.ts` | Typed clients for translation and NLU (UI in Phase 3/4). |
| Evaluation sets | `ml/evaluation_sets/` | MT: 160 English sentences from real advisories, with provenance, plus a reference template for native reviewers. NLU: 152 labelled utterances, labels **DRAFT**. |
| Harnesses | `ml/scripts/run_{stt,mt,nlu,tts}_eval.py`, `ml/src/krishios_ml/*/evaluation/` | They exercise the production backend code paths. |

## 2. Blockers found in this phase (affect every result below)

1. **AI4Bharat models: access granted, downloads too slow to finish today.**
   - The user added `HF_TOKEN` on 2026-11-12, and all 7 gated repos returned HTTP 200.
   - This connection measured about 0.2 MB/s from Hugging Face (about 0.04 MB/s from python.org). The required weights are about 4.9 GB: IndicTrans2 en→Indic 1.10 GB, Indic→en 0.91 GB, IndicConformer-600M 2.56 GB, MMS-TTS te/hi 0.30 GB. That is roughly 7 hours.
   - Downloads continue in priority order via `ml/scripts/download_models.sh`.
   - The IndicConformer provider is built (ONNX via its `trust_remote_code` loader, no NeMo). The IndicTrans2 provider is built. **Neither has been measured yet.**
   - `IndicTransToolkit` (the official pre/post-processor) did not install on Windows (it needs a native build). IndicTrans2 therefore uses the documented `<src_tag> <tgt_tag> text` input format.
2. **The Gemini key is free tier and its quota was exhausted** (HTTP 429 `generate_content_free_tier_requests`). Every Gemini comparison is **void**. The `gemini-nlu` entry in run `c3b467b50232` measured quota errors, not quality, and must not be cited. Free-tier prompts may be used by Google, so this key must never carry farmer data. `ALLOW_OFF_DEVICE_PROVIDERS` stays `false`.
3. **Native-speaker review is missing.** Without it there are no reference translations (so no reference chrF++), no review of the NLU labels, and no TTS naturalness ratings.

## 3. Results (all measured in this session)

### 3.1 NLU: rule-based provider (run `b74f7a0eb8c7`; 152 utterances; labels DRAFT)

| Metric | Value |
|---|---|
| Intent accuracy | **0.796** |
| Intent macro-F1 (10 intents) | 0.826 |
| Intent accuracy, English (n=47) | 0.702 |
| Intent accuracy, Hindi (n=34) | 0.853 |
| Intent accuracy, Hindi code-switched or romanised (n=19) | 0.737 |
| Intent accuracy, Telugu (n=34) | 0.853 |
| Intent accuracy, Telugu code-switched or romanised (n=18) | 0.889 |
| Language-ID accuracy | 0.934 |
| Code-switch flag accuracy | 0.934 |
| Crop slot P / R / F1 | 1.000 / 0.938 / 0.968 |
| District slot P / R / F1 (only 7 gold districts) | 1.000 / 0.857 / 0.923 |
| Median latency | 0.45 ms |

**Error analysis.** Top confusions: disease→advisory (11), market→advisory (4), govt_bulletin→out_of_scope (3), yield→advisory (3). These are lexical-coverage gaps. Symptom paraphrases ("white flies are sitting", "मुरझा रहे") fall back to `advisory` when a crop is present. Telugu-script కేవీకే (KVK) and the Hindi 'rate' are missing. Per ADR-013 these were **not** patched against the test set. A dev set is needed first.

**Caveats.**
- I authored both the lexicon and the test labels, so the labels need your review.
- English is the weakest segment because the English phrasings were written to avoid lexicon words.
- Precision is 1.0 on both slots because resolution is deliberately conservative: ambiguous names are never guessed.

**Gemini NLU:** run `c3b467b50232` is **void** (132/152 calls returned 429 free-tier quota errors).

### 3.2 STT: faster-whisper-small, CPU int8 (run `5c0b02cf7fef`; FLEURS test, 30 utterances per language, seed 13)

| Metric | Telugu | Hindi |
|---|---|---|
| WER | **1.119** | 0.575 |
| CER | **0.987** | 0.253 |
| LID accuracy (no hint) | 30/30 | 30/30 |
| Median latency per utterance | 47.6 s | 19.8 s |
| p90 latency | 105.1 s | 30.9 s |
| Median real-time factor | 4.95 | 1.60 |

**Conclusion:** Whisper-small is **not usable for Telugu**: WER above 1 means it inserts more words than the reference has, and nearly every character is wrong. It is too weak for Hindi and slower than real time on this CPU. Its only strong point is language ID (60/60), which the IndicConformer provider reuses.

An earlier attempt (no run_id) was aborted after 40 min. With Whisper's default temperature fallback, Telugu decoding looped. The fallback is now off by default (`STT_WHISPER_TEMPERATURE_FALLBACK`).

### 3.3 MT: opus-mt (run `955550580258`; 160 real advisory sentences; 158 contain numbers, 91 contain units)

| Metric | en→te | en→hi |
|---|---|---|
| **Passes all safety checks** | **0.325** | **0.331** |
| Number preservation, with span protection | 0.367 | 0.373 |
| Number preservation, without protection (ablation) | 0.380 | 0.310 |
| Unit preservation | 0.451 | 0.517 |
| Protected-term preservation | 0.956 | 0.994 |
| Placeholder survival | 0.614 | 0.747 |
| ms per sentence (CPU; model downloads running concurrently) | 2509 | 2160 |
| Round-trip chrF++ proxy | not available (reverse model not yet downloaded) | not available |

**Conclusions.**
1. **opus-mt is unusable for advisories:** about two-thirds of outputs change or drop numbers or units.
2. **The safety gate works:** every one of those outputs would be `blocked`, not delivered.
3. **Span protection does not help opus-mt on real sentences,** because the model mangles the placeholders themselves. On the short probe they survived 11/11 (hi) and 10/11 (te); on real sentences only 61–75% survive. The value of protection must be re-measured with IndicTrans2.

Top failure reasons: te missing numbers 100, missing units 50, unexpected numbers 48; hi missing numbers 84, unexpected numbers 74, missing units 44.
