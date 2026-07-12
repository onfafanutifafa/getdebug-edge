#!/usr/bin/env python3
"""Compose a training batch weighted toward MULTI-BUG files.

Why this exists: the 50-example run regressed recall 8->5 because the seed set
was almost all single-bug snippets, so the model learned to stop after one
finding (the terseness we measured — 3x faster because it said 3x less). This
generator fixes that by assembling files that contain 2-4 independent bugs, so
the ideal completion lists several findings — teaching the model to KEEP
scanning.

Correct-by-construction: each finding line is authored alongside its exact
code pattern in PATTERNS below, so a composed file's completion is just its
patterns' findings concatenated in order. Clean files (CLEAN) carry NO_ISSUES.

Deterministic: fixed random seed, so the batch is reproducible.

Usage:
    python3 finetune/data/generate.py --out batch1.jsonl --n 100 --seed 1
"""
import argparse
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "agent"))
from prompts import extract_findings  # noqa: E402

# Domain nouns for naming variety (African fintech/health/agri flavor).
ENTITIES = ["momo", "fee", "loan", "wallet", "invoice", "patient", "crop",
            "farmer", "student", "payout", "deposit", "claim", "order", "vendor"]

# Each bug pattern: given an entity, returns (import_lines, code_lines, findings).
# code is a self-contained function; findings are the ideal review lines.
PATTERNS = [
    ("python", lambda e: (
        ["import sqlite3"],
        [f"def get_{e}(db, {e}_id):",
         f"    q = \"SELECT * FROM {e}s WHERE id = '\" + {e}_id + \"'\"",
         "    return db.execute(q).fetchone()"],
        [f"- [high] SQL injection via string-concatenated query in get_{e} (line ~N) — fix: use a parameterized query with a ? placeholder and pass {e}_id as a bound parameter"])),
    ("python", lambda e: (
        ["import os"],
        [f"def backup_{e}(name):",
         f"    os.system(\"pg_dump \" + name + \" > /backups/\" + name + \".sql\")"],
        [f"- [high] Command injection via os.system with unsanitized name in backup_{e} (line ~N) — fix: use subprocess.run with an argument list and shell=False"])),
    ("python", lambda e: (
        [],
        [f"def average_{e}(values):",
         "    return sum(values) / len(values)"],
        [f"- [medium] Division by zero on empty input in average_{e} (line ~N) — fix: return 0 when the list is empty before dividing"])),
    ("python", lambda e: (
        ["import hashlib"],
        [f"def hash_{e}_pin(pin):",
         "    return hashlib.md5(pin.encode()).hexdigest()"],
        [f"- [high] Weak unsalted password hash (MD5) in hash_{e}_pin (line ~N) — fix: use a slow salted KDF such as bcrypt, argon2, or scrypt"])),
    ("python", lambda e: (
        [],
        [f"def apply_{e}_discount(balance, percent):",
         "    if percent > 100:",
         "        percent = 100",
         "    return balance - balance * percent / 100"],
        [f"- [medium] Missing lower-bound check on percent in apply_{e}_discount lets a negative value increase the balance (line ~N) — fix: clamp with max(0, min(percent, 100))"])),
    ("python", lambda e: (
        [],
        [f"def transfer_{e}(accounts, src, dst, amount):",
         "    accounts[src] -= amount",
         "    accounts[dst] += amount"],
        [f"- [high] No sufficient-funds or positive-amount check in transfer_{e} (line ~N) — fix: require amount > 0 and accounts[src] >= amount before moving funds"])),
    ("python", lambda e: (
        ["import pickle"],
        [f"def load_{e}(blob):",
         "    return pickle.loads(blob)"],
        [f"- [high] Insecure deserialization via pickle.loads in load_{e} (line ~N) — fix: use json for untrusted data; pickle executes arbitrary code"])),
    ("python", lambda e: (
        [],
        [f"def read_{e}_file(name):",
         f"    return open('/var/{e}/' + name).read()"],
        [f"- [high] Path traversal via unsanitized name in read_{e}_file (line ~N) — fix: resolve the path and reject anything outside the intended directory",
         f"- [low] File handle never closed in read_{e}_file (line ~N) — fix: use a with-statement context manager"])),
    ("python", lambda e: (
        ["import random"],
        [f"def {e}_token():",
         "    return str(random.randint(100000, 999999))"],
        [f"- [high] Predictable token from non-cryptographic RNG in {e}_token (line ~N) — fix: use secrets.token_urlsafe or secrets.randbelow"])),
    ("javascript", lambda e: (
        [],
        [f"function sum{e.capitalize()}(arr, n) {{",
         "  let s = 0;",
         "  for (let i = 0; i <= n; i++) s += arr[i];",
         "  return s;",
         "}"],
        [f"- [medium] Off-by-one: loop condition i <= n reads one element past the range in sum{e.capitalize()} (line ~N) — fix: use i < n"])),
    ("javascript", lambda e: (
        [],
        [f"function get{e.capitalize()}(req, res) {{",
         f"  const row = db.query(\"SELECT * FROM {e}s WHERE id = '\" + req.query.id + \"'\");",
         "  res.json(row);",
         "}"],
        [f"- [high] SQL injection from req.query.id in get{e.capitalize()} (line ~N) — fix: use a parameterized query",
         f"- [high] No ownership/authorization check on the {e} lookup (line ~N) — fix: verify the record belongs to the authenticated user"])),
    ("javascript", lambda e: (
        [],
        [f"function eval{e.capitalize()}(expr) {{",
         "  return eval(expr);",
         "}"],
        [f"- [high] Arbitrary code execution via eval in eval{e.capitalize()} (line ~N) — fix: parse with a safe expression parser, never eval untrusted input"])),
    ("javascript", lambda e: (
        [],
        [f"function set{e.capitalize()}Fee(amount, status) {{",
         "  if (status = 'premium') return amount;",
         "  return amount * 1.02;",
         "}"],
        [f"- [high] Assignment instead of comparison in condition in set{e.capitalize()}Fee (line ~N) — fix: use === for the status comparison"])),
    ("javascript", lambda e: (
        [],
        [f"function withdraw{e.capitalize()}(req) {{",
         "  const amount = req.body.amount;",
         "  wallet.balance -= amount;",
         "  return wallet.balance;",
         "}"],
        [f"- [high] Unvalidated withdrawal amount from request body in withdraw{e.capitalize()} (line ~N) — fix: parse and require a positive number within the balance"])),
]

CLEAN = [
    ("python", lambda e: (
        [], [f"def {e}_celsius_to_f(c):", "    return c * 9 / 5 + 32"],
        f"This converts Celsius to Fahrenheit with the standard formula on a plain numeric input — no external data, edge case, or resource to mishandle.")),
    ("python", lambda e: (
        ["import bcrypt"],
        [f"def hash_{e}(pw: str) -> bytes:",
         "    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt())"],
        f"This hashes a value with bcrypt and a per-call salt, the correct approach for secret storage.")),
    ("python", lambda e: (
        [], [f"def clamp_{e}(x, lo, hi):", "    return max(lo, min(x, hi))"],
        f"This clamps a number into [lo, hi] using min/max; correct for all numeric inputs with nothing to exploit.")),
    ("python", lambda e: (
        [],
        [f"def parse_{e}(raw: str):",
         "    try:",
         "        v = float(raw)",
         "    except (TypeError, ValueError):",
         "        return None",
         "    return v if v >= 0 else None"],
        f"This parses a string to a non-negative float, handling bad types and negatives explicitly and returning None on invalid input.")),
    ("javascript", lambda e: (
        [],
        [f"function paginate{e.capitalize()}(items, page, size) {{",
         "  const start = Math.max(0, (page - 1) * size);",
         "  return items.slice(start, start + size);",
         "}"],
        f"This paginates an array; slice is bounds-safe so out-of-range pages return an empty array, and start is floored at 0.")),
    ("javascript", lambda e: (
        [],
        [f"function to{e.capitalize()}Major(minor) {{",
         "  if (!Number.isInteger(minor) || minor < 0) {",
         "    throw new RangeError('minor must be a non-negative integer');",
         "  }",
         "  return minor / 100;",
         "}"],
        f"This converts integer minor units to major, validating the input is a non-negative integer first; using integer minor units also avoids float money error.")),
]

ANALYSIS_OPENERS = [
    "This module defines a few {dom} helpers. Reviewing each for bugs, security issues, and edge cases:",
    "These {dom} functions handle real user input. Checking each one:",
    "This file groups several {dom} operations. Going function by function:",
]


def compose_buggy(rng: random.Random, k: int) -> dict:
    """Assemble a file from k bug patterns of the SAME language.

    Substitutes each pattern's `line ~N` placeholder with the ACTUAL line the
    pattern's function starts on in the composed file, so the model learns to
    emit real line numbers, not the literal letter N."""
    lang = rng.choice(["python", "javascript"])
    pool = [p for p in PATTERNS if p[0] == lang]
    chosen = rng.sample(pool, min(k, len(pool)))
    entity = rng.choice(ENTITIES)
    imports, blocks = [], []  # blocks: (code_lines, findings)
    for _lang, fn in chosen:
        imp, code, finds = fn(entity)
        for line in imp:
            if line not in imports:
                imports.append(line)
        blocks.append((code, finds))

    header = imports + ([""] if imports else [])
    body, findings, cursor = [], [], len(header)
    for i, (code, finds) in enumerate(blocks):
        if body:
            body.append("")
            cursor += 1
        def_line = cursor + 1  # 1-indexed line of this block's first (def) line
        body.extend(code)
        cursor += len(code)
        findings.extend(f.replace("line ~N", f"line ~{def_line}") for f in finds)
    code_text = "\n".join(header + body)
    dom = entity
    opener = rng.choice(ANALYSIS_OPENERS).format(dom=dom)
    completion = opener + "\n\n" + "\n".join(findings)
    return {"lang": lang, "code": code_text, "completion": completion}


def compose_clean(rng: random.Random) -> dict:
    lang = rng.choice(["python", "javascript"])
    pool = [p for p in CLEAN if p[0] == lang]
    _lang, fn = rng.choice(pool)
    entity = rng.choice(ENTITIES)
    imp, code, analysis = fn(entity)
    code_text = "\n".join(imp + ([""] if imp else []) + code)
    return {"lang": lang, "code": code_text, "completion": analysis + "\n\nNO_ISSUES"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="batch1.jsonl")
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--clean-frac", type=float, default=0.30)
    args = ap.parse_args()
    rng = random.Random(args.seed)

    n_clean = round(args.n * args.clean_frac)
    n_bug = args.n - n_clean
    rows, seen = [], set()
    guard = 0
    while len([r for r in rows if "NO_ISSUES" not in r["completion"]]) < n_bug and guard < 5000:
        guard += 1
        # Heavy on multi-bug: 60% have 2-3 bugs, 40% single.
        k = rng.choices([1, 2, 3], weights=[40, 35, 25])[0]
        row = compose_buggy(rng, k)
        if row["code"] in seen:
            continue
        seen.add(row["code"])
        rows.append(row)
    while len([r for r in rows if "NO_ISSUES" in r["completion"]]) < n_clean and guard < 10000:
        guard += 1
        row = compose_clean(rng)
        if row["code"] in seen:
            continue
        seen.add(row["code"])
        rows.append(row)

    rng.shuffle(rows)
    # Validate every completion parses the way the agent will read it.
    bad = 0
    for r in rows:
        found = extract_findings(r["completion"])
        if "NO_ISSUES" in r["completion"]:
            bad += 1 if found else 0
        else:
            bad += 1 if not found else 0
    assert bad == 0, f"{bad} malformed completions"

    out = Path(__file__).parent / args.out
    out.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    multi = sum(1 for r in rows if len(extract_findings(r["completion"])) >= 2)
    clean = sum(1 for r in rows if "NO_ISSUES" in r["completion"])
    print(f"wrote {len(rows)} -> {out}  ({clean} clean, {multi} multi-bug files, 0 malformed)")


if __name__ == "__main__":
    main()
