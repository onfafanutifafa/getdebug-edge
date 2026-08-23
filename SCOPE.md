# getdebug-edge — Project Scope

**Contest:** Africa Deep Tech Challenge 2026 — Laptop LLM Challenge
**Gate 1 deadline:** Aug 25, 2026 @ 11:45pm PDT
**Status:** registered — team_id `getdebug-edge` on the ADTF portal; repo public.

## 1. Problem

Developers and small dev teams across Africa doing security- and correctness-sensitive
work (fintech, health-tech, SME software) often can't afford or reliably access
cloud-based code-review tooling: per-seat SaaS pricing, per-token LLM API costs, and
the bandwidth to ship a codebase to a cloud service are all real blockers outside
major hubs. getdebug (the cloud product this spins off from) solves this problem but
depends entirely on hosted infrastructure and a cloud LLM.

**getdebug-edge** asks: can the same "flag bugs and vulnerabilities, suggest a fix"
workflow run entirely on a $400–500 commodity laptop, with zero network calls once
the model is on disk?

Target user: a solo developer or small team in an eligible African country who wants
a pre-commit / pre-ship safety net without a cloud bill or a data-residency problem.

## 2. Constraints (from the ADTC Standard Laptop profile)

| Constraint | Detail | Design implication |
|---|---|---|
| Compute | Intel i5 10–12th gen / Ryzen 5 3000–5000, integrated graphics only | CPU-only inference via llama.cpp — no CUDA/ROCm path |
| RAM | 8 GB total, 7 GB peak budget enforced by the profiler | Model + KV cache + agent process must stay well under 7 GB |
| Storage | 256 GB SSD | Model file should be a few GB at most |
| Connectivity | Must run 100% offline during evaluation | One-time model download via `download_model.sh`; zero calls during inference |
| Thermal | -10 pts if core temp > 85°C or throttling detected | Avoid sustained 100% CPU; chunk work, allow cooldown between large files |

## 3. Domain declaration

`metadata.json` only allows **one** primary domain. Declaring **`coding_assistants`**
because:

- It has the most established accuracy benchmarks, which matters since accuracy is
  50% of the score (`S_acc`).
- The judging rubric for this domain (code generation, debugging help, tutoring)
  maps directly onto getdebug's existing product thesis.

The **execution architecture is an autonomous agent** (observe → think → act loop,
same pattern as everweep's ReAct engine, just local and code-focused). That's
captured in the `cross_disciplinary_pairing` field and in the README rather than as
the primary domain — `autonomous_ai_agents` is a newer, less-benchmarked track and a
riskier place to be judged on raw accuracy.

## 4. Model & quantization

| | Primary | Fallback |
|---|---|---|
| Model | Qwen2.5-Coder-3B-Instruct | Qwen2.5-Coder-1.5B-Instruct |
| Quantization | GGUF Q4_K_M (~2.1 GB) | GGUF Q4_K_M (~1.0 GB) |
| Why | Strongest code-task benchmarks at this size class; official GGUF releases; active llama.cpp support | Use if TPS on target hardware is uncompetitively low (~15 TPS is a rough planning target, not an official bar — S_perf is relative to the fastest submission) or RAM headroom is too tight once agent overhead is added |

Runtime is fixed by the contest rules: **llama.cpp only**, GGUF weights only.

Note: Qwen2.5-Coder-3B ships under the **Qwen Research License** — VERIFIED
2026-08-09 as **non-commercial (research/evaluation) only** (not Apache-2.0, unlike
the 1.5B/7B). Contest hosting is compliant with attribution; commercial downstream
needs a Qwen license or an Apache-2.0 model swap. See the README License section.

## 5. Architecture

```
target repo
    │
    ▼
[observe]  walk the repo, chunk files by a token-budgeted char estimate
           (derived from --ctx-size, not a fixed line count; tree-sitter AST
           chunking is a stretch goal, matching getdebug's original approach)
    │
    ▼
[think]    a single persistent llama-server (model loaded once) prompted per
           chunk over localhost HTTP: flag bugs, obvious vulnerabilities, and
           correctness issues
    │
    ▼
[act]      aggregate findings into a structured report (JSON + human-readable
           Markdown); optionally propose a fix for simple, safe cases
```

The model loads once into `llama-server`; every chunk is a fast local HTTP
call against the already-resident model. Zero network calls leave the
machine after the model file is downloaded. See §7 for why the server is
persistent rather than reloading per chunk.

## 6. Benchmark plan

1. Run `adtc-profiler run --mode participant --skip-accuracy` locally before every
   submission to catch RAM/latency regressions early.
2. Track: tokens/sec generation (~15 TPS is a rough self-check target, not the
   official bar — S_perf is relative to the fastest submission), peak RSS (<7 GB),
   first-token latency, thermal behavior over a sustained run.
3. Write the 2 required `test_prompts` as realistic African-context debugging tasks
   (see `metadata.json` — draft prompts included, refine before submission).
4. If not developing on hardware matching the exact reference spec, note the delta
   (CPU model, actual RAM) in `REPORT.md` so judges can sanity-check the numbers.

## 7. Hardware optimization

Every lever below maps directly to one of the profiler's scoring terms
(`S_perf`, `S_eff`, `P_thermal`) or to the hard OOM-disqualification rule —
these aren't generic best practices, they're chosen because of how this
specific contest scores and disqualifies submissions.

| Lever | Choice | Why |
|---|---|---|
| **Model reuse** | One persistent `llama-server` process, model loaded once, all chunks sent as HTTP requests | The original scaffold shelled out to `llama-cli` per chunk, reloading the full model from disk every call. That multiplies disk I/O and repeated load spikes — bad for throughput (`S_perf`) and for thermal load (`P_thermal`). Fixed in `agent/agent.py`. |
| **Context window** | `--ctx-size 3072`, explicit — not the model's native 32k | KV-cache memory scales directly with context size. Leaving it at the model default would blow the RAM budget for no benefit, since chunked review doesn't need long context anyway. |
| **KV cache quantization** | `--cache-type-k q8_0 --cache-type-v q8_0` **plus `--flash-attn on`** | Roughly halves KV-cache memory vs. the f16 default, at minimal quality cost. **Quantized V-cache requires flash attention in llama.cpp — without `-fa` the server refuses to start.** Honest sizing note: at ctx 3072 on a 3B GQA model the whole KV cache is only ~100 MB f16, so this saves ~50 MB — keep it, but it's a rounding error next to the model-size lever below. |
| **Chat template** | Prompts sent via `/v1/chat/completions`, never raw `/completion` | llama-server applies the model's own ChatML template from GGUF metadata. Bypassing the template on an instruct model measurably degrades output quality — this is an `S_acc` (50%-weight) lever, bigger than any runtime flag. Judges running the GGUF in Ollama/LM Studio get the template automatically, so agent behavior and judged behavior stay consistent. |
| **Threads** | **Physical core count** (not logical CPUs, not `cores-1`) | Measured on an 8c/16t i9: 15 threads → 14.7 TPS at 98.7°C with throttling to 56% CPU speed; 8 threads → 18.2 TPS at 68.8°C, no throttle. Generation is memory-bandwidth-bound, so SMT siblings add contention and heat, not speed. One change improved `S_perf` ~25% AND eliminated the `P_thermal` risk. |
| **mmap, no mlock** | Default mmap, `--mlock` intentionally omitted | Lets the OS page the model in/out via the page cache instead of force-pinning it fully resident, which helps the whole process (model + KV cache + Python agent) stay inside the 7 GB budget rather than guaranteeing the model's full footprint is locked in RAM at all times. |
| **Chunk sizing** | Token-budgeted (char-estimate) chunking derived from `--ctx-size`, not a fixed line count | A fixed 200-line window can be tiny or enormous in tokens depending on the file — token-budgeted chunking keeps prompt+output reliably inside the context cap regardless of file density. |
| **Thermal pacing** | Small pause (`INTER_CHUNK_PAUSE_SECONDS`, default 0.3s) between chunk requests | Cheap insurance against sustained 100%-CPU stretches on long repos. With physical-core threading the measured peak was only 71.6°C during a full agent run, so this is now secondary — keep unless profiler numbers say otherwise. |
| **Deterministic decoding** | `temperature 0` (greedy) | At temp 0.2 the same chunk alternated between findings formats across runs — one format evaded the parser, so a real SQL injection was flagged on one run and silently missed on the next. A scanner must be reproducible; greedy decoding makes identical input → identical report (verified 2/2 runs). |
| **Prompt shape** | Analyze-first, then findings list; findings detected by parsing severity lines, never the NO_ISSUES sentinel | A/B/C tested against the live 3B model: terse "respond in format X or say NO_ISSUES" prompts made it answer NO_ISSUES on code with a blatant SQL injection (the escape hatch was the most salient instruction). Letting it reason for 2–3 sentences first recovered full recall. It also sometimes appends NO_ISSUES *after* a valid findings list, so detection keys on `- [severity]` lines (markdown-decoration-tolerant regex). |
| **Port selection** | Ephemeral free port by default (`--port 0`), never a fixed 8080 | Found in testing: an unrelated app on 8080 answered `/health` with 200 and the agent "reviewed" a repo against a server that wasn't running the model, reporting errors as findings. |
| **RAM safety margin** | Target peak RSS meaningfully under the 7 GB budget (aim ~5–5.5 GB), not right up against it | The profiler tolerates ±15% variance on memory metrics before flagging, and OOM during evaluation is an automatic disqualification — headroom protects against measurement variance across dev machine vs. eval sandbox. |
| **GPU layers** | `--n-gpu-layers 0`, explicit | Reference hardware is integrated-graphics-only and the eval framework runs llama.cpp's CPU path via `llama-bench`; forcing CPU-only avoids iGPU backend compatibility risk in the eval sandbox rather than chasing marginal iGPU speedups. |
| **Model size** | **3B — decided empirically 2026-07-11** | The 1.5B doubles TPS (18.2 vs 9.6) and halves RAM (1.9 vs 3.6 GB), but on a buggy fintech sample it answered `NO_ISSUES` to code containing a blatant SQL injection that the 3B caught deterministically. Accuracy is 50% of the score, judged qualitatively — losing the SQLi loses the entry. Revisit only if the license question (§4) forces it. |

### How the score is actually computed (from the official challenge page)

- `S_perf = 100 × (TPS_actual / TPS_max)` where **`TPS_max` is the fastest
  submission in the contest**, not a fixed 15-TPS bar. If tiny-model entries set
  a high `TPS_max`, every 3B entry's perf score gets compressed — this
  strengthens the 1.5B case beyond what a fixed reference would suggest.
- `S_eff = 100 × ((7 GB − peak RAM) / 7 GB)` — linear reward for headroom, so
  every GB saved is worth ~2.9 total points. Dropping 3B→1.5B saves ~1.1 GB
  ≈ 3 points of `S_eff` on top of the `S_perf` gain.
- Accuracy is judged on **our 2 `test_prompts` plus 2 hidden organizer prompts
  in the declared domain** (anti-overfitting). The judges run the raw GGUF via
  llama.cpp/Ollama — so `S_acc` rides on base-model quality and the published
  test prompts, not on the agent wrapper. The agent is the product story and
  African-use-case bonus; the model pick is the accuracy score.
- **Multipliers:** Budget Profile +10% (claimed — `budget_laptop_claim` in
  `metadata.json`), African Language Support **+15%** (not claimed; see §9).
- Disqualification: OOM or sandbox crash. Thermal: −10 if >85°C or throttling.

Concretely, `agent/agent.py` now runs:

```
llama-server -m model/getdebug-edge-3b-q4_k_m.gguf \
  --ctx-size 3072 --threads <physical-cores> --threads-batch <physical-cores> \
  --batch-size 512 --cache-type-k q8_0 --cache-type-v q8_0 \
  --n-gpu-layers 0 --host 127.0.0.1 --port 0
```

and every chunk becomes a `POST /v1/chat/completions` against that already-loaded
server (an ephemeral free port is chosen automatically; the agent never assumes a
fixed port). Flag names above may shift slightly across llama.cpp versions —
verify against whatever build ends up installed before benchmarking.

## 7b. African language strategy (offline vs Khaya AI)

The contest's African Language Support multiplier is +15% — the single largest
scoring lever — but the eval sandbox is **100% offline**, which splits the
strategy in two:

**Offline (contest-eligible):** the `--lang` flag asks the submitted model
itself to write finding explanations in a target language (severity tags and
code stay in English so reports remain parseable). How well this works is a
property of the model: Qwen2.5-Coder is code-first with weak African-language
coverage; Gemma-3-4B is trained on 140+ languages and is the credible route to
claiming the multiplier honestly (Swahili and Hausa have enough training data
to be plausible; Twi/Ewe/Ga likely remain weak in ANY small open model).
Whether Gemma's code-review accuracy holds up is exactly what the bake-off
(`BAKEOFF.md`) measures — the multiplier only pays if `S_acc` doesn't crater.

**Offline via a dedicated African-NLP model — researched and TESTED
2026-08-06, not viable yet.** The African-NLP ecosystem (Masakhane, Lelapa AI,
Soynade, MsingiAI, SERENGETI, AfriTeVa, Sunbird, AfroBench) is exactly the
right place to look for a local translation layer. Only **InkubaLM-0.4B**
(Lelapa AI) fits the stack — it ships as GGUF/LLaMA-arch, runs in llama.cpp,
is ~424 MB, offline, and covers isiZulu, Yoruba, Hausa, Swahili, isiXhosa. We
downloaded and tested it: as a **base** model (not instruction- or
translation-tuned) at only 0.4B, it produced degenerate word-salad on
finding-translation prompts (few-shot and direct) — unusable without
fine-tuning it for translation, which is its own research effort. The
higher-quality African MT lives in **Masakhane MT / NLLB-distilled** models,
but those are PyTorch/HF seq2seq — not GGUF/llama.cpp — so adopting one means a
second runtime and dependency, breaking the zero-dependency, single-llama.cpp,
8 GB design. Honest conclusion: **no clean offline African-language
finding-translation exists at small scale today.** Roadmap options, in order of
realism: (1) fine-tune a small MT model (InkubaLM or an NLLB-distill) to GGUF
for `--translate`, validated against **AfroBench**; (2) the Khaya online mode
below; (3) wait for stronger small multilingual models. License note:
InkubaLM is CC BY-NC 4.0 (blocks future commercial use).

**Online (post-contest product mode, NOT in the eval path):**
[Khaya AI](https://translation.ghananlp.org/) by GhanaNLP is the best
translation coverage for Ghanaian + several other African languages (Twi, Ewe,
Ga, Fante, Dagbani, Gurene, Yoruba, Kikuyu, Kimeru, Luo — plus ASR/TTS). It is
a cloud API with a subscription key, so it **must not** be wired into the
scored path — "zero external network dependencies during our testing window"
is a hard rule, and a network call during eval risks disqualification, not
just lost points. The right shape post-contest: an explicitly opt-in
`--translate khaya` flag (off by default, clearly documented as online) that
post-processes the findings report through the Khaya translation API for
languages the local model can't handle. This also matches the product thesis:
offline-first, online-enhanced.

## 8. Timeline against Gate 1 (Aug 25, 2026)

| Window | Work |
|---|---|
| Weeks 1–2 | Wire up llama.cpp + chunking + a working end-to-end smoke test |
| Weeks 3–4 | Prompt engineering, chunking strategy, first profiler run |
| Week 5 | Quantization tuning (3B vs 1.5B tradeoff), RAM/TPS optimization |
| Week 6 | African-use-case framing pass, `REPORT.md`, 2-minute demo video |
| Buffer | Resolve any profiler flags, finalize `metadata.json`, submit |

## 9. Open items for fafa

- Solo entry or team of up to 3? Affects how much of the roadmap is realistic before
  Aug 25.
- Which real (or realistic, sanitized) code samples to build the 2 required
  `test_prompts` around.
- Confirm the entry's venture identity/team_id registration is clean against the
  eligibility rules (<12 months old, pre-commercial, <$25K raised) — separate from
  getdebug/everweep's own age and stage.
- `african_alpha_claim` is the **African-Language** (+15%) claim, and is set
  `false` in `metadata.json` — the shipping 3B cannot produce usable indigenous
  African-language output (see BAKEOFF.md). The separate **African Use-Case**
  bonus (no metadata flag; judged from the writeup) is still pursued via
  `AFRICAN_USE_CASE.md`.
- **African Language Support multiplier (+15%)** — currently NOT claimed
  (`language_scope: ["en"]`). Bake-off data (see `BAKEOFF.md`) says the honest
  route exists but requires a model swap: Qwen2.5-Coder-3B's Swahili collapses
  into repetition loops, while **Llama-3.2-3B-Instruct** produced coherent,
  correct Swahili AND caught both seeded bugs at near-identical speed/RAM. The
  `--lang` flag already implements the feature. Decision needed: stay strategy
  A (English, Qwen) or switch to B (Llama + multiplier) — test Hausa/Yoruba/
  Amharic probes and a real-repo noise check first.
- **Model weights must be retrievable by judges at a pinned git commit** — the
  rules say judges fetch the `.gguf` via the repo at your submitted commit hash.
  Confirm whether the template expects Git LFS weights in-repo or the
  `download_model.sh` pattern (check `adtc-2026-submission-template`); if LFS is
  required, set it up before Gate 1.
- Deadline discrepancy: Devpost renders the deadline as **Aug 24, 2026 11:45 PM
  PDT** while other sources (and this doc's header) say Aug 25 — confirm on the
  portal and treat the earlier date as real until proven otherwise.
