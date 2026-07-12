# Technical Report — getdebug-edge: Offline AI Code Review for Africa's Laptops

**Team ID:** TODO-register-on-adtf-portal
**Domain:** coding_assistants
**Model:** Qwen2.5-Coder-3B-Instruct-Q4_K_M

---

## Problem

Developers and small teams (fintech, health-tech, SME software) across Africa
need baseline bug and vulnerability review before shipping — but the tools that
provide it (CodeRabbit-class AI reviewers, hosted SAST) assume reliable
internet, per-seat budgets, and permission to send source code to a foreign
cloud. Those three assumptions fail for most of the target users: connectivity
is intermittent, tooling subscriptions are priced in dollars for teams billing
in cedis and naira, and data-residency rules in banking and health often
prohibit code leaving the premises at all.

getdebug-edge delivers the same "flag bugs, explain them, suggest fixes"
workflow **free, offline, and private** on the $150–$500 laptops developers
here actually own: a security-weighted AI code reviewer that works in a
village, during an outage, and inside compliance rules. The target user is a
solo developer or small team in an eligible African country who wants a
pre-commit safety net without a cloud bill or a data-residency problem — the
mobile-money and school-fees scenarios in our test prompts are their daily
reality.

Running locally is not a preference here; it is the difference between the
tool existing for this user and not existing.

---

## Design Decisions

- **Base model:** Qwen2.5-Coder-3B-Instruct — the strongest open code-review
  model in its size class in our head-to-head testing (see below).
- **Quantization:** GGUF Q4_K_M (~2.1 GB) — the standard quality/memory
  balance point; leaves >3 GB of headroom under the 7 GB budget with the
  whole agent running.
- **Alternatives considered and rejected** (all measured, not guessed — full
  data in [`BAKEOFF.md`](./BAKEOFF.md) and [`bakeoff_results.json`](./bakeoff_results.json)):
  - *Qwen2.5-Coder-1.5B*: doubles speed (18.2 vs 9.6 t/s), halves RAM — but
    answered "NO_ISSUES" to code containing a blatant SQL injection. Accuracy
    is 50% of the score; rejected.
  - *Qwen3-4B-Instruct*: tightest prose, caught all seeded bugs, but 20%
    slower and ~1 GB more RAM with no added recall; rejected on value.
  - *Llama-3.2-3B*: the only small model with coherent Swahili (relevant to
    the African-language multiplier), but on a 765-line real-repo test it
    fabricated a high-severity SQL injection in a file containing no SQL, and
    the hallucination survived a precision-mandated prompt. A security tool
    that invents vulnerabilities was disqualifying; rejected.
  - *Gemma-3-4B*: missed the seeded division-by-zero, slowest of the accurate
    group, language coverage no better in practice (its Yoruba probe drifted
    into Indonesian, its Amharic probe came back in Thai); rejected.
  - *DeepSeek-Coder-1.3B / GLM-Edge-4B*: produced zero findings / no
    advantage on any measured axis; rejected.
- **Tools used and why:**
  - *llama.cpp / llama-server* (contest-mandated runtime): the model loads
    **once** into a persistent server; every chunk is a localhost HTTP call.
    The alternative (spawning `llama-cli` per chunk) reloads 2 GB from disk
    per call — measured as the single biggest throughput/thermal hazard.
  - *Python 3 standard library only* for the agent: zero dependencies to
    install on the target laptop.
  - *Local linters as model context*: the agent runs whatever is available
    (`ruff` → `pyflakes` → `py_compile`; `node --check`) and feeds trimmed
    output to the model as hints to verify — measurably improved recall on
    unvalidated-input findings. Degrades gracefully to nothing installed.
  - *adtc-profiler* for pre-submission self-checks against the official
    metrics.
- **Key engineering decisions from testing:**
  - *Chat template correctness*: all prompts go through `/v1/chat/completions`
    so llama-server applies the model's own ChatML template — bypassing it
    measurably degrades instruct-model output.
  - *Deterministic decoding* (temperature 0 + repeat penalty 1.1): identical
    input must produce an identical report; at temp 0.2 the same chunk
    alternated output formats between runs and one format evaded parsing.
  - *Analyze-first prompting*: terse "respond in format X or say NO_ISSUES"
    prompts made the 3B model take the escape hatch and miss a SQL injection;
    letting it reason briefly before the findings list recovered full recall.
  - *Findings parsed from severity lines, never a sentinel*: the model
    sometimes appends "NO_ISSUES" after a valid findings list.
- **Fine-tuning: attempted, measured, and rejected** (full data in
  [`finetune/RESULTS.md`](./finetune/RESULTS.md)). We did not assume a LoRA
  fine-tune would help — we built a seeded-bug eval harness and tested it.
  Two LoRA runs on a free Colab T4, each scored on the **original 10-bug
  corpus** (this comparison predates the 22-bug expansion above; all three
  configs ran on the same 10-bug set, so the comparison is internally valid):

  | Configuration | Recall (10-bug corpus) | False positives | 
  |---|---|---|
  | Base model (prompt + skill + linter) | **8/10** | 3 |
  | LoRA, 50 hand-authored examples | 5/10 | 2 |
  | LoRA, 100 examples (43 multi-bug) | 1/10 | 1 |

  Both regressed. The 50-example run learned *terseness* (stop after one
  finding); the 100-example run *overfit to templated data* and defaulted to
  "NO_ISSUES" on differently-written code. Diagnosis: Qwen2.5-Coder-3B is
  already a strong code reviewer, and small fine-tunes on narrow data can only
  narrow it — beating the base would require thousands of diverse, real
  examples with no guaranteed win, out of scope for the timeline. **We ship
  the well-prompted base model.** The reproducible pipeline and the eval gate
  are retained for a future large-corpus effort. This is the contest's
  systems-engineering thesis in miniature: we measured our way to *not* adding
  complexity, and the accuracy came from the system around the model (prompt
  design, skill methodology, linter context, deterministic decoding) rather
  than from retraining it.

---

## Constraints

- **Target hardware:** ADTC Standard Laptop — 8 GB RAM (7 GB evaluation
  ceiling), Intel i5 10th–12th gen / Ryzen 5 3000–5000, integrated graphics
  only, Ubuntu 22.04.
- **No GPU acceleration** — pure CPU inference via llama.cpp
  (`--n-gpu-layers 0` explicit); context capped at 3072 tokens and KV cache
  quantized to q8_0 (with flash attention, required for quantized V-cache) to
  bound memory.
- **Compute/thermal:** threads default to **physical cores, not logical
  CPUs** — measured on an 8c/16t machine: 15 threads gave 14.7 t/s at 98.7°C
  with throttling to 56% CPU speed; 8 threads gave 18.2 t/s at 68.8°C with no
  throttling. Memory-bandwidth-bound generation means SMT threads add heat,
  not speed. An optional inter-chunk pause guards long runs.
- **Connectivity:** assumed absent. One-time model download
  (`download_model.sh`); after that, zero network calls — the review loop is
  entirely localhost. This also serves users whose constraint is policy
  (data residency) rather than infrastructure.
- **Power:** the tool tolerates interruption (per-file processing, report
  written at the end from accumulated state) and the physical-core threading
  choice reduces sustained power draw versus saturating all logical cores —
  relevant on battery during outages, common in the target environment.
- **Data:** no training or fine-tuning data required; the model runs as
  released, so there is no dataset-collection burden on the user.

---

## Benchmarks

| Metric | Value |
|---|---|
| Machine | Intel i9-9980HK (8c/16t), 64 GB RAM, macOS (development machine — faster than the ADTC reference; treat as upper bound) |
| RAM at peak | 3.59 GB (full agent run incl. llama-server; adtc-profiler concurs: 3.59 GB) |
| Time to first token | 6.1 s (512-token prompt, CPU prompt processing) |
| Generation speed | 9.6 t/s (llama-bench, 8 threads) / 12.8 t/s (adtc-profiler) |
| Thermal throttling | None observed at physical-core threading (71.6°C peak; forcing 15 threads throttled — see Constraints) |

These are self-reported development benchmarks (llama.cpp b9960,
adtc-profiler 0.1.0, 2026-07-11). Official scores are measured by the ADTC
profiler on the standard evaluation machine.

**Reference-constraint run** (2026-07-12, full detail in
[`REFERENCE_BENCHMARK.md`](./REFERENCE_BENCHMARK.md)): the agent was also run
inside a container pinned to the contest constraints — **Ubuntu 22.04, 4 CPUs,
8 GB RAM with swap disabled**, llama.cpp b9975, Python 3.10.12. Result: a full
review of a real Flask web app completed with **3.54 GB peak RAM, no OOM, no
crash** (exit 0) — verifying safety under the 8 GB disqualification ceiling on
the actual evaluation OS. 4-core generation throughput was 6.1 t/s (indicative;
absolute clock still needs true i5 hardware). The case study also honestly
surfaced the 3B model's precision ceiling — it over-flagged correctly
parameterized queries as injection — which is why the tool is positioned as a
first-pass triage, not an authoritative gate.

### Measured accuracy — reported honestly, with the sample caveat

We hold an internal benchmark (`eval/`) and score the shipping model
deterministically. We first measured on 10 seeded bugs and saw 80% recall — but
that sample was too small to trust (one miss moves the number 10 points). So we
**expanded it to 22 seeded bugs across 13 files + 8 clean control files** and
re-measured — which honestly *dropped* the LLM-only number to 68%. We then
addressed the gap (see below) with a deterministic hybrid pass:

| Configuration | Recall | False positives |
|---|---|---|
| Base model alone, 10-bug corpus (flattering small sample) | 8/10 = 80% | 3 |
| Base model alone, 22-bug corpus | 15/22 = 68% | 5 |
| **Shipping: hybrid (model + deterministic detectors)** | **18/22 = 82%** (95% CI 61–93%) | **5 (unchanged)** |

Two honesty points, both stated plainly. First, **expanding the sample dropped
the LLM-only number from 80% to 68%** — the small sample flattered the tool, and
even at n=22 the interval is wide; this is a small internal benchmark, not a
large third-party one. Second, the 68% misses **clustered in pattern-matchable
classes** the model is weak on — hardcoded secrets, weak crypto (MD5),
secrets-in-logs — so we added cheap, deterministic detectors for exactly those
(`agent/detectors.py`): a hybrid that doesn't ask a 3B model to do what a regex
does better. That lifted recall to **82% with zero new false positives** (a
regex on `hashlib.md5` cannot hallucinate).

**What the hybrid still misses is honest and instructive** — the 4 remaining
are all *reasoning-heavy, not pattern-matchable*: IDOR (requires understanding
ownership), a missing quantity check, negative-percent logic, and a JWT that
never expires. Those genuinely need the model to reason about intent; no regex
fixes them. That is the correct division of labor.

**False positives** (5, unchanged by the hybrid) come from the model, not the
detectors: it over-flags some clean code — a correct `Decimal` money function, a
bounds-checked slice — and on a real Flask app misread parameterized queries as
injection. The detectors are high-precision by construction and added none.

**Measurement caveat:** LLM ground truth is regex-matched against the model's
prose, which adds noise in both directions — we found and corrected one case
where the model caught a bug but phrased it differently than our matcher
expected. Treat the LLM numbers as indicative; the detector hits are exact.

**Bottom line: ~82% of seeded bugs caught (hybrid), a real but bounded
false-positive rate from the model, and remaining blind spots confined to
reasoning-heavy classes.** getdebug-edge remains positioned as a **first-pass
triage that directs a human's attention — not an authoritative gate.**

---

## Screenshots

<!-- TODO before submission (shot list in SUBMISSION.md): terminal run,
findings.json with a real SQL-injection finding, VS Code Problems-panel
integration, adtc-profiler output, bench.sh comparison table. -->

---

## Known Limitations

- Chunking is token-budgeted but line-boundary-based; tree-sitter AST
  chunking is future work.
- Findings parsing is regex-based, tuned for recall over precision.
- The base model's license (qwen-research on the 3B GGUF; the 1.5B sibling is
  Apache 2.0) is being re-verified before final submission.
- `--lang` (finding explanations in other languages) ships as an honest
  product feature; quality varies by language and the African Language
  multiplier is deliberately **not** claimed — our probes showed only
  Swahili-via-Llama was credible at this model size, and that model failed
  our accuracy bar (see `BAKEOFF.md`).
- Benchmarks above are from a development machine faster than the reference
  laptop; reference-hardware numbers to follow.

---

## Attribution

- Base model: Qwen2.5-Coder-3B-Instruct (Qwen team, Alibaba Cloud) — official
  GGUF quantization, hosted on Hugging Face
- Inference runtime: [llama.cpp](https://github.com/ggml-org/llama.cpp) (ggml.ai)
- Self-check tooling: [adtc-profiler](https://github.com/Africa-Deep-Tech-Foundation/adtc-profiler)
  (Africa Deep Tech Foundation)
- Optional linters surfaced to the model: ruff / pyflakes / Node.js `--check`
- All agent code (`agent/`, `skills/`, scripts) is original work, GPL-3.0
  licensed (see `LICENSE`)
