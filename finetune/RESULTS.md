# Fine-tuning results — measured, not assumed

We built the seeded-bug eval harness (`eval/`) specifically so the
fine-tuning decision would be evidence-based. Three configurations, same 10
seeded bugs + 2 clean controls, identical pipeline (persona-baked GGUF,
deterministic decoding, skill + linter context):

| Configuration | Recall | FPs (clean) | Wall-clock | Verdict |
|---|---|---|---|---|
| **Base model** (Qwen2.5-Coder-3B + persona + skill + linter) | **8/10** | 3 | 291 s | **shipped** |
| LoRA fine-tune, 50 hand-authored examples | 5/10 | 2 | 92 s | rejected |
| LoRA fine-tune, 100 examples (43 multi-bug) | 1/10 | 1 | 58 s | rejected |

## Why both fine-tunes regressed

- **50-example run — terseness.** The seed set was almost all single-bug
  snippets, so the model learned to emit ~1 finding and stop (3× faster =
  3× less output). It lost recall on multi-bug files (command injection,
  path traversal, off-by-one) it previously caught.
- **100-example run — overfitting to templates.** The generated multi-bug
  files were too structurally uniform. The model memorized "code shaped like
  *these patterns* → findings" and defaulted to **NO_ISSUES** on the eval's
  differently-written code — on one file it even misread a hardcoded secret
  as coming "from an environment variable." More synthetic data made the
  overfitting worse, not better.

## The decision

Qwen2.5-Coder-3B is already a strong code-review model. Small LoRA fine-tunes
on narrow data can only narrow it; beating the base would require thousands of
genuinely diverse, real (non-templated) examples with no guarantee of a win —
out of scope for the contest timeline. **We ship the well-prompted base model.**

The real, verified gains came from engineering the *system around* the model,
not retraining it:
- **Accuracy**: analyze-first prompting, the SKILL.md review methodology,
  local-linter context injection, deterministic decoding (temp 0 + repeat
  penalty), and the persona baked into the chat template.
- **Speed/energy**: physical-core threading (~25% faster AND ~27°C cooler),
  KV-prefix reuse, and a persistent result cache (unchanged files skip
  inference entirely).

The fine-tune pipeline (`finetune/`) is retained and reproducible — a future
research effort with a large, diverse, distilled corpus could revisit it, and
the eval harness is the gate that would judge it.
