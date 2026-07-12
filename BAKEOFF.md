# Model bake-off — measured 2026-07-11

Six candidate GGUFs (Q4_K_M each) run through the same harness on the same
machine: generation TPS via `llama-bench`, then the **full agent pipeline**
(persistent llama-server, chat template, SKILL.md loaded, linter hints, greedy
decoding) reviewing a seeded buggy fintech file, then a Swahili explanation
probe for the African-language-multiplier question. Raw data:
[`bakeoff_results.json`](./bakeoff_results.json).

Ground truth seeded in the sample: a SQL injection (string-concatenated
`UPDATE`), a division-by-zero (`sum(scores)/len(scores)` with no empty guard),
and mobile-money validation gaps.

Dev machine: i9-9980HK (8c/16t), 64 GB, macOS, llama.cpp b9960, 8 threads
(physical cores). Faster than the ADTC reference i5 — treat TPS as an upper
bound; relative ordering transfers.

## Results

| Model | Size | TPS gen | RSS (server) | Caught SQLi | Caught div-by-0 | Findings | Swahili |
|---|---|---|---|---|---|---|---|
| **Qwen2.5-Coder-3B** (current) | 2.10 GB | **9.59** | 3.6 GB | ✅ | ✅ | 7 | ❌ repetition loop |
| Qwen3-4B-Instruct-2507 | 2.50 GB | 7.63 | 4.6 GB | ✅ | ✅ | 3 (tightest writeup) | ❌ repetition loop (even at temp 0.4) |
| Gemma-3-4B-it | 2.49 GB | 7.15 | 4.4 GB | ✅ | ❌ | 4 | ⚠️ good at temp 0.4; mixed EN/SW framing |
| Llama-3.2-3B-Instruct | 2.02 GB | 9.11 | 3.7 GB | ✅ | ✅ | 9 (noisiest, some hedging) | ✅ **only fully coherent Swahili** |
| DeepSeek-Coder-1.3B-Instruct | 0.87 GB | **21.7** | 1.8 GB | ❌ | ❌ | 0 — waffled and refused to review | ❌ chat-template echo garbage |
| GLM-Edge-4B-Chat | 2.63 GB | 7.34 | 4.7 GB | ✅ | ❌ | 3 | ❌ repetition loop |

## Per-model verdicts

**Qwen2.5-Coder-3B (baseline — keep for the English/coding path).** Best
accuracy-per-TPS of the field: caught both seeded bugs, produced the most
correct findings (7), fastest of the accurate group. Weaknesses: zero usable
Swahili (kills the +15% multiplier path), and the restrictive `qwen-research`
license on this specific size (1.5B/7B siblings are Apache 2.0).

**Qwen3-4B-Instruct-2507.** The best *prose*: tight, precise, judge-friendly
findings ("high — SQL injection via string concatenation in record_payment").
Caught both bugs with zero noise. Costs 20% TPS and ~1 GB RSS vs baseline, and
its Swahili is a degeneration loop even at temp 0.4 — no multiplier path. A
legitimate alternative if judged answer *polish* turns out to matter more than
breadth; otherwise the baseline wins on value per token.

**Gemma-3-4B-it.** The expected African-language pick, and its Swahili at
temp 0.4 is genuinely good — but it **missed the division-by-zero** in the
code review, is the slowest of the accurate group, and mixes English framing
("Okay, let's review...") into non-English output. Second choice for the
language edge, behind Llama — worth re-testing on Hausa/Yoruba/Twi where its
140-language training might pull ahead.

**Llama-3.2-3B-Instruct — the surprise of the bake-off.** Only model with
fully coherent Swahili (correct diagnosis, correct fix, grammatical — at both
greedy and 0.4), caught both seeded bugs, nearly matches the baseline's speed
and RAM, and its community license sidesteps the qwen-research question. Cost:
the noisiest findings list (9, with hedgy phrasing like "if the code is not
properly sanitized") — prompt tightening could likely fix this. **If we claim
the +15% African Language multiplier, this is the model to build on.**

**DeepSeek-Coder-1.3B-Instruct.** Answers "can't DeepSeek do it?": not at this
size. Fastest and smallest by far (21.7 TPS / 1.8 GB) but it waffled
("I can provide suggestions... but I can't fix the issues") and produced zero
findings. It's a 2023-era model; DeepSeek's current strong models (V3, R1)
are far beyond the 7 GB RAM budget, and the R1-Qwen distills burn their TPS on
thinking tokens. No path here.

**GLM-Edge-4B-Chat.** Answers "can't GLM do it?": not competitively. Caught
the SQLi but missed the div-by-zero, slowest-but-one, biggest RSS of the
field (4.7 GB), Swahili degenerates. GLM's stronger models (GLM-4-9B+) don't
fit the RAM budget. No advantage over any of the above on any axis.

## Decision matrix

| Strategy | Model | Expected score effect |
|---|---|---|
| **A. English-only, maximize S_acc/S_perf** (current) | Qwen2.5-Coder-3B | Best raw accuracy+speed; resolve license before Gate 1 |
| **B. Claim +15% African Language multiplier** | Llama-3.2-3B-Instruct | ~5% worse raw TPS, slightly noisier findings, +15% multiplier if the language claim holds up in judging — likely net-positive IF the claim is defensible |
| C. Language breadth hedge | Gemma-3-4B-it | Only if B's Swahili/Hausa/etc. proves weaker than Gemma's in wider language tests; costs speed and the div-0 catch |

Recommended next test before committing to B: run Llama-3.2-3B vs Gemma-3-4B
on Hausa, Yoruba, and Amharic explanation probes (Swahili is the
best-resourced African language — the gap between models will widen on the
others), and a 20-file real-repo review to quantify Llama's noise rate.

## Decision suite (round 2, 2026-07-11): strategy A vs B resolved

**Language probes** (Hausa, Yoruba, Amharic, Twi at temp 0.4 — Swahili already
measured): neither Llama-3.2-3B nor Gemma-3-4B can honestly claim any of them.
Llama answered the Yoruba probe in English, degenerated on Amharic, produced
word-salad Twi. Gemma answered Hausa and Twi in English, drifted into
Indonesian mid-Yoruba, and answered the Amharic probe in Thai. **The only
honest African-language claim available at this model size is Swahili, via
Llama.**

**Real-repo noise test** (12 real files, 765 lines, ripple marketplace API —
sessions, Paystack payments, security plugins; same pipeline, skill + lint,
deterministic decoding):

| | Qwen2.5-Coder-3B | Llama-3.2-3B | Llama tamed* |
|---|---|---|---|
| Chunks flagged | 1/12 | 12/12 | 6/12 |
| Total findings | 12 | 84 (63 low) | 18 |
| Fabricated vulnerabilities | 0 | yes — "SQL injection" in no-SQL files, nonexistent APIs | **still yes** — same fabricated [high] injection in `audit.ts` |
| Failure mode | one repetition loop (fixed by `repeat_penalty 1.1`, now default) | over-flagging + hallucination | reduced volume, hallucination persists |

*tamed = precision-mandate skill: max 3 findings/chunk, must quote proving
code, "false alarm is worse than silence."

**Resolution: strategy A — Qwen2.5-Coder-3B stays.** The +15% multiplier is
worth ~10 points, but it would ride on a single language (Swahili) while
attaching a security reviewer that invents SQL injections on clean code —
a direct hit to the 50%-weighted, judge-scored accuracy component and to the
tool's core credibility. Llama's hallucination survived prompt-level
mitigation, so the risk is not tunable away. The `--lang` feature ships as a
product capability (documented honestly: quality varies by language), but the
African Language multiplier is **not claimed**.

## Thermal note from the marathon

Six back-to-back model loads + benches (~35 min sustained load) eventually
pushed even the 8-thread configuration to 95°C with throttling to 58% — heat
soak is real on long multi-model sessions (this i9 MacBook's cooling is
notoriously weak; the single-model contest eval never got past 72°C). For the
contest this doesn't change anything; for long real-repo reviews it validates
keeping `INTER_CHUNK_PAUSE_SECONDS` available as a lever.

## Methodology caveats

- One seeded sample file, one review pass per model — this measures "does it
  catch the obvious, must-catch bugs," not fine-grained accuracy ranking.
- Swahili probe is a single prompt; greedy decoding punishes weak languages
  with repetition loops (hence the temp-0.4 re-probe for the top-3).
- `findings_count` includes duplicates/noise — more is not better; the
  caught-columns are the signal.
- TPS measured on an i9; the contest i5 will be slower across the board but
  ordering should hold.
