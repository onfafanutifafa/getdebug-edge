#!/usr/bin/env bash
# Downloads the getdebug-edge model weights (GGUF) into model/. Idempotent:
# skips files that already exist. No credentials needed — Hugging Face model
# weights are publicly accessible.
#
# Usage:
#   bash download_model.sh          # primary model only (3B, ~2.1 GB)
#   bash download_model.sh 1.5b    # fallback model only (~1.0 GB)
#   bash download_model.sh all     # both, for bench.sh comparison runs
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODEL_DIR="$SCRIPT_DIR/model"
HF_BASE="https://huggingface.co"

MODEL_3B_FILE="qwen2.5-coder-3b-instruct-q4_k_m.gguf"
MODEL_3B_URL="$HF_BASE/Qwen/Qwen2.5-Coder-3B-Instruct-GGUF/resolve/main/$MODEL_3B_FILE"
MODEL_15B_FILE="qwen2.5-coder-1.5b-instruct-q4_k_m.gguf"
MODEL_15B_URL="$HF_BASE/Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF/resolve/main/$MODEL_15B_FILE"

mkdir -p "$MODEL_DIR"

fetch() {
  local file="$1" url="$2" label="$3"
  local dest="$MODEL_DIR/$file"
  if [ -f "$dest" ]; then
    echo "$label already present at $dest — skipping download."
    return 0
  fi
  echo "Downloading $label to $dest ..."
  curl -L --fail --progress-bar -o "$dest.tmp" "$url"
  mv "$dest.tmp" "$dest"
  echo "Done: $dest"
}

case "${1:-3b}" in
  3b)   fetch "$MODEL_3B_FILE" "$MODEL_3B_URL" "Qwen2.5-Coder-3B-Instruct (Q4_K_M, ~2.1 GB)" ;;
  1.5b) fetch "$MODEL_15B_FILE" "$MODEL_15B_URL" "Qwen2.5-Coder-1.5B-Instruct (Q4_K_M, ~1.0 GB)" ;;
  all)
    fetch "$MODEL_3B_FILE" "$MODEL_3B_URL" "Qwen2.5-Coder-3B-Instruct (Q4_K_M, ~2.1 GB)"
    fetch "$MODEL_15B_FILE" "$MODEL_15B_URL" "Qwen2.5-Coder-1.5B-Instruct (Q4_K_M, ~1.0 GB)"
    ;;
  *) echo "Usage: bash download_model.sh [3b|1.5b|all]" >&2; exit 1 ;;
esac
