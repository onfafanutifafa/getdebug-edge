#!/usr/bin/env python3
"""Curated LoRA training examples, hand-authored for correctness.

Each entry is (lang, code, completion) where completion is the IDEAL review in
the agent's output contract: a 2-3 sentence analysis, then `- [severity] ...`
lines, or NO_ISSUES for clean code.

Design goals (why this set looks the way it does):
- Cover the classes the seeded-bug eval showed the base 3B missing: weak
  crypto, subtle edge cases, off-by-one, validation gaps.
- ~30% clean/NO_ISSUES so the model does NOT learn to always find something
  (the false-positive failure mode measured in BAKEOFF.md).
- African fintech/health/agri context where natural (momo, fees, clinics,
  crop prices) so the domain flavor matches the test prompts and use case.
- Vary phrasing and severity so the model learns the CONTRACT, not templates.

Run: python3 finetune/data/curated.py  ->  writes expanded.jsonl
"""
import json
from pathlib import Path

E: list[tuple[str, str, str]] = [
    # ---------- SQL injection ----------
    ("python",
     "def find_orders(db, customer):\n    q = f\"SELECT * FROM orders WHERE customer = '{customer}'\"\n    return db.execute(q).fetchall()",
     "This builds a SQL query by interpolating the caller-supplied `customer` into an f-string. A value like `x' OR '1'='1` changes the query's meaning and exposes every row.\n\n- [high] SQL injection via f-string query (line ~2) — fix: use a parameterized query, e.g. db.execute(\"SELECT * FROM orders WHERE customer = ?\", (customer,))"),
    ("javascript",
     "async function login(email, password) {\n  const rows = await db.query(\n    \"SELECT id FROM users WHERE email = '\" + email + \"' AND pass = '\" + password + \"'\");\n  return rows[0];\n}",
     "This authenticates by concatenating email and password directly into a SQL string. An email of `' OR 1=1 --` bypasses the check and logs in as the first user.\n\n- [high] SQL injection in the login query (line ~2) — fix: parameterize, e.g. db.query('SELECT id FROM users WHERE email = $1 AND pass = $2', [email, password])\n- [high] Passwords compared in plaintext (line ~3) — fix: store and compare a bcrypt/argon2 hash, never the raw password"),
    ("python",
     "def search(db, term):\n    return db.execute(\n        \"SELECT * FROM products WHERE name LIKE '%\" + term + \"%'\").fetchall()",
     "This concatenates the search term into a LIKE clause, so the input is executed as SQL. A crafted term can break out of the string literal.\n\n- [high] SQL injection in LIKE clause (line ~2) — fix: parameterize with a bound wildcard, e.g. db.execute(\"SELECT * FROM products WHERE name LIKE ?\", (f\"%{term}%\",))"),

    # ---------- Command injection ----------
    ("python",
     "import os\n\ndef convert(infile):\n    os.system(\"ffmpeg -i \" + infile + \" out.mp4\")",
     "This passes a caller-supplied filename straight into a shell command. A filename containing `;` or backticks executes arbitrary commands.\n\n- [high] Command injection via os.system (line ~4) — fix: use subprocess with an argument list, e.g. subprocess.run([\"ffmpeg\", \"-i\", infile, \"out.mp4\"], check=True)"),
    ("javascript",
     "const { exec } = require('child_process');\nfunction ping(host) {\n  exec('ping -c 1 ' + host, (e, out) => console.log(out));\n}",
     "This interpolates `host` into a shell string passed to exec. A host like `8.8.8.8; rm -rf /` runs the trailing command.\n\n- [high] Command injection via child_process.exec (line ~3) — fix: use execFile with an args array, e.g. execFile('ping', ['-c', '1', host], cb)"),

    # ---------- Path traversal ----------
    ("python",
     "from flask import send_file\n\ndef download(name):\n    return send_file('/srv/files/' + name)",
     "This serves a file from /srv/files using an unsanitized name. A name of `../../etc/passwd` escapes the directory and leaks arbitrary files.\n\n- [high] Path traversal in file download (line ~4) — fix: resolve and confirm the path stays under the root, e.g. reject if not os.path.realpath(path).startswith('/srv/files/')"),

    # ---------- Weak crypto / secrets / randomness ----------
    ("python",
     "import hashlib\n\ndef store_password(pw):\n    return hashlib.sha1(pw.encode()).hexdigest()",
     "This hashes a password with SHA-1: fast, unsalted, and collision-broken. Leaked hashes are cracked with commodity hardware.\n\n- [high] Weak unsalted password hash (SHA-1) (line ~4) — fix: use a slow salted KDF — bcrypt, argon2, or scrypt"),
    ("python",
     "import random\n\ndef reset_token():\n    return str(random.randint(100000, 999999))",
     "This generates a password-reset token with random.randint, which is a non-cryptographic PRNG — its output is predictable, so tokens can be guessed or reproduced.\n\n- [high] Predictable token from non-cryptographic RNG (line ~4) — fix: use the secrets module, e.g. secrets.token_urlsafe(32)"),
    ("javascript",
     "const DB_PASSWORD = 'Pr0dPassw0rd!2024';\nfunction connect() {\n  return pg.connect({ user: 'app', password: DB_PASSWORD });\n}",
     "This hardcodes the production database password in source. Anyone with repo access — now or after any leak — has the credential.\n\n- [high] Hardcoded database password in source (line ~1) — fix: read from an environment variable or secrets store, e.g. process.env.DB_PASSWORD, and rotate the exposed value"),
    ("python",
     "def make_session_id(user_id):\n    return str(user_id) + '-' + str(user_id * 7 + 3)",
     "This derives a session id deterministically from the user id, so any attacker who knows a user id can compute that user's session id and impersonate them.\n\n- [high] Guessable session id derived from user id (line ~2) — fix: use an unpredictable random token, e.g. secrets.token_urlsafe(32), stored server-side"),

    # ---------- Division by zero / empty collection ----------
    ("python",
     "def average_rainfall(readings):\n    return sum(readings) / len(readings)",
     "This averages sensor readings but divides by len without guarding the empty case, so an empty list raises ZeroDivisionError.\n\n- [medium] Division by zero on empty readings (line ~2) — fix: return 0 (or None) when not readings before dividing"),
    ("javascript",
     "function average(xs) {\n  return xs.reduce((a, b) => a + b, 0) / xs.length;\n}",
     "This computes a mean; if `xs` is empty, length is 0 and the result is NaN, which then silently corrupts any downstream math.\n\n- [medium] Empty-array input yields NaN (line ~2) — fix: guard with `if (xs.length === 0) return 0;`"),
    ("python",
     "def split_evenly(total, people):\n    return [total / len(people) for _ in people]",
     "This splits a bill across people but crashes with ZeroDivisionError when the people list is empty.\n\n- [medium] Division by zero when people is empty (line ~2) — fix: return [] or raise a clear error when not people"),

    # ---------- Off-by-one / indexing ----------
    ("python",
     "def last_three(items):\n    return items[len(items) - 3:len(items)]",
     "This intends to return the last three items. The slice works but is fragile and non-idiomatic; more importantly, for a list shorter than three it silently returns fewer without signaling — acceptable here, but the manual index arithmetic invites off-by-one edits.\n\n- [low] Fragile manual slice indexing (line ~2) — fix: use items[-3:], which is clearer and bounds-safe"),
    ("javascript",
     "function sumTo(arr, n) {\n  let s = 0;\n  for (let i = 0; i <= n; i++) s += arr[i];\n  return s;\n}",
     "This sums the first n elements but the loop condition `i <= n` reads one element past the intended range, adding arr[n] and risking an undefined read.\n\n- [medium] Off-by-one: loop includes index n (line ~3) — fix: use i < n"),

    # ---------- None / null / undefined ----------
    ("python",
     "def full_name(user):\n    return user['first'] + ' ' + user['last']",
     "This concatenates dictionary fields without checking they exist. A user missing 'first' or 'last' raises KeyError, and a None value raises TypeError.\n\n- [medium] Unchecked dict access can raise KeyError/TypeError (line ~2) — fix: use user.get('first', '') and validate presence before formatting"),
    ("javascript",
     "function greeting(profile) {\n  return 'Hello ' + profile.name.toUpperCase();\n}",
     "This calls toUpperCase on profile.name without checking either exists; a missing profile or name throws 'cannot read properties of undefined'.\n\n- [medium] Unchecked property access throws on missing name (line ~2) — fix: guard, e.g. profile?.name ? profile.name.toUpperCase() : 'there'"),

    # ---------- Missing input validation / money ----------
    ("python",
     "def transfer(accounts, src, dst, amount):\n    accounts[src] -= amount\n    accounts[dst] += amount",
     "This moves money between accounts with no check that the source has enough or that the amount is positive, so it can overdraw an account or, with a negative amount, move funds the wrong way.\n\n- [high] No sufficient-funds or positive-amount validation (line ~2) — fix: require amount > 0 and accounts[src] >= amount, else reject"),
    ("javascript",
     "app.post('/withdraw', (req, res) => {\n  const amount = req.body.amount;\n  wallet.balance -= amount;\n  res.json({ balance: wallet.balance });\n});",
     "This withdraws an amount taken directly from the request body with no validation and no auth on the wallet. A negative amount credits the account, a string breaks the arithmetic, and there is no ownership check.\n\n- [high] Unvalidated withdrawal amount from request body (line ~2) — fix: parse and require a positive number within balance\n- [medium] No check the caller owns this wallet (line ~3) — fix: authorize the request against the session user"),
    ("python",
     "def price_with_tax(price):\n    return price + price * 0.125",
     "This adds 12.5% VAT to a price using floating-point multiplication. For money, binary floats accumulate rounding error (e.g. 0.1 + 0.2), so totals can be off by a cent.\n\n- [low] Floating-point arithmetic on money (line ~2) — fix: use Decimal (or integer minor units) for currency, e.g. Decimal(price) * Decimal('1.125')"),

    # ---------- Auth / access control (IDOR) ----------
    ("javascript",
     "app.get('/invoice/:id', (req, res) => {\n  const inv = db.getInvoice(req.params.id);\n  res.json(inv);\n});",
     "This returns any invoice by id with no check that it belongs to the requesting user, so changing the id in the URL reads other customers' invoices.\n\n- [high] Insecure direct object reference: no ownership check (line ~2) — fix: verify the invoice's owner matches the authenticated user before returning it"),

    # ---------- Resource leaks ----------
    ("python",
     "def read_config(path):\n    f = open(path)\n    data = f.read()\n    return data",
     "This opens a file but never closes it; on many rows or under errors the process leaks file descriptors until it hits the OS limit.\n\n- [medium] File handle never closed (line ~2) — fix: use a context manager, e.g. with open(path) as f: return f.read()"),

    # ---------- Insecure deserialization / eval ----------
    ("python",
     "import pickle\n\ndef load_state(blob):\n    return pickle.loads(blob)",
     "This unpickles bytes from an untrusted source. pickle.loads executes arbitrary code embedded in the payload, giving remote code execution.\n\n- [high] Insecure deserialization via pickle.loads (line ~4) — fix: use a safe format such as json.loads for untrusted data"),
    ("javascript",
     "function calc(expr) {\n  return eval(expr);\n}",
     "This evaluates a caller-supplied string as JavaScript. Any input runs with the program's privileges — a direct code-execution hole.\n\n- [high] Arbitrary code execution via eval (line ~2) — fix: parse the expression with a safe math parser, never eval untrusted input"),

    # ---------- SSRF / open redirect ----------
    ("python",
     "import requests\n\ndef fetch(url):\n    return requests.get(url).text",
     "This fetches a caller-supplied URL server-side with no allowlist, enabling SSRF: an attacker can target internal services (e.g. http://169.254.169.254/ metadata) from your server.\n\n- [high] Server-side request forgery: unrestricted URL fetch (line ~4) — fix: validate the URL against an allowlist of hosts/schemes and block internal ranges"),

    # ---------- Logic errors ----------
    ("python",
     "def is_adult(age):\n    if age > 18:\n        return True\n    return False",
     "This treats exactly 18 as not an adult because it uses a strict greater-than, an off-by-one on the boundary.\n\n- [medium] Boundary error: age 18 excluded (line ~2) — fix: use age >= 18"),
    ("javascript",
     "function applyFee(amount, status) {\n  if (status = 'premium') return amount;\n  return amount * 1.02;\n}",
     "This uses a single `=` in the condition, which assigns 'premium' to status and always evaluates truthy, so every caller skips the fee.\n\n- [high] Assignment instead of comparison in condition (line ~2) — fix: use === , i.e. if (status === 'premium')"),

    # ---------- Clean / NO_ISSUES (negatives — keep ~30%) ----------
    ("python",
     "def celsius_to_fahrenheit(c):\n    return c * 9 / 5 + 32",
     "This converts Celsius to Fahrenheit with the standard formula. It operates on a plain numeric input with no external data, edge case, or resource to mishandle.\n\nNO_ISSUES"),
    ("python",
     "import bcrypt\n\ndef hash_password(pw: str) -> bytes:\n    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt())",
     "This hashes a password with bcrypt and a per-call salt, which is the correct approach for password storage. No issues.\n\nNO_ISSUES"),
    ("javascript",
     "function clamp(x, lo, hi) {\n  return Math.max(lo, Math.min(x, hi));\n}",
     "This clamps a number to the [lo, hi] range using Math.min/Math.max. The logic is correct for all numeric inputs and there is nothing to exploit.\n\nNO_ISSUES"),
    ("python",
     "def parse_amount(raw: str):\n    try:\n        value = float(raw)\n    except (TypeError, ValueError):\n        return None\n    return value if value >= 0 else None",
     "This parses a string to a non-negative float, handling both bad types and negatives explicitly and returning None on invalid input. Input is validated and errors are handled.\n\nNO_ISSUES"),
    ("javascript",
     "function toGhs(minorUnits) {\n  if (!Number.isInteger(minorUnits) || minorUnits < 0) {\n    throw new RangeError('minorUnits must be a non-negative integer');\n  }\n  return minorUnits / 100;\n}",
     "This converts integer minor units (pesewas) to GHS, validating the input is a non-negative integer before dividing. Using integer minor units avoids float money errors and the input is checked.\n\nNO_ISSUES"),
    ("python",
     "def get(d, key, default=None):\n    return d[key] if key in d else default",
     "This safely reads a dictionary key with a fallback, checking membership before access so it never raises KeyError. Correct and defensive.\n\nNO_ISSUES"),
    ("python",
     "import secrets\n\ndef otp() -> str:\n    return f\"{secrets.randbelow(1000000):06d}\"",
     "This generates a 6-digit OTP using secrets.randbelow, the cryptographically-secure source, zero-padded to six digits. The randomness source is correct for a security token.\n\nNO_ISSUES"),
    ("javascript",
     "function paginate(items, page, size) {\n  const start = Math.max(0, (page - 1) * size);\n  return items.slice(start, start + size);\n}",
     "This paginates an array; slice is bounds-safe so out-of-range pages simply return an empty array, and start is floored at 0. No correctness or security issue.\n\nNO_ISSUES"),
    ("python",
     "def clinic_wait_minutes(arrival, seen):\n    if seen < arrival:\n        raise ValueError('seen before arrival')\n    return int((seen - arrival).total_seconds() // 60)",
     "This computes wait time between two datetimes, explicitly rejecting the impossible case where the patient was seen before arriving. Inputs are validated and the arithmetic is sound.\n\nNO_ISSUES"),
]


def main() -> None:
    out = Path(__file__).parent / "expanded.jsonl"
    with out.open("w") as f:
        for lang, code, completion in E:
            f.write(json.dumps({"lang": lang, "code": code, "completion": completion}) + "\n")
    findings = sum(1 for _, _, c in E if "NO_ISSUES" not in c)
    clean = len(E) - findings
    print(f"wrote {len(E)} curated examples ({findings} findings, {clean} clean) -> {out}")


if __name__ == "__main__":
    main()
