#!/usr/bin/env python3
"""Seeded-bug evaluation harness.

Reviews eval/corpus/ with the real agent pipeline and scores the model
against eval/truth.json:

- recall: fraction of seeded bugs whose signature appears in the model's
  response for that file
- false positives: findings reported on the clean control files

Run before/after any prompt, skill, model, or quantization change — this is
the regression gate for S_acc-affecting edits.

Usage:
    python3 eval/run_eval.py [--model path.gguf] [--out eval/baseline.json]
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "agent"))
from agent import (  # noqa: E402
    LlamaServer, chars_per_chunk, chunk_file, physical_core_count, run_linters,
)
from prompts import build_review_prompt, build_system_prompt, extract_findings  # noqa: E402
from detectors import scan_text  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "eval" / "corpus"
TRUTH = json.loads((ROOT / "eval" / "truth.json").read_text())["files"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path,
                        default=ROOT / "model" / "qwen2.5-coder-3b-instruct-q4_k_m.gguf")
    parser.add_argument("--out", type=Path, default=ROOT / "eval" / "results.json")
    parser.add_argument("--ctx-size", type=int, default=3072)
    args = parser.parse_args()

    skill = (ROOT / "skills" / "SKILL.md").read_text()
    system = build_system_prompt(skill)
    server = LlamaServer(args.model, args.ctx_size, physical_core_count())
    server.start(120)

    results = {"model": args.model.name, "files": {}}
    caught = missed = fps = 0
    t0 = time.monotonic()
    try:
        for fname, spec in TRUTH.items():
            path = CORPUS / fname
            chunks = chunk_file(path, chars_per_chunk(args.ctx_size))
            lint = run_linters(path)
            response = "\n".join(
                server.complete(build_review_prompt(fname, c, i, len(chunks), lint), system=system)
                for i, c in enumerate(chunks)
            )
            # Hybrid: append deterministic-detector findings, exactly as the
            # agent does, so the eval measures the shipping configuration.
            det = scan_text(path.read_text(errors="ignore"))
            if det:
                response += "\n" + "\n".join(det)
            findings = extract_findings(response)
            entry = {"findings": len(findings), "caught": {}, "false_positives": 0}
            if spec["clean"]:
                entry["false_positives"] = len(findings)
                fps += len(findings)
            else:
                for bug, pattern in spec["bugs"].items():
                    hit = bool(re.search(pattern, response, re.IGNORECASE))
                    entry["caught"][bug] = hit
                    caught += hit
                    missed += not hit
            entry["response_excerpt"] = response[:400]
            results["files"][fname] = entry
            print(f"  {fname}: {entry['findings']} findings, "
                  f"caught={[k for k, v in entry['caught'].items() if v]}, "
                  f"fp={entry['false_positives']}", flush=True)
    finally:
        server.stop()

    total_bugs = caught + missed
    results["summary"] = {
        "recall": round(caught / total_bugs, 3) if total_bugs else None,
        "bugs_caught": caught,
        "bugs_total": total_bugs,
        "false_positives_on_clean": fps,
        "seconds": round(time.monotonic() - t0, 1),
    }
    args.out.write_text(json.dumps(results, indent=2))
    print(f"\nRecall {caught}/{total_bugs} = {results['summary']['recall']}, "
          f"FPs on clean files: {fps}, {results['summary']['seconds']}s -> {args.out}")


if __name__ == "__main__":
    main()
