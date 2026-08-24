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

# Q4_K_M is the shipping quant — chosen over Q3_K_M because the contest scores
# the BARE MODEL (S_acc = 50%), where Q4 leads (arc_easy 0.82 vs 0.80; code-review
# model-only recall 68% vs 59%). Q3 stays available via `--model` as the lighter
# efficiency alternative. See REPORT.md.
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

bake() {
  # Bake the getdebug-edge reviewer persona into the chat template so the
  # model behaves as a code reviewer even when run bare (Ollama/llama-cli
  # with no system prompt). Reproducible from public weights — see
  # tools/bake_persona.py. Skipped gracefully if the gguf package is absent.
  local src="$MODEL_DIR/$MODEL_3B_FILE" dst="$MODEL_DIR/getdebug-edge-3b-q4_k_m.gguf"
  [ -f "$dst" ] && { echo "Baked model already present at $dst — skipping."; return 0; }
  if python3 -c "import gguf" 2>/dev/null; then
    python3 "$SCRIPT_DIR/tools/bake_persona.py" "$src" "$dst"
  else
    echo "NOTE: 'pip install gguf' then run: python3 tools/bake_persona.py $src $dst"
  fi
}

case "${1:-3b}" in
  3b)   fetch "$MODEL_3B_FILE" "$MODEL_3B_URL" "Qwen2.5-Coder-3B-Instruct (Q4_K_M, ~2.1 GB)" && bake ;;
  1.5b) fetch "$MODEL_15B_FILE" "$MODEL_15B_URL" "Qwen2.5-Coder-1.5B-Instruct (Q4_K_M, ~1.0 GB)" ;;
  all)
    fetch "$MODEL_3B_FILE" "$MODEL_3B_URL" "Qwen2.5-Coder-3B-Instruct (Q4_K_M, ~2.1 GB)"
    fetch "$MODEL_15B_FILE" "$MODEL_15B_URL" "Qwen2.5-Coder-1.5B-Instruct (Q4_K_M, ~1.0 GB)"
    ;;
  *) echo "Usage: bash download_model.sh [3b|1.5b|all]" >&2; exit 1 ;;
esac
