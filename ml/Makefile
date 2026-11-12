.PHONY: sync test lint lgd
sync:
	uv sync --extra eval
test:
	uv run pytest -q
lint:
	uv run ruff check src tests
# Rebuild LGD tables: make lgd DISTRICTS=... BLOCKS=... OBSERVED=YYYY-MM-DD
lgd:
	uv run python -m krishios_ml.reference.build_lgd_reference --districts $(DISTRICTS) --blocks $(BLOCKS) --observed-on $(OBSERVED)
