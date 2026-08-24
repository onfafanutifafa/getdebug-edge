# Technical Report — getdebug-edge: Offline AI Code Review for Africa's Laptops

**Team ID:** getdebug-edge (registered on the ADTF portal)
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
- **Quantization:** GGUF Q4_K_M (~2.1 GB) — chosen over Q3_K_M because the
  contest scores the **bare model** (S_acc is 50% of the score) and Q4 leads the
  bare model on every measure that path sees: lm-eval `arc_easy` acc_norm 0.82
  vs Q3's 0.80, and our code-review **model-only** recall 68% vs Q3's 59%. The
  profiler measures 2.21 GB peak RSS, leaving ~4.8 GB of headroom under the 7 GB
  budget. Q3_K_M stays selectable via `--model` as the **efficiency
  alternative** (smaller ~1.72 GB download, lower RAM, fewer false positives) —
  better for real-world/low-RAM use, but it gives up the model-alone accuracy
  that judges score.
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
  - *Deterministic hybrid detectors* (`agent/detectors.py`): a cheap,
    LLM-free pass for the pattern-matchable classes the eval proved the 3B
    model reliably misses — hardcoded secrets (known token formats + secret-
    named string literals, excluding env-refs and placeholders), weak crypto
    (MD5/SHA-1, ECB mode, weak RNG in a security context), and secrets written
    to logs. These run alongside the model and their findings merge into the
    report. This is the *principle of not asking a 3B model to do what a regex
    does better*: it lifted measured recall from 68% to 86% with zero added
    false positives (a `hashlib.md5` match cannot hallucinate). It also mirrors
    the free-tier detectors of the hosted getdebug product.
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
  CPUs** — measured on an 8c/16t i9 (llama-bench, shipping Q4): 8 physical
  threads gave **9.6 t/s** generation; 16 logical threads gave **7.9 t/s** —
  physical cores are **~22% faster**. Memory-bandwidth-bound generation means
  SMT siblings add heat, not speed (compute-bound prompt processing is
  marginally faster at 16 threads, but generation is the scored metric). Fewer
  active execution units also run cooler; the profiler measured **no throttling**
  (`throttled=false`, CPU p99 51.6%). An optional inter-chunk pause guards long runs.
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

Shipping quant: **Q4_K_M** (see the quant sweep below).

| Metric | Value (Q4_K_M shipping) |
|---|---|
| Machine | Intel i9-9980HK (8c/16t), 64 GB RAM, macOS (development machine — faster than the ADTC reference; treat as upper bound) |
| **RAM at peak (ADTC profiler)** | **2.21 GB** (model process, profiler's standardized load) → **S_eff = 100×(7−2.21)/7 = 68** — this is the figure the judges' profiler scores |
| RAM at peak (full agent review) | ~3.5 GB reviewing a real multi-file repo (Python orchestrator + persistent llama-server + linters) — the tool's end-to-end footprint, not the profiler figure |
| Generation speed | 9.6 t/s (llama-bench, 8 physical threads, dev i9) |
| Thermal throttling | None (ADTC profiler: `throttled=false`, CPU p99 51.6%) — and physical-core threading keeps all-logical-thread throttling away (see Constraints) |

### Quantization sweep — why Q4_K_M, not Q3_K_M

Both are the same 3B model, compressed differently, measured on the same
development machine. The recall column is the **full-tool** (model + detectors)
recall, each quant scored against its own committed eval run. The Peak-RAM and
S_eff columns here are **dev-machine** measurements, kept for an internally
consistent apples-to-apples ranking of the quants; the authoritative shipping
figures come from the ADTC profiler and are given just below.

| Quant | Size | Recall (full tool) | Gen TPS | Peak RAM (dev) | S_eff (dev) |
|---|---|---|---|---|---|
| **Q4_K_M (shipping)** | **2.10 GB** | **19/22 = 86%** | **9.6** | **3.83 GB** | **47** |
| Q3_K_M (alternative) | 1.72 GB | 18/22 = 82% | 11.1 | 2.65 GB | 62 |

**Q4_K_M ships because the contest scores the bare model, and Q4 leads it.** The
judged path (§below) runs the raw GGUF — no agent, no detectors — so what wins is
model-alone quality: Q4 scores `arc_easy` acc_norm 0.82 vs Q3's 0.80, and
**model-only** code-review recall 68% vs Q3's 59%. Q3_K_M is the **efficiency
alternative** (still selectable via `--model`): 18% smaller, faster, lighter on
RAM, and fewer false positives (2 vs 5) — the better pick for real-world/low-RAM
use, but it gives up the model-alone accuracy judges score. Full-tool recall is
close (86% Q4 vs 82% Q3, both within noise at n=22) because the deterministic
detectors close most of the model gap on either quant. The importance-matrix
quants (IQ4_XS, IQ3_M) were also swept but are excluded here: their recall
numbers are unbacked by a committed eval run.

#### ADTC profiler, authoritative — Q4 vs Q3 head-to-head

Both quants were run through the **canonical ADTC profiler** in an identical
constrained container (`--cpus=4 --memory=8g`, swap disabled), which measures
the real automated accuracy (lm-eval `arc_easy`, acc_norm) and the peak RSS that
feeds S_eff. This is the apples-to-apples comparison on the *judges'* harness:

| Quant | Accuracy (arc_easy, n=50) | Peak RSS | S_eff | Throttled | 0.5·S_acc + 0.2·S_eff |
|---|---|---|---|---|---|
| **Q4_K_M (shipping)** | **0.82 (41/50)** | 2,209 MB | 68.4 | false | 54.68 |
| Q3_K_M (alternative) | 0.80 (40/50) | **1,840 MB** | **73.7** | false | **54.74** |

On the combined `0.5·S_acc + 0.2·S_eff` sub-score it is a **dead heat** (54.68 vs
54.74): Q3's RAM efficiency almost exactly cancels Q4's accuracy edge, and that
accuracy edge is **one arc_easy question out of 50**, well inside the ~5.7%
binomial standard error at n=50. But the two axes are not weighted equally in the
real contest — **S_acc is 50% of the score and S_eff only 20%**, and the judged
accuracy path runs the *bare model*, where Q4 also leads on our own code-review
recall (68% vs 59% model-only). So we ship Q4 for the accuracy the judges score;
Q3's tie-breakers (369 MB less RAM, 380 MB smaller download, better fit for the
Budget-Laptop bonus) make it the documented low-RAM alternative rather than the
default.

The raw profiler outputs for both runs are committed as evidence:
[`submission_q3.json`](./submission_q3.json) and
[`submission_q4.json`](./submission_q4.json) (schema 1.1.0, adtc-profiler 0.1.0,
identical `--cpus=4 --memory=8g` container).

Both quants were swept on the same tooling (llama.cpp b9960, adtc-profiler
0.1.0). Official scores are measured by the ADTC profiler on the standard
evaluation machine.

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

### How the contest scores accuracy vs. what our numbers measure

An important distinction, stated plainly so nothing here is misread. The
contest's automated accuracy (50% of the score) is measured by the ADTC
profiler running **lm-evaluation-harness** on a hidden benchmark dataset,
scoring the **raw model's continuation log-probabilities** — it does **not**
apply our chat template, and it does **not** run our agent, detectors, or
spec. So the automated Sacc reflects the *base model's capability and
quantization*, not our review methodology. (A separate qualitative judge read
of prompt responses may exist, where our baked methodology could help; the
automated stage does not use it.)

**Measured, not assumed.** We ran the profiler's own accuracy stage
(lm-eval `arc_easy`, the public proxy for the hidden set) on both shipping
candidates: **Q4_K_M (shipping) scored acc_norm = 0.82** (41/50) and Q3_K_M 0.80
(40/50). Q4's 0.82 is the actual automated Sacc our submission carries — a
*general-reasoning* number that is a different axis entirely from our code-review
recall below.

Everything below is **our own code-review benchmark** — a fair measure of *the
tool's* quality for a developer, and of *our* engineering — but it is a
different thing from the contest's lm-eval Sacc. We keep the two separate:
our detectors, spec-aware review, and baked methodology make the *product*
better; they do not move the automated contest number.

### Measured accuracy (our code-review benchmark) — reported honestly

We hold an internal benchmark (`eval/`) and score the shipping model
deterministically. We first measured on 10 seeded bugs and saw 80% recall — but
that sample was too small to trust (one miss moves the number 10 points). So we
**expanded it to 22 seeded bugs across 13 files + 8 clean control files** and
re-measured — which honestly *dropped* the LLM-only number to 68%. We then
addressed the gap (see below) with a deterministic hybrid pass:

| Configuration | Recall | False positives | Evidence |
|---|---|---|---|
| Base model, generic prompt, 10-bug corpus (flattering small sample) | 8/10 = 80% | 3 | `eval/baseline.json` |
| **Bare model, methodology baked into chat template (the judged path)** | **15/22 = 68%** | 5 | `eval/baseline_v2.json` |
| **Product path: agent (model + deterministic detectors, incl. JWT-no-expiry)** | **19/22 = 86%** | 5 | `eval/hybrid_v2.json` |

Two honesty points, both stated plainly. First, **expanding the sample dropped
the number from 80% to 68%** — the small sample flattered the tool, and even at
n=22 the interval is wide; this is a small internal benchmark, not a large
third-party one. Second, the 68% misses **clustered in pattern-matchable
classes** the model is weak on — hardcoded secrets, weak crypto (MD5),
secrets-in-logs.

There are exactly **two honest recall numbers**, one for each path:

- **The judged path** runs the bare GGUF on prompts, so the agent's detectors
  don't execute there. We bake the full review methodology (the analyze-first
  instruction, the injection/edge-case/crypto/secrets/authz/logging checklist,
  the output format) into the **chat template's default system prompt**
  (`tools/bake_persona.py`) so the bare model behaves as a security reviewer with
  no external harness. Measured with no external system message — exactly how a
  judge runs it — the shipping Q4_K_M model scores **68% recall (15/22)** with 5
  false positives on the clean controls. The methodology shapes *behavior* (what
  to look for, the output format), but it does not by itself close the
  pattern-matchable gap — that takes executable detectors, which don't run in the
  judged path.
- **The product path** (the actual tool a developer runs) adds the
  deterministic detectors (`agent/detectors.py`) — a hybrid that doesn't ask a
  3B model to do what a regex does better — lifting recall from **68% to 86%
  (19/22)** with no added false positives (a regex on `hashlib.md5` cannot
  hallucinate). The three still-missed bugs (broken access control / IDOR, and
  two business-logic validation cases) are genuinely reasoning-heavy: no regex
  catches them, and prompt-cue experiments to make the 3B reason about them
  measurably *lowered* accuracy — a real capability ceiling, honestly reported.

**What the hybrid still misses is honest and instructive** — the 4 remaining
are all *reasoning-heavy, not pattern-matchable*: IDOR (requires understanding
ownership), a missing quantity check, negative-percent logic, and a JWT that
never expires. Those genuinely need the model to reason about intent; no regex
fixes them. That is the correct division of labor.

**False positives** (5, unchanged by the hybrid) come from the model, not the
detectors: it over-flags some clean code — a correct `Decimal` money function, a
bounds-checked slice — and on a real Flask app misread parameterized queries as
injection. The detectors are high-precision by construction and added none.

### Independent validation — OWASP Benchmark (Java)

To check generalization beyond our self-authored corpus, we ran the shipping
model over a balanced 36-case sample of the **OWASP Benchmark** — independent,
externally-labeled Java, across the six categories we target (SQLi, command
injection, path traversal, weak hash, weak crypto, weak random). Java is a
language the tool was *not* tuned on, and the deterministic detectors are
Python/JS-specific and do not fire here, so this measures the **model's raw
detection ability** on unseen, taint-flow code. Results:

| Metric | Value |
|---|---|
| **Recall (real vulnerabilities)** | **23/24 = 96%** |
| **False-positive rate (safe decoys)** | **9/12 = 75%** |
| Precision | 23/32 = 72% |

The honest reading: the model has **high recall — it rarely misses a real
vulnerability** — but on adversarial *decoys* (safe code that mimics a
vulnerable shape) it **over-flags badly.** On the benchmark's discrimination
measure (recall − false-positive rate ≈ 21%) this is weak, because it doesn't
reliably distinguish a sanitized flow from an unsanitized one. This is
independent confirmation of the tool's core character — high recall, real
false-positive rate — and precisely why it is positioned as a **first-pass
triage a human confirms, not an authoritative gate.** (Detectors would not
help here — they are Python/JS-specific; extending them and adding data-flow
awareness is the clearest path to better precision.)

**Measurement caveat:** LLM ground truth is regex-matched against the model's
prose, which adds noise in both directions — we found and corrected one case
where the model caught a bug but phrased it differently than our matcher
expected. Treat the LLM numbers as indicative; the detector hits are exact.

**Bottom line: 86% of seeded bugs caught (full tool / hybrid), 68% for the bare
model a judge scores, a real but bounded false-positive rate from the model, and
remaining blind spots confined to reasoning-heavy classes.** getdebug-edge remains positioned as a **first-pass
triage that directs a human's attention — not an authoritative gate.**

---

## Screenshots

<!-- Screenshots to capture: terminal run, findings.json with a real
SQL-injection finding, VS Code Problems-panel integration, adtc-profiler
output, bench.sh comparison table. -->

---

## Known Limitations

- **Reasoning-heavy false negatives — helped by spec-aware review, but not a
  recall claim.** Without knowing intent, the model (and any regex) misses
  business-logic bugs: access control (IDOR), missing quantity/bounds checks,
  and similar. These are only "bugs" relative to what the code is *supposed* to
  do. The `--spec` feature helps: given a plain-language description of intended
  behavior, the model checks the code against it — in a **small test (3
  hand-picked business-logic bugs, with specs written to describe the intended
  behavior), all three flipped from missed to caught.** We deliberately do
  **not** turn this into a headline recall number: the specs were tailored to
  the bugs (teaching-to-the-test), the sample is tiny, and real-world recall
  depends entirely on the quality of the developer's spec. It is a *per-project
  capability*, not a benchmark figure — the honest tool number remains 86%
  (without a spec); a spec extends coverage on *your* code when you describe
  your rules.
- **The benchmark is small and self-authored** (22 seeded bugs + 8 clean
  controls). Numbers are honestly caveated with wide confidence intervals
  throughout, but the clearest next step for firmer, more generalizable figures
  is validation against a larger, *independent* ground-truth set — e.g. public
  SAST benchmarks (OWASP Benchmark, NIST Juliet) or real CVE-fixed files. This
  is future work, not done here.
- **The model's false-positive rate on clean code is real** (it over-flagged
  correctly-parameterized queries in the Flask case study). Mitigated by the
  first-pass-triage positioning, but not eliminated.
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
- Deterministic detectors (`agent/detectors.py`) are original, regex-based, and
  run fully offline — no third-party SAST engine is bundled.
- All agent code (`agent/`, `skills/`, scripts) is original work, GPL-3.0
  licensed (see `LICENSE`)
