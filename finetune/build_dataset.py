#!/usr/bin/env python3
"""Assemble the LoRA training set in the EXACT format the agent uses at
inference time.

This is the single most important correctness property of the whole
fine-tune: the training prompt must be byte-identical in shape to what
`agent.py` sends, or the model learns a format it never actually sees in
production. So we import the real `build_system_prompt` / `build_review_prompt`
from the agent rather than re-typing the templates here.

Input:  finetune/data/seed.jsonl   (one {lang, code, completion} per line)
Output: finetune/data/train.jsonl  (one {messages:[system,user,assistant]} per line)

Each row becomes a 3-message ChatML conversation. The assistant turn is the
ideal review in the agent's output contract (2-3 sentence analysis, then
`- [severity] ...` lines, or NO_ISSUES).

Usage:
    python3 finetune/build_dataset.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "agent"))
from prompts import build_review_prompt, build_system_prompt  # noqa: E402

SEED = ROOT / "finetune" / "data" / "seed.jsonl"
OUT = ROOT / "finetune" / "data" / "train.jsonl"
SKILL = (ROOT / "skills" / "SKILL.md").read_text()


def main() -> None:
    system = build_system_prompt(SKILL)
    rows = []
    for lineno, line in enumerate(SEED.read_text().splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        code, completion = rec["code"], rec["completion"].strip()
        # Single-file review: chunk 1/1, no linter section (kept simple and
        # deterministic; the linter hint is optional context at inference).
        user = build_review_prompt(f"snippet.{rec.get('lang', 'py')}", code, 0, 1)
        rows.append({"messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
            {"role": "assistant", "content": completion},
        ]})

    # Sanity checks that catch the two classic fine-tune footguns.
    findings = sum(1 for r in rows if "NO_ISSUES" not in r["messages"][-1]["content"])
    clean = len(rows) - findings
    assert clean >= max(3, len(rows) // 5), (
        f"only {clean} clean/NO_ISSUES examples — too few negatives; the model "
        "will learn to always report a finding (false-positive bias)")

    OUT.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    print(f"wrote {len(rows)} examples ({findings} with findings, {clean} clean) -> {OUT}")
    print("NOTE: this seed set is a STARTING POINT. For a real accuracy lift, "
          "expand to 300-1000+ examples — see finetune/README.md for how to "
          "distill more from a stronger model without self-distilling the 3B.")


if __name__ == "__main__":
    main()
