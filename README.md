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

**Working end-to-end and measured.** Verified on Ubuntu 22.04 in a container
pinned to the contest spec (4 CPUs, 8 GB RAM, swap disabled): a full review
runs at ~3.5 GB peak RAM with no OOM and no crash. Measured hybrid recall is
**82%** on an internal seeded-bug benchmark (see [`REPORT.md`](./REPORT.md) for
the honest accuracy characterization, including false-positive/negative rates,
and [`BAKEOFF.md`](./BAKEOFF.md) for the six-model comparison).

Key components:
- `agent/agent.py` — the agent: launches a persistent `llama-server`, chunks a
  target repo by token budget, reviews each chunk through the model's chat
  template, runs deterministic detectors + local linters, caches results, and
  aggregates findings; `--prompt` one-shot mode for demos, `--diagnostics` for
  VS Code
- `agent/detectors.py` — deterministic hybrid pass (secrets, weak crypto, logs)
- `eval/` — seeded-bug benchmark harness and its results
- `finetune/` — the LoRA pipeline and the measured decision to ship the base
  model (see [`finetune/RESULTS.md`](./finetune/RESULTS.md))
- `bench.sh` / `REFERENCE_BENCHMARK.md` — throughput + constraint benchmarks

Remaining before final submission: `team_id` + `github_handle` in
`metadata.json`, and a true reference-hardware (Intel i5) throughput run.

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
  secrets, weak crypto (MD5/SHA-1, ECB), secrets written to logs, JWTs with no
  expiry — lifting measured recall from 68% to 86% with zero added false
  positives (see REPORT.md)
- supports **spec-aware review** (`--spec spec.md`, or a `SPEC.md` at the
  target root): describe how the app *should* behave, and the model checks the
  code against your intent — the tractable way to surface **business-logic
  bugs** (wrong amounts, missing guards, access-control gaps) that generic
  review can't find, because they're only bugs relative to intent. In a small
  test (3 business-logic bugs) a spec flipped all three from missed to caught —
  but this is a *per-project capability whose payoff depends on your spec's
  quality*, not a fixed recall number, so we don't headline a percentage for it.
- can **suggest code fixes** (`--fix`): for each flagged chunk it emits
  corrected code into the report's `fix_code` field (CodeRabbit-style suggested
  change). Because the base is a *code* model, it also writes code on request
  via `--prompt` ("write a function that…"). Opt-in — `--fix` roughly doubles
  inference on files with findings, and the fixes are a starting point to
  review, not guaranteed-complete at this model size.

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

## Model vs. tool — two honest numbers

getdebug-edge has **two** measured recall numbers, because there are two ways to
run it, and we state both plainly so there's no ambiguity:

- **The model alone — 82%** (18/22 seeded bugs). The bare GGUF answering prompts
  with the review methodology baked into its chat template, *no harness*. This
  is what a contest judge scores when they run the model directly.
- **The full tool — 86%** (19/22). Adds the agent's deterministic detectors
  (hardcoded secrets, weak crypto, JWT-no-expiry) and, with a `SPEC.md`,
  business-logic checks. This is what a developer gets running `agent.py`.

The gap is by design — it reflects what can and can't live *inside the model*
(weights + chat template) versus what must run in the *tool* (the Python agent):

| Lives in the model ✅ | Lives in the tool (harness) |
|---|---|
| Review methodology & instructions | Deterministic regex detectors (run at review time) |
| The behavior to *look for* secrets, MD5, injection | The regex's 100%-reliable *guarantee* |
| The capability to check code against a spec | Your project's specific `SPEC.md` (per-project data) |
| **→ this is the 82% a judge scores** | **→ this is what lifts it to 86% + logic bugs** |

In short: *instructions and behaviors* bake into the model; *executable code and
per-project data* stay in the tool. The base weights are unchanged from
Qwen2.5-Coder-3B — we made the model **focused** (methodology in the template)
and **augmented** it (detectors + spec), not smarter. See
[`REPORT.md`](./REPORT.md) for the full measured breakdown.

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
