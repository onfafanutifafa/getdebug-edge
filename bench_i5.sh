#!/usr/bin/env bash
# Reference-hardware benchmark for getdebug-edge — RUN THIS ON THE i5 UBUNTU BOX.
#
# This is the one measurement that must happen on real target hardware: true
# generation TPS (S_perf) and true CPU temperature + throttling (P_thermal).
# Accuracy (0.80 arc_easy) and RAM/S_eff (1.84 GB → 74) are hardware-INDEPENDENT
# and already locked by the Docker profiler run; this fills in the last two.
#
# It captures, automatically (no manual `watch sensors`):
#   1. llama-bench pp512 / tg128 on PHYSICAL cores  → generation TPS
#   2. peak CPU package/core temperature during the run
#   3. Intel per-core throttle counters before/after → hard throttle signal
#   4. (optional) the official adtc-profiler → the authoritative submission.json
#         with real throughput + thermal + memory on this machine
#
# Results are written to bench_i5_results/ as both human-readable text and JSON.
#
# Usage (on the i5, from the repo root):
#   sudo apt install -y lm-sensors && sudo sensors-detect --auto   # once
#   bash download_model.sh 3b                                      # if not present
#   bash bench_i5.sh                       # native llama-bench + thermal
#   RUN_PROFILER=1 bash bench_i5.sh        # also run the official profiler
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODEL_DIR="$SCRIPT_DIR/model"
OUT_DIR="$SCRIPT_DIR/bench_i5_results"
mkdir -p "$OUT_DIR"
RESULT_TXT="$OUT_DIR/results.txt"
RESULT_JSON="$OUT_DIR/results.json"
THERMAL_LOG="$OUT_DIR/thermal_timeline.csv"
: > "$RESULT_TXT"

log() { echo "$@" | tee -a "$RESULT_TXT"; }

if [ "$(uname)" != "Linux" ]; then
  echo "This script is for the Linux (Ubuntu) reference machine, not $(uname)." >&2
  echo "On the dev Mac use bench.sh instead — its TPS is an upper bound only." >&2
  exit 1
fi

# --- Shipping model: prefer the baked Q3, else any Q3, else first gguf. ---
shopt -s nullglob
MODEL="$MODEL_DIR/getdebug-edge-3b-q3_k_m.gguf"
if [ ! -f "$MODEL" ]; then
  cands=("$MODEL_DIR"/*q3_k_m*.gguf "$MODEL_DIR"/*.gguf)
  [ ${#cands[@]} -gt 0 ] || { echo "No .gguf in $MODEL_DIR — run: bash download_model.sh 3b" >&2; exit 1; }
  MODEL="${cands[0]}"
fi

command -v llama-bench >/dev/null 2>&1 || {
  echo "llama-bench not on PATH — build llama.cpp with -DGGML_NATIVE=ON (see README)." >&2; exit 1; }

# --- Physical cores (not SMT siblings): the measured sweet spot. ---
THREADS="$(lscpu -p=CORE,SOCKET 2>/dev/null | grep -v '^#' | sort -u | wc -l | tr -d ' ')"
[ "${THREADS:-0}" -ge 1 ] || THREADS=$(( $(nproc)/2 > 0 ? $(nproc)/2 : 1 ))

CPU_MODEL="$(sed -n 's/^model name[[:space:]]*: //p' /proc/cpuinfo | head -1)"
log "=== getdebug-edge reference-hardware benchmark ==="
log "date         : $(date -u +%Y-%m-%dT%H:%M:%SZ)"
log "cpu          : ${CPU_MODEL:-unknown}"
log "physical thr : $THREADS   (of $(nproc) logical)"
log "model        : $(basename "$MODEL")"
log ""

# --- Thermal helpers -------------------------------------------------------
# Read the hottest current temperature (°C) from lm-sensors, or fall back to
# the kernel thermal zones. Prints a bare number or empty if unavailable.
read_temp_c() {
  local m=""
  if command -v sensors >/dev/null 2>&1; then
    m=$(sensors -u 2>/dev/null | awk -F': ' '/_input/ && $2+0>x {x=$2+0} END{if(x>0)printf "%.1f", x}')
  fi
  if [ -z "$m" ]; then                       # fall back to kernel thermal zones
    local mm=0 t
    for z in /sys/class/thermal/thermal_zone*/temp; do
      [ -r "$z" ] || continue; t=$(cat "$z" 2>/dev/null || echo 0); t=$(( t/1000 ))
      [ "$t" -gt "$mm" ] && mm=$t
    done
    [ "$mm" -gt 0 ] && m="$mm"
  fi
  printf "%s" "$m"
}

# Sum of Intel per-core throttle counters (increments when a core throttles
# for thermal reasons). Best hard signal that P_thermal should apply.
throttle_count() {
  local s=0 c
  for f in /sys/devices/system/cpu/cpu*/thermal_throttle/core_throttle_count; do
    [ -r "$f" ] || continue; c=$(cat "$f" 2>/dev/null || echo 0); s=$(( s + c ))
  done
  echo "$s"
}

HAVE_SENSORS=0
if [ -n "$(read_temp_c)" ]; then           # sensors OR kernel thermal zones
  HAVE_SENSORS=1
else
  log "WARNING: no readable temperature source (install lm-sensors + run"
  log "         'sudo sensors-detect --auto'). TPS will still be measured;"
  log "         thermal peak will be reported as unavailable."
fi

# --- Background thermal sampler --------------------------------------------
echo "t_iso,temp_c" > "$THERMAL_LOG"
SAMPLER_PID=""
if [ "$HAVE_SENSORS" = 1 ]; then
  ( while :; do echo "$(date -u +%H:%M:%S),$(read_temp_c)" >> "$THERMAL_LOG"; sleep 1; done ) &
  SAMPLER_PID=$!
  trap '[ -n "$SAMPLER_PID" ] && kill "$SAMPLER_PID" 2>/dev/null || true' EXIT
fi

THR_BEFORE="$(throttle_count)"
TEMP_IDLE="$([ "$HAVE_SENSORS" = 1 ] && read_temp_c || echo "")"
log "idle temp    : ${TEMP_IDLE:-n/a} °C"
log "throttle cnt : $THR_BEFORE (before)"
log ""
log "--- llama-bench (pp512 prompt, tg128 generation, ngl 0, $THREADS threads) ---"

# Run llama-bench; keep its native table in the results, and pull TPS out.
BENCH_OUT="$(llama-bench -m "$MODEL" -t "$THREADS" -p 512 -n 128 -ngl 0 2>&1)"
echo "$BENCH_OUT" | tee -a "$RESULT_TXT"

# Give the sampler a moment to capture the post-run peak, then stop it.
sleep 2
[ -n "$SAMPLER_PID" ] && kill "$SAMPLER_PID" 2>/dev/null || true
SAMPLER_PID=""

THR_AFTER="$(throttle_count)"
TEMP_PEAK=""
if [ "$HAVE_SENSORS" = 1 ]; then
  TEMP_PEAK="$(awk -F',' 'NR>1 && $2+0>m{m=$2+0} END{if(m>0)printf "%.1f", m}' "$THERMAL_LOG")"
fi

# Parse tg128 (generation) and pp512 (prompt) t/s from llama-bench's table.
# Rows look like: | ... | pp512 | 123.45 ± 0.67 |  and  | ... | tg128 | 12.34 ± 0.05 |
parse_tps() { echo "$BENCH_OUT" | awk -F'|' -v k="$1" '$0 ~ k {gsub(/ /,"",$(NF-1)); split($(NF-1),a,"±"); print a[1]; exit}'; }
TG_TPS="$(parse_tps 'tg128')"
PP_TPS="$(parse_tps 'pp512')"

THROTTLED="false"
THR_DELTA=$(( THR_AFTER - THR_BEFORE ))
if [ "$THR_DELTA" -gt 0 ]; then THROTTLED="true"; fi
# Also flag if we crossed the contest's 85°C line even without a counter tick.
OVER_85="false"
if [ -n "$TEMP_PEAK" ] && awk "BEGIN{exit !($TEMP_PEAK>85)}"; then OVER_85="true"; THROTTLED="true"; fi

log ""
log "=== SUMMARY (reference hardware) ==="
log "generation TPS (tg128) : ${TG_TPS:-parse-failed} t/s   <- this is S_perf's raw input"
log "prompt    TPS (pp512)  : ${PP_TPS:-parse-failed} t/s"
log "peak CPU temp          : ${TEMP_PEAK:-unavailable} °C"
log "throttle counter delta : $THR_DELTA   (>0 means a core throttled)"
log "crossed 85 °C          : $OVER_85"
log "THROTTLED (P_thermal)  : $THROTTLED   -> P_thermal = $([ "$THROTTLED" = true ] && echo -10 || echo 0)"
log ""
log "Full thermal timeline: $THERMAL_LOG"

# --- Machine-readable result ----------------------------------------------
cat > "$RESULT_JSON" <<JSON
{
  "measured_on": "reference_i5",
  "date_utc": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "cpu_model": "${CPU_MODEL:-unknown}",
  "physical_threads": $THREADS,
  "logical_threads": $(nproc),
  "model": "$(basename "$MODEL")",
  "generation_tps": ${TG_TPS:-null},
  "prompt_tps": ${PP_TPS:-null},
  "idle_temp_c": ${TEMP_IDLE:-null},
  "peak_temp_c": ${TEMP_PEAK:-null},
  "throttle_count_before": $THR_BEFORE,
  "throttle_count_after": $THR_AFTER,
  "throttled": $THROTTLED,
  "crossed_85c": $OVER_85,
  "p_thermal": $([ "$THROTTLED" = true ] && echo -10 || echo 0)
}
JSON
log "Machine-readable result: $RESULT_JSON"

# --- Optional: the authoritative profiler run on this hardware -------------
if [ "${RUN_PROFILER:-0}" = "1" ]; then
  log ""
  log "--- official adtc-profiler (authoritative submission.json on this box) ---"
  if command -v adtc-profiler >/dev/null 2>&1; then
    # Full run: accuracy is hardware-independent but harmless to re-measure, and
    # this yields ONE submission.json with real TPS + thermal + RAM + accuracy.
    ARGS=(run --submission "$SCRIPT_DIR" --mode participant --output "$OUT_DIR/submission_i5.json")
    [ "${SKIP_ACCURACY:-0}" = "1" ] && ARGS+=(--skip-accuracy)
    adtc-profiler "${ARGS[@]}" 2>&1 | tee -a "$RESULT_TXT"
    log "Wrote $OUT_DIR/submission_i5.json — use this as the final submission JSON."
  else
    log "adtc-profiler not installed. Install with:"
    log "  pip install \"git+https://github.com/Africa-Deep-Tech-Foundation/adtc-profiler.git\""
    log "then re-run: RUN_PROFILER=1 bash bench_i5.sh"
  fi
fi

log ""
log "Done. Paste results.txt (or results.json) back to finalize S_perf + P_thermal."
