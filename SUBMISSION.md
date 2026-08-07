# Submission plan — ADTC 2026 (deadline: verify Aug 24 vs 25, 2026, 11:45 PM PDT)

Working checklist for Gate 1. The contest requires: an open-source GitHub repo
conforming to the official `adtc-2026-submission-template`, a project report
(problem, constraints, design alternatives, tool justification, benchmarks),
screenshots/clips of the model running, a ≤2-minute explanation video, valid
`metadata.json` with 2 test prompts, and `.gguf` weights retrievable at the
submitted commit hash.

## Gate 0 — decisions to lock BEFORE recording anything

- [x] **Model strategy A vs B**: RESOLVED 2026-07-11 → **A (Qwen2.5-Coder-3B)**,
      per the round-2 decision suite in `BAKEOFF.md`: the only honest language
      claim was Swahili-via-Llama, and Llama fabricates high-severity
      vulnerabilities on real code even under a precision-mandated prompt —
      an unacceptable accuracy/credibility risk against a 50%-weighted,
      judge-scored component. `--lang` stays as an honest product feature;
      the +15% multiplier is not claimed. (Fafa preferred B for the language
      edge — revisit only if a better small multilingual coder model ships
      before Gate 1.)
- [x] **Eligibility check**: RESOLVED 2026-07-11 — Masenu Cybernetics is not
      incorporated, so the 12-month venture-age rule has nothing to attach to.
      Enter as an **individual/team** ("organized team" age = this project,
      started July 2026); no external funding raised. Keep the README lineage
      framing as-is (original open-source project sharing a thesis with a
      pre-incorporation product idea).
- [ ] Qwen 3B license re-verify (qwen-research) — if it blocks, strategy B
      also solves this (Llama community license).

## Repo & compliance

- [ ] `git init`, first commit, push to GitHub public repo (profiler embeds a
      commit SHA; judges fetch weights at a pinned hash)
- [x] Diff our layout against `Africa-Deep-Tech-Foundation/adtc-2026-submission-template`
      — DONE 2026-07-11: template files are README.md, REPORT.md, metadata.json,
      download_model.sh, model/.gitkeep, .gitignore, LICENSE. Ours matched except
      LICENSE (added: GPL-3, same as template). REPORT.md restructured to the
      template's exact section set (header block + Problem / Design Decisions /
      Constraints / Benchmarks incl. their benchmark table format), with
      Screenshots / Known Limitations / Attribution appended. metadata.json
      already field-identical to the template schema.
- [ ] Weights delivery: check whether the template expects Git LFS in-repo or
      a `download_model.sh` pattern — set up LFS if required
- [ ] `metadata.json`: fill `team_id` (register on the portal) and
      `github_handle`; test prompts are DONE (both verified to produce strong
      model answers — tp_001 rewritten 2026-07-11 after the original made the
      model produce a wrong fix)
- [ ] Add `LICENSE` (Apache-2.0 for our code) + attribution section (llama.cpp,
      model license; "Built with Llama" notice if strategy B)
- [ ] **Final `adtc-profiler` run must include the accuracy stage** (NOT
      `--skip-accuracy`) — accuracy is 50% of the score and runs lm-eval on the
      raw model. Earlier runs used `--skip-accuracy`; the submitted
      `submission.json` must be a full run. Ideally on the reference i5, which
      also confirms the Q3-vs-Q4 accuracy delta. Needs the accuracy stack
      installed (`pip install lm-eval llama-cpp-python`).

## Benchmarks on believable hardware

- [ ] Re-measure on Ubuntu 22.04 + 4-core/8 GB — either a real refurb i5
      (~$150–250, also useful for the video's credibility) or a UTM/QEMU VM on
      this Mac capped to 4 cores + 8 GB with Ubuntu 22.04
- [ ] Update `REPORT.md` §4 with reference-hardware numbers next to the i9
      numbers (keep both; the delta itself shows engineering honesty)
- [ ] Long-run thermal test on the reference hardware (30-min repo review,
      `sensors` logging) — we only have i9 MacBook thermal data

## Screenshots / short clips (shot list)

1. Terminal: `agent.py --target <repo>` full run — startup, progress, summary line
2. `findings.json` open, showing a real SQL-injection finding with fix
3. VS Code Problems panel populated via the `--diagnostics` task (clickable finding)
4. One-shot `--prompt` answering tp_001 (the fee-report bug) correctly
5. `--lang Swahili` run (strategy B only)
6. `adtc-profiler` output: TPS, peak RSS, `throttled: false`
7. `bench.sh` table: model comparison
8. htop/sensors during a review: 8 threads busy, temperature under limit

## 2-minute video script (≈260 words, storyboard) — v3, real profiler numbers

**[0:00–0:18 — problem, talking head or a $200 laptop on the desk]**
"Cloud AI code reviewers are excellent — if you have fast internet, a company
card, and permission to send your code abroad. Most African developers have
none of those. getdebug-edge is security-first code review that runs entirely
on the laptops we actually have: free, offline, private."

**[0:18–1:05 — live demo, screen capture]**
"This is a budget laptop with no internet." *(toggle airplane mode on screen)*
"I point it at a fintech project…" *(run agent; findings stream in)* "…and a
3-billion-parameter model running locally flags the SQL injection in this
payment webhook, and a deterministic pass catches a hardcoded secret the model
alone would miss. In VS Code, findings land in the Problems panel, clickable to
the line."

**[1:05–1:40 — engineering, cutaways to charts]**
"Everything is tuned to an 8-gigabyte, CPU-only budget. I benchmarked six open
models, ship a 3-bit quantization, and found that using physical cores instead
of hyperthreads made it 25% faster AND 27 degrees cooler — an energy win where
the grid is the constraint. The contest's own profiler confirms the margin: just
1.8 gigabytes of RAM — leaving most of the budget free — no crash, no
throttling."

**[1:40–2:00 — honesty + impact]**
"I measured the tool honestly — on my own benchmark it catches around 86% of
seeded bugs, and I report its false-positive rate too, because a security tool
should. It's a first-pass safety net with no cloud bill and no data leaving the
machine. Free and open-source, built for the hardware Africa actually has."
<!-- NB: frame 86% as THE TOOL's review recall (product), not the contest's
automated accuracy score — those are different metrics. The automated profiler
score is acc_norm 0.80 on arc_easy (raw model, general reasoning); do NOT
conflate the two on screen. See REPORT. -->


Key on-screen proof to show: airplane-mode toggle, a real finding + fix,
VS Code Problems panel, the **`adtc-profiler` result — 1.84 GB peak / S_eff 74 /
no OOM, no throttle** (straight from `submission_q3.json`), and the 68%→82%
recall chart.

## Score projection (official formula, TPS_REFERENCE = 15.0 provisional)

`S_total = 0.50·S_acc + 0.30·S_perf + 0.20·S_eff − P_thermal`. Shipping quant
is **Q3_K_M** (quant sweep in REPORT.md). **Measured by the canonical ADTC
profiler** (4 CPU / 8 GB / no-swap container): peak RSS **1.84 GB → S_eff =
100×(7−1.84)/7 = 74**; `throttled=false` → P_thermal = **0**; automated accuracy
**acc_norm = 0.80** on lm-eval `arc_easy`. S_perf = 100×(TPS/TPS_fastest), and
Q3's generation is ~35% faster than Q4 (14.6 vs 10.8 t/s on the dev machine).

<!-- S_acc here = the AUTOMATED lm-eval benchmark score on the raw model (the
profiler's accuracy stage, no chat template, no agent). It is NOT our
code-review recall (82%/86%) — that measures the tool, not the contest metric.
NOW MEASURED on the canonical profiler: Q3 arc_easy acc_norm = 0.80 (40/50),
Q4 = 0.82 (41/50) — a 1-question gap, within noise; Q3 ships. A qualitative
judge read may adjust the final S_acc; the automated stage is 80. -->

| Scenario | S_acc | TPS → S_perf | S_eff | S_total |
|---|---|---|---|---|
| Dev-machine optimistic | 80 (measured) | 14.6 → 97 | 74 | **~84** |
| Central | 80 (measured) | 11 → 73 | 74 | **~77** |
| Reference-hw conservative | 80 (measured) | ~9 → 60 | 74 | **~73** |

Plus (per challenge page): Budget Profile multiplier +10% (claimed) and
African Use Case bonus up to +10 — central case lands ≈ **73–83** after
multiplier/bonus. S_acc estimates are guesses until judged; everything else is
measured. Note: generation TPS is memory-bandwidth-bound and the reference
i5's DDR4 bandwidth is close to the dev machine's, so the reference-hardware
TPS drop may be smaller than the core-count difference suggests — verify on
real hardware.

**Lever analysis:** S_eff was capped by model size — and a smaller quant moved
it, exactly as predicted. **Q3_K_M switch (2026-07-16)** delivered equal-or-
better accuracy at 18% smaller / 35% faster / less RAM. On the canonical
profiler this is **S_eff 68 (Q4) → 74 (Q3)**, worth ~+1.2 total points, on top
of Q3's smaller download; the importance-matrix quants (IQ4_XS/IQ3_M) were tested
and rejected (accuracy collapsed). (Earlier: Q4_0 was rejected for regressing
tp_001; Q4_K_M was superseded by Q3_K_M.) Remaining S_acc levers: LoRA fine-tune on the contest's free GPU hours (only lever that
reaches the hidden prompts), default system prompt baked into the GGUF chat
template, seeded-bug eval corpus for measurable prompt tuning.

## Strengtheners (highest impact first)

- [ ] **Real-repo case study**: run the agent over a real open-source African
      project (or a sanitized real codebase), include finding counts + 2–3
      anonymized real findings in `REPORT.md` — evidence beats claims
- [x] **African Use Case writeup** — `AFRICAN_USE_CASE.md` (2026-07-12):
      Accra fintech persona, three walls (cost/connectivity/residency),
      power-as-binding-constraint engineering story, honest language claims
- [x] **Persona baked into the GGUF chat template** (2026-07-12) — judges
      running the bare model in Ollama/llama-cli get the security-reviewer
      behavior; reproducible from public weights via `tools/bake_persona.py`
      (wired into `download_model.sh`); verified live on bare prompts.
      Submitted model = `model/getdebug-edge-3b-q3_k_m.gguf`
- [x] **Seeded-bug eval harness** — `eval/` (2026-07-12): 10 seeded bugs
      across 5 files + 2 clean controls; baseline recall 8/10 with 3 FPs;
      regression gate for all prompt/skill/model changes
- [x] Unit tests (14, stdlib unittest) + GitHub Actions CI on ubuntu-22.04
- [ ] **Demo GIF at the top of the README** — first thing judges see
- [ ] Architecture diagram (observe→think→act, one persistent server) in README
- [ ] `BAKEOFF.md` is already a differentiator — reference it prominently in
      `REPORT.md` §2 as the "design alternatives" evidence the rubric asks for
- [ ] Keep `submission.json` from the final profiler run in the repo
- [ ] Host/deliver the BAKED weights: judges must be able to obtain
      `getdebug-edge-3b-q3_k_m.gguf` — either reproduce-by-script (current,
      documented) or upload to a HF repo under the team account once
      registered (needed anyway if the LoRA fine-tune lands)
