"""Deterministic, LLM-free detectors for pattern-matchable vulnerability
classes the 3B model reliably misses (measured in eval/): hardcoded secrets,
weak cryptography, weak RNG, secrets-in-logs, and JWT-no-expiry. Syntax-aware
patterns cover Python, JavaScript, Java, and Go (JWT is Python/JS).

Design principle: don't ask a 3B model to do what a regex does better. These
run as a cheap hybrid pass alongside the model — high precision by construction
(a hit is a real, quotable pattern), catching the deterministic classes and
leaving reasoning-heavy bugs (IDOR, business logic) to the LLM.

Findings are emitted in the agent's standard contract so they merge with the
model's output and are picked up by the same parser:
    - [severity] summary (line ~N) — fix: ...
"""
from __future__ import annotations

import re

# --- High-signal secret tokens: always flag, regardless of variable name. ---
_TOKEN_PATTERNS = [
    (re.compile(r"sk_live_[A-Za-z0-9]{8,}"), "Stripe live secret key"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "AWS access key ID"),
    (re.compile(r"\bghp_[A-Za-z0-9]{20,}"), "GitHub token"),
    (re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"), "Slack token"),
    (re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"), "private key"),
]

# --- Secret assigned to a suggestively-named variable as a string literal. ---
_SECRET_ASSIGN = re.compile(
    r"([A-Za-z_][A-Za-z0-9_]*"
    r"(?:secret|passwd|pwd|api[_-]?key|access[_-]?token|auth[_-]?token|"
    r"client[_-]?secret|private[_-]?key|jwt[_-]?secret|password|apikey)"
    r"[A-Za-z0-9_]*)\s*(?::=|[:=])\s*(['\"])([^'\"]{6,})\2",   # =, :, and Go :=
    re.IGNORECASE,
)
_PLACEHOLDER = re.compile(r"^(changeme|placeholder|your[_-]?|xxx+|todo|example|test|dummy|<|\{)", re.IGNORECASE)

# --- Weak cryptography (Python, JS, Java, Go). ---
_WEAK_CRYPTO = [
    # Python
    (re.compile(r"hashlib\.(md5|sha1)\b", re.IGNORECASE),
     "high", "Weak hash ({m}) used", "use bcrypt/argon2/scrypt for passwords, SHA-256+ otherwise"),
    # JS
    (re.compile(r"createHash\(\s*['\"](md5|sha1)['\"]", re.IGNORECASE),
     "high", "Weak hash ({m}) used", "use a modern algorithm (SHA-256+, or bcrypt for passwords)"),
    # Java weak hash: MessageDigest.getInstance("MD5"|"SHA-1")
    (re.compile(r"MessageDigest\.getInstance\(\s*['\"](MD5|SHA-?1)['\"]", re.IGNORECASE),
     "high", "Weak hash ({m}) used", "use SHA-256+ (bcrypt/argon2 for passwords)"),
    # Go weak hash: md5.New() / sha1.Sum(...) (crypto/md5, crypto/sha1)
    (re.compile(r"\b(md5|sha1)\.(?:New|Sum)\b", re.IGNORECASE),
     "high", "Weak hash ({m}) used", "use SHA-256+ (bcrypt/argon2 for passwords)"),
    # Insecure cipher/mode: ECB anywhere; Java Cipher DES/ECB; Go des.NewCipher
    (re.compile(r"MODE_ECB|['\"]ecb['\"]", re.IGNORECASE),
     "high", "Insecure ECB cipher mode", "use an authenticated mode such as AES-GCM with a random nonce"),
    (re.compile(r"Cipher\.getInstance\(\s*['\"][^'\"]*(DES|ECB)", re.IGNORECASE),
     "high", "Insecure cipher/mode ({m})", "use AES-GCM with a random nonce"),
    (re.compile(r"\b(des)\.NewCipher\b", re.IGNORECASE),
     "high", "Insecure cipher ({m})", "use AES-GCM (crypto/aes + crypto/cipher) with a random nonce"),
]
# Non-cryptographic RNG in a security-sensitive line (Py, JS, Java, Go).
_WEAK_RANDOM = re.compile(
    r"Math\.random\s*\(|\brandom\.(?:randint|random|choice)\s*\(|"
    r"new\s+(?:java\.util\.)?Random\s*\(|"                          # Java
    r"\brand\.(?:Intn|Int31|Int63|Float64|Float32)\s*\(",           # Go math/rand
    re.IGNORECASE)
_SEC_CONTEXT = re.compile(r"token|secret|otp|password|passwd|pin|session|nonce|salt|api[_-]?key|auth", re.IGNORECASE)

# --- Sensitive data written to logs (Py, JS, Java, Go). ---
_LOG_CALL = re.compile(
    r"\b(logging\.\w+|logger\.\w+|log\.\w+|console\.(?:log|info|warn|error|debug)|"
    r"fmt\.Print\w*|System\.(?:out|err)\.print\w*|print)\s*\(", re.IGNORECASE)
_SENSITIVE = re.compile(r"\b(password|passwd|pwd|secret|api[_-]?key|access[_-]?token|private[_-]?key|\bpin\b)\b", re.IGNORECASE)

# --- JWT issued without an expiry claim (token never expires). ---
# Needs multi-line context (the exp may sit in a payload dict just above the
# call), so this is checked over the full text, not per line.
_JWT_SIGN = re.compile(r"\bjwt\.(?:encode|sign)\s*\(", re.IGNORECASE)
_JWT_HAS_EXP = re.compile(r"""['"]exp['"]|expiresIn|\bexpires?\b|\bexp\b\s*[:=]""", re.IGNORECASE)


def _fmt(severity: str, summary: str, line: int, fix: str) -> str:
    return f"- [{severity}] {summary} (line ~{line}) — fix: {fix}"


def scan_text(text: str) -> list[str]:
    """Return deterministic findings for one file's source, in agent format."""
    findings: list[str] = []
    seen: set[tuple[str, int]] = set()

    def add(kind: str, line: int, finding: str) -> None:
        key = (kind, line)
        if key not in seen:
            seen.add(key)
            findings.append(finding)

    for lineno, line in enumerate(text.splitlines(), 1):
        # High-signal token literals
        for pat, label in _TOKEN_PATTERNS:
            if pat.search(line):
                add("token", lineno, _fmt(
                    "high", f"Hardcoded secret in source ({label})", lineno,
                    "move to an environment variable or secrets manager and rotate the exposed value"))

        # Secret assigned to a secret-named variable
        for m in _SECRET_ASSIGN.finditer(line):
            var, literal = m.group(1), m.group(3)
            if _PLACEHOLDER.search(literal):
                continue
            add("secret", lineno, _fmt(
                "high", f"Hardcoded secret: `{var}` assigned a literal credential", lineno,
                "load from an environment variable or secrets store, never commit the value"))

        # Weak crypto
        for pat, sev, summary, fix in _WEAK_CRYPTO:
            m = pat.search(line)
            if m:
                algo = (m.group(1) if m.groups() else "").upper()
                add("crypto:" + summary, lineno, _fmt(sev, summary.format(m=algo or "weak"), lineno, fix))

        # Weak RNG in a security context
        if _WEAK_RANDOM.search(line) and _SEC_CONTEXT.search(line):
            add("rng", lineno, _fmt(
                "high", "Predictable value from a non-cryptographic RNG in a security context", lineno,
                "use secrets (Python) or crypto.randomBytes (Node) for tokens/secrets"))

        # Sensitive data in logs
        if _LOG_CALL.search(line) and _SENSITIVE.search(line):
            add("log", lineno, _fmt(
                "medium", "Sensitive data (password/secret/token) written to logs", lineno,
                "never log secrets; redact or omit the sensitive field"))

    # JWT issued with no expiry — check a window before and after each sign
    # call so an exp claim in an inline payload OR a payload dict defined just
    # above still counts (keeps precision high).
    for m in _JWT_SIGN.finditer(text):
        window = text[max(0, m.start() - 200):m.start() + 300]
        if not _JWT_HAS_EXP.search(window):
            lineno = text[:m.start()].count("\n") + 1
            add("jwt_exp", lineno, _fmt(
                "medium", "JWT issued without an expiry (exp) claim — the token never expires", lineno,
                "add an exp claim (e.g. now + a timedelta), or set expiresIn, so tokens expire"))

    return findings
