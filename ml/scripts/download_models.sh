#!/usr/bin/env bash
# Pre-download evaluation/runtime models with long timeouts and retries (slow networks).
# Usage (from backend/): bash ../ml/scripts/download_models.sh <repo_id>...
# Reads HF_TOKEN from backend/.env (never printed).
set -u
T=$(grep "^HF_TOKEN=" .env 2>/dev/null | head -1 | cut -d= -f2- | tr -d '\r" ')
export HF_TOKEN="$T" HF_HUB_DOWNLOAD_TIMEOUT=600 HF_HUB_ETAG_TIMEOUT=120
for m in "$@"; do
  for attempt in 1 2 3 4 5 6 7 8; do
    if uv run python - "$m" <<'PY'
import sys
from huggingface_hub import snapshot_download
repo = sys.argv[1]
allow = None if repo.startswith("Helsinki-NLP/") else [
    "*.json", "*.py", "*.txt", "*.model", "*.spm", "*.SRC", "*.TGT", "*.safetensors",
    "assets/*",
]
snapshot_download(repo, allow_patterns=allow, max_workers=4,
                  ignore_patterns=["*.h5", "*.msgpack", "tf_model*", "rust_model*", "*.ot"])
print("OK", repo, flush=True)
PY
    then break; else echo "retry $attempt $m" ; fi
  done
done
echo "DONE"
