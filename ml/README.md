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

### Local GPU (training phases)

The laptop has an NVIDIA RTX 2050 (4 GB). CUDA PyTorch is an opt-in extra, so the backend
image is unaffected:

```bash
cd ml
uv sync --extra gpu --extra eval                    # torch 2.14.1+cu130, torchvision, timm (~3 GB)
uv run --extra gpu python scripts/check_gpu.py      # prints the GPU, runs fp32/fp16 matmul and a timm step
```

Use `uv run --extra gpu ...` for GPU scripts: a plain `uv run` re-syncs the default
dependency set and may remove the extra. With 4 GB of VRAM, use AMP (fp16), small batches and
compact backbones (MobileNetV3, EfficientNet-B0, ConvNeXt-Atto).

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
