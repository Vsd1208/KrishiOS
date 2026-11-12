# KrishiOS ML

Research, training and evaluation code for KrishiOS. This is a separate `uv` project, so heavy
training dependencies never enter the backend image. The backend only loads **exported
artifacts** from `ml/artifacts/` (mounted read-only) and the **reference tables** in
`ml/reference/`.

```bash
cd ml
uv sync                 # base deps
uv sync --extra eval    # + evaluation metrics (sacrebleu, jiwer)
uv run pytest
```

## Layout

| Path | Purpose |
|---|---|
| `reference/` | Committed, hand-reviewed tables: `crop_catalog.csv`, `lgd_districts.csv`, `lgd_blocks.csv` |
| `configs/` | YAML configs for data, crops and evaluations |
| `src/krishios_ml/common/` | Seeding, logging, JSONL experiment log, catalog loader |
| `src/krishios_ml/reference/` | Builders for the reference tables |
| `src/krishios_ml/*/evaluation/` | Evaluation harnesses (translation, NLU, voice, ...) |
| `data/`, `artifacts/` | Git-ignored. Raw data is downloaded by documented scripts |
| `experiments/` | JSONL experiment logs. Every reported number cites a `run_id` |
| `reports/` | Phase reports |

## Integrity rules

No metric, coverage count or latency appears in any report unless it was produced by code in
this folder and logged in `experiments/`. Raw datasets and large artifacts are never committed.
Licences are recorded in [DATA_SOURCES.md](DATA_SOURCES.md).
