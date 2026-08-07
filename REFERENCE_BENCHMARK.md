# Reference-constraint benchmark + real-repo case study

Run 2026-07-12 in a **Docker container pinned to the contest constraints**:
Ubuntu 22.04, **4 CPUs, 8 GB RAM with swap disabled** (`--cpus=4
--memory=8g --memory-swap=8g`), llama.cpp b9975 (prebuilt Ubuntu-x64),
Python 3.10.12 (Ubuntu 22.04 system Python), shipping model
`getdebug-edge-3b-q4_k_m.gguf`.

**Fidelity note (read this):** the container runs on the dev machine's Intel
i9 cores capped to 4, so absolute **throughput is indicative, not a true
Intel-i5 clock** — that still requires real reference hardware before final
submission. What this test validates definitively (hardware-independent):
runs on the exact contest OS, and **memory safety under the 8 GB
disqualification ceiling with no swap**.

## Results

| Metric | Value | Notes |
|---|---|---|
| OS / runtime | Ubuntu 22.04, llama.cpp b9975, Python 3.10.12 | contest-representative |
| Throughput (generation) | **6.1 t/s** (tg128) | 4 threads; prebuilt generic binary understates vs a `-march=native` build |
| Throughput (prompt) | 14.5 t/s (pp512) | 4 threads |
| **Peak RAM (full agent run)** | **3.54 GB** | via cgroup `memory.current` sampling — **Q4_K_M-era** (2026-07-12, before the Q3 switch); the whole agent (llama-server + Python orchestrator + linters), not the model process alone |
| **OOM / crash** | **None** — `OOMKilled=false`, exit 0 | passes the disqualification condition with comfortable headroom under 8 GB |
| Real-repo review | 5 files, 266 s | Flask tutorial app (auth + DB + blog) |

> **Note — two different RAM numbers, reconciled.** This 3.54 GB is the
> *whole-agent* footprint on the earlier **Q4_K_M** model. The **canonical ADTC
> profiler**, which is what the judges score for S_eff, measures the *model
> process* under its standardized load — and on the shipping **Q3_K_M** that is
> **1.84 GB → S_eff = 74** (`throttled=false`; see REPORT.md). So the contest
> S_eff figure is 74, not the 49 this legacy full-agent Q4 run would imply; the
> two measure different scopes and different quants.

**The headline result: no OOM, no crash under a hard 8 GB ceiling** — even the
heavier full-agent Q4 run at 3.54 GB stayed safe. The single most dangerous
contest failure mode (out-of-memory = instant disqualification) is verified safe
on the actual evaluation OS, with the whole agent (persistent llama-server +
Python orchestrator) running.

## Real-repo case study — and an honest limitation

Target: the official **Flask tutorial application** (`pallets/flask`
`examples/tutorial/flaskr`) — a real, well-written web app with authentication,
a SQLite layer, and blog CRUD. The agent flagged the auth and DB layers — the
right *areas* to scrutinize in a web app — but two of its findings were **false
positives**, and this is worth stating plainly:

- It reported `[high] SQL injection` in `auth.py`, but every query there is
  correctly parameterized (`execute("SELECT * FROM user WHERE username = ?",
  (username,))`). The model misread safe placeholder queries as concatenation.
- It reported `[high] injection` on `db.py`'s `executescript`, which runs a
  bundled static `schema.sql` via `open_resource` — trusted input, not a
  vector.

The remaining findings (missing explicit error handling, no input-validation
guards) were generic and debatable rather than wrong.

**What this tells us honestly:** the 3B model errs toward *flagging* — high
recall on genuinely buggy code (~68%, 15/22 on the expanded seeded eval), but a real
false-positive rate on well-written code (consistent with the clean-file FPs in
`eval/`). That is the precision ceiling of a 3B model, and it is why
getdebug-edge is positioned as a **first-pass triage that surfaces areas for
human confirmation**, not an authoritative gate. A developer reviewing the
flagged auth/DB code and confirming the queries are safe still spent their
attention in the right place — but the tool must not be trusted to auto-approve
or auto-reject on its findings alone. We report this rather than cherry-pick a
cleaner target, because a security tool's honesty about its own false-positive
rate is part of its trustworthiness.

## Reproduce

```bash
docker run -d --name edgebench --cpus=4 --memory=8g --memory-swap=8g \
  -v $PWD:/edge:ro ubuntu:22.04 sleep infinity
# install python3 + llama.cpp b9975 (ubuntu-x64), then:
python3 /edge/agent/agent.py --target <writable-repo-copy> --threads 4 --no-cache
# peak RAM via: cat /sys/fs/cgroup/memory.current  (sample during the run)
```
