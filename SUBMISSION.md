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
- [x] Qwen 3B license re-verify (qwen-research) — DONE 2026-08-09: confirmed
      **non-commercial (research/evaluation) only**; contest hosting is compliant
      with attribution ("Built with Qwen" + copyright notice, in HF card/README).
      Commercial downstream needs a Qwen license or an Apache-2.0 model swap.
      (The old strategy-B fallback — Llama community license — is moot; we ship Qwen Q4.)

## Repo & compliance

- [x] `git init`, first commit, push to GitHub public repo (DONE — repo is
      public at github.com/onfafanutifafa/getdebug-edge; profiler embeds a
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
- [x] `metadata.json`: `team_id` (`getdebug-edge`, registered on the portal) and
      `github_handle` set; test prompts are DONE (both verified to produce strong
      model answers — tp_001 rewritten 2026-07-11 after the original made the
      model produce a wrong fix)
- [x] `LICENSE` added (**GPL-3.0** for our code) + attribution section (llama.cpp;
      model under Qwen-Research non-commercial; **"Built with Qwen"** notice in
      README + HF card)
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
models, ship a 4-bit quantization, and found that using physical cores instead
of hyperthreads made it ~22% faster at generation and run cooler — an energy win where
the grid is the constraint. The contest's own profiler confirms the margin: just
2.2 gigabytes of RAM — leaving most of the budget free — no crash, no
throttling."

**[1:40–2:00 — honesty + impact]**
"I measured the tool honestly — on my own benchmark it catches around 86% of
seeded bugs, and I report its false-positive rate too, because a security tool
should. It's a first-pass safety net with no cloud bill and no data leaving the
machine. Free and open-source, built for the hardware Africa actually has."
<!-- NB: frame 86% as THE TOOL's review recall (product), not the contest's
automated accuracy score — those are different metrics. The automated profiler
score is acc_norm 0.82 on arc_easy (raw model, general reasoning); do NOT
conflate the two on screen. See REPORT. -->


Key on-screen proof to show: airplane-mode toggle, a real finding + fix,
VS Code Problems panel, the **`adtc-profiler` result — 2.21 GB peak / S_eff 68 /
no OOM, no throttle** (straight from `submission_q4.json`), and the 68%→86%
recall chart.

## Score projection (official formula; S_perf is relative to the fastest submission — unknowable pre-audit)

`S_total = 0.50·S_acc + 0.30·S_perf + 0.20·S_eff − P_thermal`. Shipping quant
is **Q4_K_M** (quant sweep in REPORT.md). **Measured by the canonical ADTC
profiler** (4 CPU / 8 GB / no-swap container): peak RSS **2.21 GB → S_eff =
100×(7−2.21)/7 = 68**; `throttled=false` → P_thermal = **0**; automated accuracy
**acc_norm = 0.82** on lm-eval `arc_easy`, reported in `submission.json`'s
top-level `accuracy[]` block (auto-populated by a full participant run).

**S_perf = 100×(TPSact ÷ TPSmax)** where `TPSmax` = the fastest submission's
tokens/sec and `TPSact` is measured *during the judges' audit* on the ADTC
Standard Laptop — the **official rule, verified 2026-08-09** on
[africadeeptech.org/challenge-2026](https://africadeeptech.org/challenge-2026/)
(it is **relative to the fastest team, NOT a fixed 15-TPS reference** — the
profiler README's `TPS_REFERENCE=15.0` is a local self-check simplification and
does not govern). So S_perf **cannot be computed until all submissions are in**;
the projections below assume a placeholder `TPSmax ≈ 15` purely for illustration.
For context, the Q3 alternative's generation is ~15% faster than shipping Q4 (11.1 vs 9.6 t/s, dev-machine llama-bench, 8 physical cores).

<!-- S_acc here = the AUTOMATED lm-eval benchmark score on the raw model (the
profiler's accuracy stage, no chat template, no agent). It is NOT our
code-review recall (68%/86%) — that measures the tool, not the contest metric.
NOW MEASURED on the canonical profiler: Q4 arc_easy acc_norm = 0.82 (41/50),
Q3 = 0.80 (40/50) — a 1-question gap, within noise; Q4 ships (it leads the bare
model the judged path scores). A qualitative judge read may adjust the final
S_acc; the automated stage is 82. -->

| Scenario (Q4 shipping) | S_acc | TPS → S_perf *(illustrative, TPSmax≈15 placeholder)* | S_eff | S_total |
|---|---|---|---|---|
| Dev-machine native (9.6 t/s, i9) | 82 (measured) | 9.6 → 64 | 68 | **~74** |
| Profiler / audit-like container (3.9 t/s, no-AVX) | 82 (measured) | 3.9 → 26 | 68 | **~62** |

*S_perf column is illustrative only:* the real `TPSmax` is the fastest submission's
speed and is unknown until judging. If a tiny-model entry sets a very high `TPSmax`,
every 3B entry's S_perf compresses — a structural ceiling on the 30% axis we accept
to protect the 50% accuracy axis.

Plus (per challenge page): Budget Profile multiplier +10% (claimed) and
African Use Case bonus up to +10 — central case lands ≈ **73–83** after
multiplier/bonus. S_acc's **automated half is measured (82)**; its **qualitative
judge-panel half** and S_perf's `TPSmax` are the only unknowns until judging —
S_eff and P_thermal are measured. Note: generation TPS is memory-bandwidth-bound and the reference
i5's DDR4 bandwidth is close to the dev machine's, so the reference-hardware
TPS drop may be smaller than the core-count difference suggests — verify on
real hardware.

**Lever analysis:** the **S_acc axis (50%) outweighs S_eff (20%)**, and the
judged accuracy path scores the *bare model* — so we ship **Q4_K_M**, which leads
the bare model (arc_easy 0.82 vs 0.80; model-only code-review recall 68% vs 59%)
even though it costs S_eff. On the canonical profiler that is **S_eff 68 (Q4) vs
74 (Q3)** — a ~1.2-point S_eff give-up that is roughly offset by Q4's ~+1
S_acc-half advantage, and the tie-break goes to the 50%-weighted, judge-scored
axis. **Q3_K_M stays the documented low-RAM alternative** (smaller download,
lower RAM, fewer false positives), selectable via `--model`. The
importance-matrix quants (IQ4_XS/IQ3_M) were tested and rejected (accuracy
collapsed, and their recall is unbacked by a committed eval). (Earlier: Q4_0 was
rejected for regressing tp_001.) Remaining S_acc levers: LoRA fine-tune on the
contest's free GPU hours (only lever that reaches the hidden prompts), default
system prompt baked into the GGUF chat template, seeded-bug eval corpus for
measurable prompt tuning.

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
      Submitted model = `model/getdebug-edge-3b-q4_k_m.gguf`
- [x] **Seeded-bug eval harness** — `eval/` (2026-07-12): 10 seeded bugs
      across 5 files + 2 clean controls; baseline recall 8/10 with 3 FPs;
      regression gate for all prompt/skill/model changes
- [x] Unit tests (44, stdlib unittest) + GitHub Actions CI on ubuntu-22.04
- [ ] **Demo GIF at the top of the README** — first thing judges see
- [ ] Architecture diagram (observe→think→act, one persistent server) in README
- [ ] `BAKEOFF.md` is already a differentiator — reference it prominently in
      `REPORT.md` §2 as the "design alternatives" evidence the rubric asks for
- [ ] Keep `submission.json` from the final profiler run in the repo
- [ ] Host/deliver the BAKED weights: judges must be able to obtain
      `getdebug-edge-3b-q4_k_m.gguf` — either reproduce-by-script (current,
      documented) or upload to a HF repo under the team account once
      registered (needed anyway if the LoRA fine-tune lands)
