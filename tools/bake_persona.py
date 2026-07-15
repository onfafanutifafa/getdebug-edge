#!/usr/bin/env python3
"""Bake the getdebug-edge reviewer persona into the GGUF chat template.

Replaces the base model's default fallback system prompt ("You are Qwen…")
with the getdebug-edge security-reviewer persona. This only changes behavior
when the model is run WITHOUT an explicit system message (e.g. bare Ollama /
llama-cli usage, as in contest judging) — the agent always sends its own
system prompt and is unaffected.

The persona string must contain no single quotes: it is spliced into a
Jinja '<single-quoted>' literal inside the template (an apostrophe broke the
template lexer in testing, killing llama-server at startup).

Requires: pip install gguf

Usage:
    python3 tools/bake_persona.py model/qwen2.5-coder-3b-instruct-q4_k_m.gguf \
        model/getdebug-edge-3b-q4_k_m.gguf
"""
import subprocess
import sys
from pathlib import Path

try:
    from gguf import GGUFReader
except ImportError:
    sys.exit("pip install gguf   (needed once, only for baking)")

DEFAULT_PERSONA_MARKER = "You are Qwen, created by Alibaba Cloud. You are a helpful assistant."
PERSONA = (
    "You are getdebug-edge, an expert security-focused code reviewer running fully "
    "offline on a developer laptop. For any code you are shown, first briefly note "
    "what it does and what could go wrong (2-3 sentences), then list concrete "
    "findings, one per line, in exactly this format: "
    "- [high|medium|low] <summary> (line ~N) then a dash and fix: <short fix>. "
    "Check specifically for: injection (SQL, command, or path) built from untrusted "
    "input; unvalidated input; unhandled edge cases such as empty collections, zero, "
    "or None; weak cryptography, meaning MD5 or SHA-1 for passwords, hardcoded secrets "
    "or API keys in source, and predictable non-cryptographic random tokens; missing "
    "access-control or ownership checks; sensitive data such as passwords written to "
    "logs; and logic errors. Report only real issues you can point to in the code; do "
    "not invent problems, and do not flag safe, idiomatic code such as correctly "
    "parameterized queries. If the code is genuinely correct, say so plainly. When "
    "asked to write code, write clean, validated, idiomatic code following DRY principles."
)
assert "'" not in PERSONA, "persona must not contain single quotes (Jinja literal)"


def main() -> None:
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    reader = GGUFReader(str(src))
    field = reader.get_field("tokenizer.chat_template")
    template = bytes(field.parts[field.data[0]]).decode()
    if DEFAULT_PERSONA_MARKER not in template:
        sys.exit("default persona marker not found — base model/template changed; update this script")
    new_template = template.replace(DEFAULT_PERSONA_MARKER, PERSONA)
    del reader  # release memmap before gguf-new-metadata reads the file
    subprocess.run(
        ["gguf-new-metadata", "--chat-template", new_template, str(src), str(dst)],
        check=True,
    )
    print(f"baked: {dst}")


if __name__ == "__main__":
    main()
