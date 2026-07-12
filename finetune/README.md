# Fine-tuning getdebug-edge (LoRA)

Why: the seeded-bug eval (`eval/`) shows the base 3B model hits a **capability
ceiling** on a few bug classes (weak crypto, subtle edge cases) that prompt
engineering can't fix — even when the skill file names the exact bug. A small
LoRA fine-tune is the only lever left that reaches the judges' *hidden* prompts,
because those hit the bare GGUF, not our agent wrapper.

The goal is modest and honest: teach the model our exact output contract and
sharpen recall on the classes it misses, **without** inflating false positives
(the eval measures both).

## The pipeline at a glance

```
seed.jsonl ──build_dataset.py──▶ train.jsonl ──train_lora.py──▶ merged GGUF
  (laptop)      (laptop)          (upload to GPU)   (GPU)         (download)
      │                                                              │
      └── expand first! (see below)          bake_persona ◀──────────┘
                                                   │
                                         re-run eval/run_eval.py
                                         compare to eval/baseline.json
                                         keep ONLY if recall↑ and FPs not↑
```

## Step 1 — expand the dataset (do this before spending GPU hours)

`data/seed.jsonl` has 15 hand-authored examples covering the eval-missed
classes plus clean negatives. **15 is enough to prove the pipeline, not enough
to move the score.** Aim for 300–1000+ before the real run.

Two honest ways to expand (do NOT self-distill — the 3B can't teach itself what
it doesn't know):

1. **Distill from a stronger model.** Take real buggy snippets (public CVEs,
   your own git history, deliberately-broken variants of clean code) and have a
   strong model (Claude, GPT-4-class) write the ideal review *in our exact
   format* — analysis sentences, then `- [severity] ... — fix: ...` lines, or
   NO_ISSUES. Save each as a `{lang, code, completion}` line in `seed.jsonl`.
2. **Curate real bug/fix pairs.** Mine fix commits ("fix: sql injection",
   "handle empty list") — the pre-fix file is the input, the commit message +
   diff informs the ideal completion.

Keep **~25-30% clean/NO_ISSUES** examples. This is the single most important
ratio: too few negatives and the model learns to always find something, which
tanks precision (we watched exactly this failure mode with an untamed model in
`BAKEOFF.md`).

Then rebuild:
```bash
python3 finetune/build_dataset.py     # seed.jsonl -> train.jsonl (exact inference format)
```

## Step 2 — train on the GPU (Udutech / Colab)

Upload `finetune/data/train.jsonl` and `finetune/train_lora.py` to the GPU box.

```bash
pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"
pip install --no-deps trl peft accelerate bitsandbytes
TRAIN_JSONL=train.jsonl python3 train_lora.py
```

- A 3B QLoRA fits on a single T4/L4; a few hundred examples × 3 epochs is well
  under one GPU hour — comfortably inside the contest's ~5-hour grant.
- Watch the loss: if it collapses toward zero fast, you're overfitting the
  small set — reduce epochs to 1–2 or add data.
- The script exports a **merged GGUF at q4_k_m** directly (Unsloth's
  `save_pretrained_gguf`), so no separate llama.cpp conversion is needed.

## Step 3 — finish on the laptop and PROVE it helped

```bash
# bake the reviewer persona into the fine-tuned GGUF's chat template
python3 tools/bake_persona.py getdebug-edge-3b-lora/*q4_k_m.gguf \
    model/getdebug-edge-3b-q4_k_m.gguf

# regression gate: recall must go UP and false positives must NOT
python3 eval/run_eval.py --model model/getdebug-edge-3b-q4_k_m.gguf \
    --out eval/after_finetune.json
```

Compare `eval/after_finetune.json` to `eval/baseline.json`. **Only ship the
fine-tune if recall improved and FPs on clean files did not rise.** A fine-tune
that trades a missed bug for a new false alarm is a net loss on a security
tool. Put the before/after table in `REPORT.md` — "we measured a ceiling,
trained against it, here's the delta" is exactly the systems-engineering story
this contest rewards.

## Guardrails (learned the hard way this session)

- **Format must match inference exactly** — `build_dataset.py` imports the real
  agent prompt builders so it can't drift. Don't hand-write the templates here.
- **Keep temperature/decoding identical** to production (temp 0, repeat penalty
  1.1) when you re-eval, or you're not measuring the same thing.
- **Re-verify TPS/RAM** after fine-tuning: a LoRA merge shouldn't change the
  quant footprint, but run `bench.sh` and the profiler once to be sure the
  S_perf/S_eff numbers still hold.
- **Licensing:** the fine-tuned weights inherit the base model's license — the
  same qwen-research question flagged in `SCOPE.md` §4 applies; re-verify
  before publishing the GGUF.
