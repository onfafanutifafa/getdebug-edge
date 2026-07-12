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
- [ ] Re-run `adtc-profiler` on the final commit; commit `submission.json`

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

## 2-minute video script (≈250 words, storyboard)

**[0:00–0:20 — problem, talking head or slide]**
"Cloud AI code reviewers are excellent — if you have fast internet, a company
card, and permission to send your code abroad. Most African developers have
none of those. getdebug-edge is CodeRabbit-class code review that runs entirely
on the laptops we actually have: free, offline, private."

**[0:20–1:15 — live demo, screen capture]**
"This is a $400-class laptop with no internet connection." *(airplane-mode
toggle on screen)* "I point the agent at a fintech project…" *(run agent;
findings appear)* "…and a 3-billion-parameter model running locally finds the
SQL injection in this payment webhook and shows the parameterized-query fix.
In VS Code, findings land in the Problems panel, clickable to the line."
*(optional, strategy B: "And it can explain the finding in Swahili.")*

**[1:15–1:45 — engineering, cutaways to charts]**
"Everything is tuned to the contest's 8-gigabyte, CPU-only budget: we
benchmarked six open models head-to-head, quantized to 4 bits, capped the
context window, and discovered that using physical cores instead of
hyperthreads made it 25% faster AND 27 degrees cooler. Peak memory: 3.6 of the
7-gigabyte budget. Zero throttling."

**[1:45–2:00 — impact]**
"Fintech and health-tech teams get a pre-ship safety net with no cloud bill and
no data leaving the machine. Free and open-source — built for Africa's real
hardware."

## Score projection (official formula, TPS_REFERENCE = 15.0 provisional)

`S_total = 0.50·S_acc + 0.30·S_perf + 0.20·S_eff − P_thermal`, with measured
values: peak RAM 3.59 GB → S_eff = 100×(7−3.59)/7 = **48.7**; P_thermal = **0**
(no throttle at physical-core threading); S_perf = 100×(TPS/15).

| Scenario | S_acc (est.) | TPS → S_perf | S_eff | S_total |
|---|---|---|---|---|
| Dev-machine optimistic | 85 | 12.8 → 85.3 | 48.7 | **77.6** |
| Central | 75 | 9.6 → 64.0 | 48.7 | **66.4** |
| Reference-hw conservative | 70 | ~8 → 53.3 | 48.7 | **60.7** |

Plus (per challenge page): Budget Profile multiplier +10% (claimed) and
African Use Case bonus up to +10 — central case lands ≈ **73–83** after
multiplier/bonus. S_acc estimates are guesses until judged; everything else is
measured. Note: generation TPS is memory-bandwidth-bound and the reference
i5's DDR4 bandwidth is close to the dev machine's, so the reference-hardware
TPS drop may be smaller than the core-count difference suggests — verify on
real hardware.

**Lever analysis:** S_eff is capped by model size (weights are 2.1 GB of the
3.59 GB peak) — only a smaller model moves it much, and the 1.5B fails
accuracy. **Q4_0 tested 2026-07-12 and REJECTED**: +10% generation TPS
(10.54 vs 9.56 t/s, runtime AVX2 repacking) and 90 MB smaller, but it
regressed on tp_001 — explained the `==` bug backwards and missed the
division-by-zero entirely, the prompt's headline bug. ~+2 total points were
not worth degrading a directly-judged S_acc item; Q4_K_M stays. Remaining
S_acc levers: LoRA fine-tune on the contest's free GPU hours (only lever that
reaches the hidden prompts), default system prompt baked into the GGUF chat
template, seeded-bug eval corpus for measurable prompt tuning.

## Strengtheners (highest impact first)

- [ ] **Real-repo case study**: run the agent over a real open-source African
      project (or a sanitized real codebase), include finding counts + 2–3
      anonymized real findings in `REPORT.md` — evidence beats claims
- [ ] **African Use Case writeup** backing `african_alpha_claim` (competes for
      the $1,500 prize + up to 10 bonus points): one page, concrete persona
      (Accra fintech SME, MoMo integrations, data-residency rules), grounded
      in the test prompts' scenarios
- [ ] **Demo GIF at the top of the README** — first thing judges see
- [ ] Unit tests for `extract_findings`/chunking + a tiny GitHub Action
      (py_compile + tests) — visible engineering rigor
- [ ] Architecture diagram (observe→think→act, one persistent server) in README
- [ ] `BAKEOFF.md` is already a differentiator — reference it prominently in
      `REPORT.md` §2 as the "design alternatives" evidence the rubric asks for
- [ ] Keep `submission.json` from the final profiler run in the repo
