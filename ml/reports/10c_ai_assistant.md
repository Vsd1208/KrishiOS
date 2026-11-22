# Phase 10c: KrishiOS AI Assistant (interim)

- **Status:** built on `feat/sprint-11-phase10c-ai-assistant`; not yet merged. Last updated 2026-11-22.
- **What it is:** an on-device assistant that answers farming questions **only from vetted guides**, citing the
  page, or says it has no verified source; and that turns an uploaded document into an officer brief or a
  plain-language farmer summary. English, Hindi and Telugu. Nothing is sent to an online AI service.
- **Not yet decided:** whether answers are good enough for farmers. That needs the human review of
  `reports/data/assistant_review_31f459a7e4b0.csv` and then one score on the held-back test questions.
- **Not done:** the Kisan Call Centre fine-tune planned in the roadmap. Retrieval, not the model's
  knowledge, turned out to be the main limit (section 4), so grounding came first.

## Runs of record

All runs are logged in `ml/experiments/`; full results are in `ml/reports/data/`.

| Experiment | Run id | Script | Notes |
|---|---|---|---|
| Retrieval baseline, all 20 topics (before the split) | `6fba3adba44f` | `scripts/eval_assistant_retrieval.py --split all` | MiniLM-era query path, e5 index v009 |
| Retrieval, dev, question as asked | `1dbcceed54a7` | `... --split dev` | index v009 |
| Retrieval, dev, Hindi/Telugu translated to English first | `894e4efc957b` | `... --split dev --translated` | index v009 |
| Retrieval, dev, cross-encoder rerank of 25 candidates (rejected) | `f7df6c181acc` | `... --split dev --translated` | code reverted |
| Retrieval, dev, passages with section headers | `30379be0fae7` | `... --split dev --translated` | index v010 (live) |
| Answers, dev, qwen2.5:3b | `08b03b0f1711` | `scripts/eval_assistant_answers.py --split dev` | index v009 |
| Answers, dev, qwen2.5:3b, stricter instruction (rejected) | `63073ee0d023` | same | instruction reverted |
| Answers, dev, qwen2.5:7b | `c6a701ba71eb` | `... --model qwen2.5:7b` | index v009 |
| Answers, dev, qwen2.5:7b, section headers | `31f459a7e4b0` | `... --model qwen2.5:7b` | index v010; review sheet |

Earlier evidence reused: cross-lingual retrieval benchmark `bf4365b06b28` (Phase 2/3), which chose the
embedding model.

## 1. Library and question set

- **Vetted library** (`scripts/fetch_knowledge_sources.py`, `scripts/upload_knowledge_sources.py`): TNAU Crop
  Production Guide (Agriculture) 2020 and PAU Packages of Practices for Kharif and Rabi crops; 852 pages,
  3,099 passages with title, publisher, URL and page. The five earlier knowledge-base files had no stated
  source. ICAR and `nic.in` sites did not resolve from this network, CICR failed the TLS handshake, and the
  CRRI bulletin and TNAU horticulture guide (chilli) did not download; chilli has no vetted source yet.
- **Question set** (`reference/assistant_qset_v1.json`, draft for review): 22 topics, each asked in English,
  Hindi and Telugu, with a reference answer, the key facts and the PDF page. Every key fact was checked
  against the text of its page. Four topics are not covered by the guides, to test declining.
  **Split:** q01-q10 and q21-q22 for development, q11-q20 held back for one final score.

## 2. Retrieval

- **Embedding model:** `intfloat/multilingual-e5-small` replaced `all-MiniLM-L6-v2`. On the earlier benchmark
  (`bf4365b06b28`) Hindi/Telugu questions against English text reached recall@5 1.00/1.00, against 0.03/0.21.
- **Translate the question first** (IndicTrans2, local): on dev, Telugu hit@5 0.3 -> 0.8 and MRR 0.15 -> 0.60;
  Hindi MRR 0.41 -> 0.48 (`1dbcceed54a7` vs `894e4efc957b`).
- **Cross-encoder rerank** of 25 candidates: pooled dev hit@5 22/30 both ways, hit@1 13 vs 14, four times
  slower. Not kept. (The reranker's score had been computed and then ignored by the ranking step.)
- **Section headers** ("guide title | chapter > section", read from heading font sizes): pooled dev hit@1
  14 -> 16, hit@5 22 -> 23, mean MRR 0.57 -> 0.63 (`30379be0fae7`). The direct-seeded-rice urea question
  went from ranks 2/none/5 to 1/2/2 (en/hi/te). Index v010 is live; v009 is kept for rollback.

Fixes found on the way: the index quality gate set precision/recall/MRR from vector counts (always 1.0) and
treated the whole build time as search latency, so every real index failed; words in the question (a crop,
a state) were hard filters, so any English question naming a crop returned nothing.

## 3. Answers

The assistant answers only from numbered passages and must cite them; an answer with no valid citation is
not shown, and the farmer gets "no verified source, ask your officer or KVK" in their language.

Dev, 30 answerable and 6 uncovered questions:

| | 3B, v009 | 7B, v009 | 7B, v010 |
|---|---|---|---|
| Answered | 23 | 27 | 25 |
| Cited the expected page | 11 | 15 | 14 |
| Cited another page | 12 | 12 | 11 |
| All key facts present | 5 | 7 | 10 |
| Uncovered questions declined | 6/6 | 6/6 | 6/6 |
| Hindi + Telugu answers blocked by translation checks | 15 | 6 | 6 |
| Median seconds per answer (en/hi/te) | 3/9/7 | 10/14/12 | 11/12/11 |

- **Model:** `qwen2.5:7b` (4-bit, Ollama, on this laptop's 4 GB GPU with CPU spill-over) is the default.
- **"Cited another page" overstates errors**: some facts appear in both guides. Only the human review can say
  how many answers are wrong. Until then the farmer chat stays on the agent runtime
  (`CONVERSATION_ANSWER_RUNNER=agents`); the assistant runner is ready behind that setting.
- **Translation checks** block a translated answer when numbers, units or protected terms do not survive
  (seen: "0.45" -> "45", "urea" mangled); the English answer is shown instead, flagged.

## 4. Document analysis

`POST /assistant/analyze-document` (background job; officer brief or farmer summary). The file is read in
memory and never stored; results expire after an hour and only the uploader can read them.

Trial on the NAAS agromet advisory of 20 July 2026 (14 pages), `qwen2.5:7b`:

- **Officer brief** (4.4 min): correct period, states and concrete actions; no line removed by the checks.
- **Farmer summary for paddy + cotton in Telangana** (5-7 min, 5 of 7 sections read): the English summary
  was correct and specific (transplant 20-25-day seedlings at 20 x 10 cm). The Telugu summary moved the
  cowpea anthracnose spray (Carbendazim 1 g/L) to rice. Every number was in the document, so a second
  check was added: a dose line naming a crop must have its product or disease name near that crop in the
  document. On this advisory it removes exactly that line.

## 5. Limits

- Answer accuracy is not yet established; review pending.
- Answers take about 11 s and document summaries several minutes on this laptop.
- Document jobs live in one backend process's memory; several workers would need a shared store.
- The checks catch invented numbers and advice moved between crops, not every misreading.
- Hindi/Telugu output quality has not been reviewed by a native-speaking agronomist.

## 6. Remaining work

1. Human review of `assistant_review_31f459a7e4b0.csv`, and of the Hindi/Telugu question wording.
2. One score on the test half (q11-q20) with the final configuration.
3. Decide whether the farmer chat uses the assistant.
4. Optional: the Kisan Call Centre fine-tune, measured against this baseline.
