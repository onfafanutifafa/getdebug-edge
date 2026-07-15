<!-- Paste this as the README on the Hugging Face model repo.
     The YAML block at the top is HF metadata — keep it as the very first lines. -->
---
license: other
license_name: qwen-research
license_link: https://huggingface.co/Qwen/Qwen2.5-Coder-3B-Instruct/blob/main/LICENSE
base_model: Qwen/Qwen2.5-Coder-3B-Instruct
tags:
  - code
  - code-review
  - security
  - static-analysis
  - offline
  - gguf
  - llama.cpp
library_name: llama.cpp
pipeline_tag: text-generation
---

# getdebug-edge-3B (Q4_K_M GGUF)

**Offline, security-first code review that runs entirely on a commodity CPU laptop.**

This is the model artifact for **getdebug-edge**, an entry in the Africa Deep
Tech Challenge 2026 (Laptop LLM Challenge). It is
[Qwen2.5-Coder-3B-Instruct](https://huggingface.co/Qwen/Qwen2.5-Coder-3B-Instruct),
quantized to 4-bit **Q4_K_M GGUF (~2.1 GB)**, with the getdebug-edge code-review
methodology **baked into the chat template's default system prompt** — so when
you run it bare (no external system message), it behaves as a security-focused
reviewer: it analyzes code, then reports findings in the format
`- [high|medium|low] summary (line ~N) — fix: ...`, checking for injection,
unvalidated input, edge cases, weak crypto, hardcoded secrets, access-control
gaps, secrets-in-logs, and logic errors.

Full project, agent, evaluation harness, and technical report:
**https://github.com/onfafanutifafa/getdebug-edge**

## Run it (fully offline)

**llama.cpp:**
```bash
llama-server -m getdebug-edge-3b-q4_k_m.gguf \
  --ctx-size 3072 --flash-attn on \
  --cache-type-k q8_0 --cache-type-v q8_0 \
  --n-gpu-layers 0 --threads $(nproc)   # use physical-core count for best speed+thermals
# then POST a prompt to /v1/chat/completions with just a user message —
# the baked chat template supplies the reviewer system prompt.
```

**Ollama:**
```bash
ollama create getdebug-edge -f Modelfile   # FROM ./getdebug-edge-3b-q4_k_m.gguf
ollama run getdebug-edge "Review this function for bugs: ..."
```

## Intended use

A **first-pass triage** that points a developer at the code worth a closer
look — not an authoritative gate. On an internal 22-bug benchmark it catches
~82% of seeded bugs (judged bare-model path); it has a real false-positive rate
on clean code and known blind spots in reasoning-heavy classes (access control,
business-logic validation). Confirm every finding before acting on it. See the
[technical report](https://github.com/onfafanutifafa/getdebug-edge/blob/main/REPORT.md)
for the honest accuracy characterization, including false-negative/positive rates.

## Hardware target

Built for the ADTC Standard Laptop: 8 GB RAM (7 GB budget), integrated
graphics, CPU-only, Ubuntu 22.04. Verified under a hard 8 GB ceiling: ~3.5 GB
peak RAM, no OOM, no crash.

## Base model, quantization, and reproducibility

- **Base:** Qwen2.5-Coder-3B-Instruct (Qwen team, Alibaba Cloud)
- **Quantization:** GGUF Q4_K_M (official Qwen GGUF weights)
- **Modification:** only the chat template's default system prompt is changed
  (the getdebug-edge reviewer methodology). Weights are unchanged. Reproduce
  exactly with `tools/bake_persona.py` in the GitHub repo.

## License & attribution

This is a derivative of Qwen2.5-Coder-3B-Instruct and inherits the **Qwen
Research License** (see `license_link` above) — please review its terms before
use. Base model © the Qwen team. Inference via
[llama.cpp](https://github.com/ggml-org/llama.cpp). The getdebug-edge agent,
detectors, and harness are original work, GPL-3.0 (in the GitHub repo).
