# getdebug-edge

**CodeRabbit-class code review — free, offline, and private — built for the
laptops and realities African developers actually have.**

An on-device, offline autonomous coding agent for the Africa Deep Tech Challenge
2026 — Laptop LLM Challenge. Point it at a project folder and a small AI model
running entirely on your machine flags bugs, security vulnerabilities, and
correctness issues with suggested fixes. No cloud, no account, no per-seat
pricing, and your code never leaves your laptop — which for fintech and
health-tech teams is not a convenience but a compliance requirement.

getdebug-edge is a from-scratch, contest-eligible spinoff of [getdebug](https://getdebug.dev)'s
"analyze → flag → fix" workflow, rebuilt to run entirely on an 8 GB commodity laptop
with integrated graphics and zero cloud dependency. Where getdebug is a hosted SaaS
calling a cloud LLM, getdebug-edge runs a small quantized coding model locally via a
single persistent `llama-server` process (model loaded once, reused for every chunk)
and orchestrates its own observe → think → act loop over localhost — no cloud API,
no network call once the model is downloaded. Hardware-tuning choices (context cap,
KV-cache quantization, threading, RAM safety margin) are documented in `SCOPE.md` §7.

See [`SCOPE.md`](./SCOPE.md) for the full problem statement, constraints, model
choice, architecture, and benchmark plan. See [`REPORT.md`](./REPORT.md) for the
contest-required technical writeup (fill in once benchmarks are run).

## Status

Scaffold only — not yet functional end-to-end. This repo currently contains:

- `metadata.json` — contest submission metadata (placeholders need filling in:
  `team_id`, `submitter.github_handle`, final `test_prompts`)
- `download_model.sh` — downloads the Qwen2.5-Coder-3B-Instruct Q4_K_M GGUF weights
- `agent/agent.py` — starter CLI: launches a persistent `llama-server`, chunks a
  target repo by token budget, sends each chunk through the model's chat
  template via `/v1/chat/completions`, aggregates findings into a report, shuts
  the server down on exit; also has a `--prompt` one-shot mode for demos
- `bench.sh` — llama-bench comparison across every downloaded quant/model size
- `REPORT.md` — skeleton for the required contest writeup

## Install llama.cpp

The contest evaluation OS is **Ubuntu 22.04 LTS** (CPU-only). Build from source
with native optimizations — the prebuilt generic binaries leave CPU throughput
on the table, and throughput is 30% of the contest score:

```bash
sudo apt install -y build-essential cmake git
git clone https://github.com/ggml-org/llama.cpp
cmake -S llama.cpp -B llama.cpp/build -DGGML_NATIVE=ON -DCMAKE_BUILD_TYPE=Release
cmake --build llama.cpp/build --config Release -j
sudo cp llama.cpp/build/bin/llama-server llama.cpp/build/bin/llama-bench /usr/local/bin/
```

On macOS (development only — not the target hardware): `brew install llama.cpp`.

## Quick start

```bash
# 1. Download model weights (3b | 1.5b | all)
bash download_model.sh

# 2a. Review a whole codebase
python3 agent/agent.py --target /path/to/some/repo --out findings.json

# 2b. One-shot question (demo mode — also how the contest test_prompts run)
python3 agent/agent.py --prompt "Review this function for bugs: ..."

# 2c. Finding explanations in another language (code terms stay in English)
python3 agent/agent.py --target /path/to/repo --lang Swahili --out findings.json
```

New to all of this? **[USER_MANUAL.md](./USER_MANUAL.md)** walks through setup
and usage step by step, including how to get the best speed and thermal results.

The agent also:
- loads **[skills/SKILL.md](./skills/SKILL.md)** into the system prompt — a review
  methodology (injection checklist, edge cases, DRY-with-drift detection, fix
  style) that steers the model; swap in your own with `--skill path.md`
- runs **local linters** when available (`ruff`/`pyflakes`/`py_compile` for
  Python, `node --check` for JS) and feeds their output to the model as
  static-analysis hints to verify — disable with `--no-lint`
- runs a **deterministic hybrid pass** ([agent/detectors.py](./agent/detectors.py))
  for pattern-matchable classes the 3B model reliably misses — hardcoded
  secrets, weak crypto (MD5/SHA-1, ECB), secrets written to logs — lifting
  measured recall from 68% to 82% with zero added false positives (see
  REPORT.md)

The agent starts and stops its own persistent `llama-server` — no separate
server process to manage, and zero network calls after the model is on disk.

## Benchmarking & local self-check before submitting

```bash
# Compare 3B vs 1.5B TPS on this machine (S_perf is 30% of the score)
bash download_model.sh all && bash bench.sh

# Official profiler (RAM / TPS / thermal, same checks as the judges)
pip install "git+https://github.com/Africa-Deep-Tech-Foundation/adtc-profiler.git"
adtc-profiler run --submission . --mode participant --output submission.json --skip-accuracy
```

## What it is

A **code reviewer and debugging assistant**, not a step-through debugger: it
reads code and flags bugs, vulnerabilities, and correctness issues with
suggested fixes (`--target`), and answers one-off debugging questions
(`--prompt`). It never edits your files.

## Why this exists — and who is behind it

getdebug-edge shares its thesis with [getdebug.dev](https://getdebug.dev), an
AI code-security product by **Masenu Cybernetics**: developers ship fewer
vulnerabilities when review is built into how they work. But getdebug.dev, like
every tool in its class (CodeRabbit, Snyk, cloud SAST), assumes reliable
internet, a cloud LLM, and a budget — assumptions that exclude most developers
on the continent.

getdebug-edge is the answer to that exclusion: a **free, open-source,
fully offline** sibling, purpose-built for the ADTC 2026 Laptop LLM Challenge
and for the $150–$500 laptops African developers actually own. It shares no
code or infrastructure with the cloud product — it is an original, from-scratch
build against the contest's constraints (llama.cpp, 8 GB RAM, zero network).

The commitment: getdebug-edge stays free and open-source regardless of what
happens commercially with its cloud sibling. Prize support from this
competition goes toward keeping it maintained, benchmarked on real budget
hardware, and extended to more African languages (see `SCOPE.md` §7b for the
Khaya AI roadmap).

## License

getdebug-edge is licensed under the **GNU General Public License v3.0** (see
[`LICENSE`](./LICENSE)). GPL-3.0 is a copyleft license: you are free to use,
study, run, and modify this code — but any distributed derivative work must
also be released under GPL-3.0 with source. In short, it stays free and open
for everyone; it cannot be taken closed-source.
