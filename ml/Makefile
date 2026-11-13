.PHONY: sync test lint lgd gpu
sync:
	uv sync --extra eval
test:
	uv run pytest -q
lint:
	uv run ruff check src tests
# Rebuild LGD tables: make lgd DISTRICTS=... BLOCKS=... OBSERVED=YYYY-MM-DD
lgd:
	uv run python -m krishios_ml.reference.build_lgd_reference --districts $(DISTRICTS) --blocks $(BLOCKS) --observed-on $(OBSERVED)
# Local GPU (CUDA 13.0 PyTorch, ~3 GB download) for training phases; then verify the GPU.
gpu:
	uv sync --extra gpu --extra eval
	uv run --extra gpu python scripts/check_gpu.py
