# Reference-hardware run — do this on the i5 Ubuntu laptop

This is the **last missing measurement** before submission. Everything else is
locked from the Docker profiler run: accuracy `acc_norm 0.82` (arc_easy), peak
RAM `2.21 GB → S_eff 68`, no OOM. Those are **hardware-independent**. What still
needs *real target hardware* is the two things a virtualized Mac container can't
measure honestly:

- **Generation TPS** → the raw input to **S_perf** (30% of the score)
- **CPU temperature + throttling** → **P_thermal** (−10 if it throttles or crosses 85 °C)

The i5 is the first time we read a real thermometer — our Docker-on-Mac profiler
run reported `core_temp_c_peak: null` because there were no host sensors.

## What "the i5" should be

The ADTC reference class: a budget/refurb laptop with an **Intel Core i5**,
**8 GB RAM**, integrated graphics, **Ubuntu 22.04 LTS**, CPU-only. A refurb
i5-8250U / i5-1035G1 / i5-8365U-class machine is representative. Run on battery
*and* on mains once if you can — thermal behavior differs.

## Steps (copy-paste, ~15 min)

```bash
# 0. Get the repo + model onto the i5 (git clone, or copy the folder over)
cd getdebug-edge

# 1. Build llama.cpp WITH native optimizations (prebuilt generic binaries
#    leave ~throughput on the table, and throughput is 30% of the score)
sudo apt update && sudo apt install -y build-essential cmake git lm-sensors
git clone https://github.com/ggml-org/llama.cpp
cmake -S llama.cpp -B llama.cpp/build -DGGML_NATIVE=ON -DCMAKE_BUILD_TYPE=Release
cmake --build llama.cpp/build --config Release -j
sudo cp llama.cpp/build/bin/llama-bench llama.cpp/build/bin/llama-server /usr/local/bin/

# 2. Enable temperature sensors (answer YES to the safe auto-detect)
sudo sensors-detect --auto
sensors            # sanity: you should see Core 0…N temperatures

# 3. Make sure the shipping model is present (~2.1 GB)
bash download_model.sh 3b        # skip if model/getdebug-edge-3b-q4_k_m.gguf exists

# 4a. Native benchmark — real TPS + auto thermal capture + throttle detection
bash bench_i5.sh

# 4b. (recommended) also produce the authoritative submission.json on THIS box
pip install "git+https://github.com/Africa-Deep-Tech-Foundation/adtc-profiler.git"
RUN_PROFILER=1 bash bench_i5.sh
```

## What you get

Written to `bench_i5_results/`:

- **`results.txt`** — human-readable summary: generation TPS (tg128), prompt TPS
  (pp512), idle vs **peak CPU temperature**, Intel **throttle-counter delta**,
  whether it crossed 85 °C, and the resulting **P_thermal (0 or −10)**.
- **`results.json`** — the same, machine-readable.
- **`thermal_timeline.csv`** — per-second temperature trace for the run (good
  for the video's thermal chart).
- **`submission_i5.json`** — (if `RUN_PROFILER=1`) the official profiler output
  with real throughput + thermal + memory on reference hardware. **This becomes
  the final submission JSON.**

## After it runs

Paste `bench_i5_results/results.txt` (or `results.json`) back here. Then we:

1. Fill the real TPS and thermal numbers into **REPORT.md** / **REFERENCE_BENCHMARK.md**
   (they currently carry the i9 dev-machine TPS as an explicit *upper bound*).
2. Recompute **S_perf** once we know the fastest-submission TPS (S_perf is
   normalized to that, not a fixed bar) — until then TPS is the input, not the score.
3. Confirm **P_thermal = 0** (the design target: physical-core threading runs
   cooler than all-threads — fewer active execution units — precisely to avoid
   the penalty; capture the real i5 peak temp here since the container can't).
4. Swap `submission_i5.json` in as the final submission artifact (it carries the
   real TPS/thermal that the Docker run on the Mac could not).

## Notes

- `bench_i5.sh` uses **physical cores** (not hyperthreads) — the measured sweet
  spot (~22% faster at generation than all logical threads on the i9: 9.6 vs
  7.9 t/s; and cooler, since the extra hyperthreads add heat, not speed).
- If `sensors` shows nothing after `sensors-detect`, the script falls back to
  `/sys/class/thermal/thermal_zone*` and still reports a peak; if even that is
  empty it says "unavailable" and still gives you TPS.
- Run it twice if the first run was from cold — thermals matter most on the
  *second* back-to-back run, which is closer to a real review session.
