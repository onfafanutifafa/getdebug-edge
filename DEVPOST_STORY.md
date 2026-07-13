<!-- Paste the body below into Devpost's "About the project" box. First-person
singular (solo submission). "Built with" tags and "Try it out" links are at the
bottom for the other two form fields. -->

## Inspiration

The seed was my own cloud product, [getdebug.dev](https://getdebug.dev) — AI code-security review. But every tool in that class (CodeRabbit, Snyk, cloud SAST) quietly assumes three things: fast internet, a company credit card, and permission to send your source code to a server abroad. For most developers on the continent, those are three walls.

A three-person fintech team in Accra moving school fees over mobile money often ships code that handles children's financial data with **no security review at all** — not because they don't care, but because the tools that would help are unreachable: priced in dollars against revenue in cedis, gated behind connectivity they don't always have, and blocked by data-residency rules for banking data. I wanted to find out: could a genuinely useful code reviewer run *entirely offline* on the $150–$500 laptop they already own?

## What it does

getdebug-edge is an **offline, security-first code reviewer**. You point it at a project folder and a 3-billion-parameter model running entirely on your CPU — **no internet, no account, no data ever leaving the machine** — reads your code and flags bugs, vulnerabilities, and correctness issues with suggested fixes.

- **Hybrid detection:** the LLM handles reasoning-heavy bugs; fast deterministic detectors catch the pattern-matchable classes (hardcoded secrets, weak crypto, secrets-in-logs) it would otherwise miss.
- **Meets you where you work:** findings drop into VS Code's Problems panel, clickable to the line; a one-shot mode answers ad-hoc questions.
- **Honest by design:** it's a *first-pass triage* that points a developer at the code worth a closer look — not an authoritative gate.

It works in a village, during a power cut, and inside compliance rules — because it needs nothing but the laptop on the desk.

## How I built it

Every decision was measured, not assumed:

- **Model:** I benchmarked **six** open models head-to-head (Qwen2.5-Coder-3B/1.5B, Qwen3-4B, Gemma-3-4B, Llama-3.2-3B, DeepSeek-Coder, GLM-Edge) on a real laptop. Qwen2.5-Coder-3B won on accuracy-per-resource.
- **Runtime:** llama.cpp with the model quantized to a ~2.1 GB 4-bit GGUF, loaded **once** into a persistent server, context capped at 3072 tokens, KV cache quantized with flash attention.
- **The threading discovery:** using **physical cores instead of logical threads** made it ~25% *faster* AND ~27°C *cooler* — generation is memory-bandwidth-bound, so hyperthreads add heat, not speed.
- **A hybrid pass:** cheap regex detectors for the classes a 3B model reliably misses — because you shouldn't ask a language model to do what a regex does better.
- **A measurement harness:** a seeded-bug eval (22 planted bugs + clean controls) that scored every change objectively, plus a persona baked into the model, prompt/KV and result caching, and deterministic decoding.
- **Verification:** I ran the whole thing in a container pinned to the contest spec — Ubuntu 22.04, 4 CPUs, **8 GB RAM with swap disabled** — reviewing a real Flask app.

## Challenges I ran into

- **Fine-tuning made it *worse* — twice.** Two LoRA runs on a free Colab T4 regressed recall: the first learned terseness, the second overfit to templated data and started answering "no issues" on buggy code. The eval harness caught it, and I made the hard call to **ship the base model, not the fine-tune.**
- **The thermal trap was counterintuitive** — the "obvious" setting (use all threads) was both slower and hot enough to trigger the contest's throttling penalty.
- **My own accuracy number was flattering me.** On 10 samples I saw 80% recall; expanding to 22 dropped it to a *truthful* 68%. Rather than hide that, I published it — then closed the gap to 82% with the hybrid detectors.
- **Small-model false positives are real** — on well-written code it over-flags (it called a correctly parameterized query "SQL injection"). I report the false-positive rate openly.

## Accomplishments that I'm proud of

- **Passes the disqualification test:** a full review runs at **3.5 GB peak RAM, no OOM, no crash** under a hard 8 GB ceiling on the actual evaluation OS.
- **The physical-core finding:** faster *and* cooler *and* lighter on the battery — an energy win that matters where the grid is the constraint.
- **Intellectual honesty as a feature:** I expanded my own benchmark until the number got worse, reported it, and *then* engineered it back up — recall **68% → 82% with zero added false positives.**
- **I refused to ship a regression** even after investing in the fine-tune path, because a security tool that invents or misses bugs is worse than one that's honest about its limits.
- **Truly offline, zero-dependency:** Python standard library only, one 2 GB model download, then nothing leaves the machine — ever.

## What I learned

- **Measure, don't assume.** "Fine-tuning helps" and "more threads = faster" were both wrong, and only the eval and the thermal probe revealed it.
- **Right tool for the right job.** A 3B model reasoning about intent + a regex catching `hashlib.md5` beats either alone.
- **Honesty is a competitive advantage.** In a field of overclaiming demos, a security tool that reports its own false-positive and false-negative rates reads as *more* trustworthy — and it's the correct product positioning.
- **The constraint is the design.** 8 GB of RAM and no GPU didn't limit the project; they defined every good decision in it.

## What's next for getdebug-edge

- **Close the reasoning-heavy gap** (access control / IDOR, business-logic validation) with lightweight taint analysis for authorization flows.
- **Real reference-hardware validation** on a refurbished Intel i5 for true throughput numbers.
- **Wider language reach** for finding explanations via offline translation models (and GhanaNLP/Khaya as an opt-in online mode) — honestly, not by overclaiming.
- **Broader detector coverage** and tree-sitter AST-aware chunking.
- Keep it **free and open-source**, so the developers who need it most never hit a paywall.

---
<!-- ===== "Built with" tags (up to 25) ===== -->
**Built with:** llama.cpp · ggml · gguf · qwen2.5-coder · python · quantization · lora · unsloth · docker · ubuntu · cpu-inference · sast · static-analysis · offline-ai · on-device-llm · vs-code · google-colab

<!-- ===== "Try it out" link ===== -->
**Try it out:** https://github.com/onfafanutifafa/getdebug-edge  (public at submission time)
