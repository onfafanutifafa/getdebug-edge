#!/usr/bin/env bash
# Benchmarks every .gguf in model/ with llama-bench, using settings that
# mirror the agent's runtime (CPU-only, cores-1 threads).
#
# Purpose: decide the 3B-vs-1.5B (and quant-level) tradeoff with real numbers.
# The contest normalizes S_perf against the FASTEST submission's TPS and
# scores S_eff as (7GB - peak RAM)/7GB, so smaller/faster models win those
# two terms by construction — the only question is how much accuracy (50% of
# the score) is given up. Run this, then compare answer quality on the
# metadata.json test_prompts via:
#   python3 agent/agent.py --model model/<file>.gguf --prompt "<test prompt>"
#
# Also run the official profiler before every submission:
#   adtc-profiler run --submission . --mode participant --output submission.json --skip-accuracy
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODEL_DIR="$SCRIPT_DIR/model"

if ! command -v llama-bench >/dev/null 2>&1; then
  echo "llama-bench not found on PATH — install llama.cpp first (see README.md)." >&2
  exit 1
fi

# Physical cores, not logical: measured 18.2 TPS @ 68.8°C (8 threads) vs
# 14.7 TPS @ 98.7°C + throttling (15 threads) on an 8c/16t i9. Generation is
# memory-bandwidth-bound; SMT siblings add heat, not speed.
if [ "$(uname)" = "Darwin" ]; then
  THREADS="$(sysctl -n hw.physicalcpu)"
else
  THREADS="$(lscpu -p=CORE,SOCKET 2>/dev/null | grep -v '^#' | sort -u | wc -l | tr -d ' ')"
  [ "${THREADS:-0}" -ge 1 ] || THREADS=$(( $(nproc) / 2 > 0 ? $(nproc) / 2 : 1 ))
fi

shopt -s nullglob
GGUFS=("$MODEL_DIR"/*.gguf)
if [ ${#GGUFS[@]} -eq 0 ]; then
  echo "No .gguf files in $MODEL_DIR — run: bash download_model.sh all" >&2
  exit 1
fi

for gguf in "${GGUFS[@]}"; do
  echo "=== $(basename "$gguf") ==="
  # -p 512: prompt-processing speed (matters for time-to-first-token on chunks)
  # -n 128: generation speed (the TPS number the contest scores)
  llama-bench -m "$gguf" -t "$THREADS" -p 512 -n 128 -ngl 0
  echo
done

echo "Note: on Linux, watch thermals during the run with: watch -n2 sensors"
