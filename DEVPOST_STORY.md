<!-- Paste the body below into Devpost's "About the project" box. First-person
singular (solo submission). "Built with" tags and "Try it out" links are at the
bottom for the other two form fields. -->

## Inspiration

The seed was my own cloud product, [getdebug.dev](https://getdebug.dev) — AI code-security review. But every tool in that class (CodeRabbit, Snyk, cloud SAST) quietly assumes three things: fast internet, a company credit card, and permission to send your source code to a server abroad. For most developers on the continent, those are three walls.

A three-person fintech team in Accra moving school fees over mobile money often ships code that handles children's financial data with **no security review at all** — not because they don't care, but because the tools that would help are unreachable: priced in dollars against revenue in cedis, gated behind connectivity they don't always have, and blocked by data-residency rules for banking data. I wanted to find out: could a genuinely useful code reviewer run *entirely offline* on the $150–$500 laptop they already own?

## What it does

getdebug-edge is an **offline, security-first code reviewer** — and, because its base is a code model, a fix-suggester and coding assistant too. You point it at a project folder and a 3-billion-parameter model running entirely on your CPU — **no internet, no account, no data ever leaving the machine** — reviews your code and flags bugs, vulnerabilities, and correctness issues with fixes.

- **A three-layer hybrid.** The LLM reasons about the code; fast deterministic detectors catch pattern-matchable classes it misses (hardcoded secrets, weak crypto, secrets-in-logs, JWTs with no expiry); and **spec-aware review** — you describe how the app *should* behave in a `SPEC.md` — surfaces business-logic bugs that neither a model nor a regex can find without knowing intent.
- **Multi-language.** The LLM reviews 12 languages across 16 file types (Python, JS/TS/JSX/TSX, Java, Go, Rust, C/C++, C#, Ruby, PHP, SQL); the deterministic detectors cover **Python, JavaScript, Java, and Go**, so those developers get the extra safety net, not just LLM review.
- **It suggests code, not just prose.** `--fix` emits corrected code for each finding; `--prompt` writes new code on request.
- **It meets you where you work.** Findings drop into VS Code's Problems panel; explanations can come in other languages.
- **It's tiny on purpose.** A 3-bit quantized model (~1.7 GB on disk, **1.84 GB peak RAM** measured by the official profiler) — small enough to run on a 4 GB machine, or on a modern phone.
- **Honest by design.** A first-pass triage that points a developer at the code worth a closer look — not an authoritative gate.

## How I built it

Every decision was measured, not assumed:

- **Model:** I benchmarked **six** open models head-to-head (Qwen2.5-Coder-3B/1.5B, Qwen3-4B, Gemma-3-4B, Llama-3.2-3B, DeepSeek-Coder, GLM-Edge). Qwen2.5-Coder-3B won on accuracy-per-resource.
- **Quantization:** a measured sweep across Q4/Q3/IQ quants chose **Q3_K_M** — smaller, faster, and lighter on RAM than Q4 at equal-or-better accuracy.
- **The model, focused.** I baked the review methodology (analyze-first, the vulnerability checklist, the output format) into the model's chat template — so the bare model behaves as a security reviewer with no external harness. That alone took bare-model recall from 68% to 82%.
- **The model, augmented.** Deterministic detectors (across Python, JS, Java, and Go) and spec-aware checking wrap the model to catch what it misses — lifting the full tool to 86%, plus business-logic bugs.
- **Engineering for the box:** persistent llama-server (model loaded once), physical-core threading, KV-cache quantization, prompt/result caching, deterministic decoding.
- **A measurement harness** (a seeded-bug eval) gated every single change, and I verified the whole thing on real Ubuntu under a hard 8 GB ceiling.

## Challenges I ran into

**First, the box I had to build inside.** The contest constraints are unforgiving, and every one of them shaped the design:

- **8 GB RAM, and out-of-memory means instant disqualification** — not lost points, a zero. Every choice (model size, context window, KV-cache quantization) was made against that ceiling.
- **CPU only, no GPU** — so throughput is bound by memory bandwidth, and every millisecond had to be earned in software.
- **Fully offline during evaluation** — no cloud fallback, no API, nothing. The whole review loop had to run on localhost.
- **A thermal penalty** — exceed 85 °C or throttle, and you lose 10 points. On the low-cost, poorly-cooled hardware this targets, that is a real risk.
- **Speed is scored *relative to the fastest submission*** — meaning a 3B model, chosen for accuracy, can never win the speed axis outright. I had to accept a structural ceiling on 30% of the score to protect the 50% that is accuracy.

**Then, the obstacles that fought back:**

- **Fine-tuning made the model *worse* — twice.** Two LoRA runs on a free Colab T4 both regressed accuracy: the first taught it to stop after one finding, the second overfit to my templated data and started answering "no issues" on obviously buggy code. My own eval harness caught it, and I made the hard call to ship the base model, not the fine-tune.
- **The obvious performance setting was a trap.** Using all CPU threads was *slower* than using fewer, and hot enough to trip the thermal penalty — the exact opposite of intuition. Physical-core threading turned out to be ~25% faster *and* ~27 °C cooler.
- **My own accuracy number flattered me.** A 10-sample test showed 80%; expanding it to a size that actually means something dropped it to a truthful 68%. I published the lower number.
- **The 3B has a hard reasoning ceiling.** When I tried to prompt it into catching business-logic bugs by adding reasoning cues, accuracy went *down*, not up (82% → 73%) — proof you can't prompt a small model into reasoning it can't do. (The fix came later, from a different angle: letting the developer supply the intent via a spec.)
- **The model over-flags clean code** — it called a correctly-parameterized query "SQL injection." False positives are real at this size, and I report the rate openly.
- **Not everything can live in the model.** The detectors are executable code and per-project specs are runtime data — neither can be baked into the weights. Only *instructions* bake in. That forced an honest split I document plainly: the bare model a judge scores (82%) and the full tool a developer runs (86%) are two different numbers.
- **The model kept finding ways to misbehave.** Given a terse prompt it took the "no issues" escape hatch and skipped a real SQL injection; at nonzero temperature it produced different output formats run-to-run that broke my findings parser; greedy decoding sent it into repetition loops.
- **Infrastructure bit back constantly.** A single stray apostrophe in the baked chat template broke the server at startup. A fixed network port silently collided with another app, so the agent "reviewed" code against a server that wasn't even running the model. A read-only test mount made the linter error out, and that error text got reported as a phantom bug. Free Colab sessions recycled mid-work and 2 GB downloads stalled near completion.
- **African-language support collapsed beyond Swahili.** Probing Hausa, Yoruba, Amharic, and Twi, the small models degenerated or answered in the wrong language — closing off a +15% language-bonus path I could not claim honestly.
- **Compression had a surprise.** The importance-matrix quants that *should* have been most efficient unexpectedly collapsed in accuracy; only a measured sweep revealed that the plain Q3_K_M was the real winner.

Every one of these was found by measuring, not guessing — and each is documented in the repo with the data behind it.

## Accomplishments that I'm proud of

- **Passes the disqualification test:** the official ADTC profiler measures **1.84 GB peak RAM** for the shipping model (S_eff = 74), `throttled=false`, no OOM, no crash, under a hard 8 GB ceiling on the actual evaluation OS.
- **The physical-core finding:** faster *and* cooler *and* lighter on the battery — an energy win that matters where the grid is the constraint.
- **Intellectual honesty as a feature.** I expanded my own benchmark until the number got worse, reported it, and *then* engineered it back up — and I keep two separate, clearly-labeled numbers (82% model, 86% tool) so no one can mistake transparency for spin.
- **I closed my own reasoning ceiling honestly.** After proving prompt tricks couldn't make a 3B reason about logic, spec-aware review did — the developer describes intent, and business-logic bugs the tool fundamentally missed became catchable.
- **I refused to ship a regression** even after investing in the fine-tune path, because a security tool that invents or misses bugs is worse than one honest about its limits.
- **Truly offline, zero-dependency, and tiny** — Python standard library only, one ~1.7 GB download, small enough for a 4 GB machine.

## What I learned

- **Measure, don't assume.** "Fine-tuning helps," "more threads = faster," and "importance-matrix quants are best" were all wrong, and only the eval and the profiler revealed it.
- **Right tool for the right job.** A 3B model reasoning about intent, a regex catching `hashlib.md5`, and a developer's spec describing business rules each do what the others can't.
- **Honesty is a competitive advantage.** A security tool that reports its own false-positive and false-negative rates — and refuses to claim a flattering "100%" — reads as *more* trustworthy, not less.
- **The constraint is the design.** 8 GB of RAM, no GPU, and no network didn't limit the project; they defined every good decision in it.

## What's next for getdebug-edge

- **Independent validation** against a larger, real ground-truth set (public SAST benchmarks, or my own CodeSecBench) to firm up the accuracy numbers.
- **Close the last reasoning gaps** (access control / IDOR) with lightweight authorization-flow analysis.
- **A mobile version** — the model already fits on a phone; the tooling around it is next.
- **Wider language reach** for finding explanations via offline translation. I researched and tested the African-NLP ecosystem (Masakhane, Lelapa AI, and others): **InkubaLM-0.4B** is the one that fits our stack (GGUF, runs in llama.cpp, covers Yoruba/Hausa/Swahili/isiZulu/isiXhosa), but as a base model it can't translate out of the box — so it's a **fine-tune candidate**: train it for finding-translation, ship it as GGUF, and validate on AfroBench. That's the honest path to real local-language support, built on African-made models.
- Keep it **free and open-source**, so the developers who need it most never hit a paywall.

---
<!-- ===== "Built with" tags (up to 25) ===== -->
**Built with:** llama.cpp · ggml · gguf · qwen2.5-coder · python · quantization · lora · unsloth · docker · ubuntu · cpu-inference · sast · static-analysis · offline-ai · on-device-llm · vs-code · google-colab

<!-- ===== "Try it out" link ===== -->
**Try it out:** https://github.com/onfafanutifafa/getdebug-edge  (public at submission time)
