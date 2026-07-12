#!/usr/bin/env python3
"""getdebug-edge — local offline code-review agent.

Observe -> think -> act loop over a target codebase, using a local GGUF model
served by a single persistent `llama-server` process (llama.cpp). No network
calls beyond localhost. Stdlib only.

Hardware-optimization decisions (see SCOPE.md §7 for the full rationale):

- The model is loaded ONCE into a background llama-server and reused for every
  chunk, instead of re-invoking llama-cli per chunk. Reloading a 2GB+ model
  from disk per call was the original scaffold's biggest flaw — it multiplies
  disk I/O, kills throughput, and creates repeated load spikes that push
  toward the thermal-throttle penalty.
- Context size is explicitly capped (default 3072 tokens) rather than left at
  the model's native max (Qwen2.5-Coder supports up to 32k) — KV-cache memory
  scales directly with context size, and this is an 8GB-RAM budget.
- KV cache is quantized to q8_0 (roughly half the memory of the f16 default)
  — a direct RAM lever with minimal quality cost. Quantizing the V cache
  requires flash attention in llama.cpp, so `--flash-attn on` is passed too.
- Prompts go through the OpenAI-compatible /v1/chat/completions endpoint so
  llama-server applies the model's own chat template (ChatML for Qwen) from
  the GGUF metadata. Sending raw concatenated text to /completion bypasses
  the template and measurably degrades instruct-model output quality —
  accuracy is 50% of the contest score, so this matters more than any
  runtime flag.
- Threads default to the PHYSICAL core count, not logical CPUs. Measured on
  an 8-core/16-thread i9: 15 threads = 14.7 TPS with a 98.7°C peak and
  thermal throttling to 56% CPU speed; 8 threads = 18.2 TPS at 68.8°C with
  no throttling. Generation is memory-bandwidth-bound — SMT threads add
  contention and heat, not speed. This is simultaneously the biggest S_perf
  and P_thermal lever measured so far.
- Chunking is token-budgeted (char-estimate based), not line-count based, so
  chunk size actually tracks what fits the context window instead of varying
  wildly with how dense a file's lines are.
- `--n-gpu-layers 0` is explicit: the reference hardware has integrated
  graphics only and the eval framework runs llama.cpp's CPU backend via
  llama-bench, so this scaffold targets CPU-only rather than risking iGPU
  backend compatibility issues in the eval sandbox.

STATUS: architecture is sound but UNTESTED end-to-end — no llama.cpp
available in the environment this was written in. Verify server startup
flags against whatever llama.cpp build/version you install; some flag names
(e.g. --cache-type-k/v) have shifted across versions.

Usage:
    # Review a whole repo
    python3 agent/agent.py --target /path/to/repo --out findings.json

    # One-shot question (demo mode / contest test_prompts)
    python3 agent/agent.py --prompt "Review this function: ..."
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

import shutil

from prompts import SYSTEM_PROMPT, build_review_prompt, build_system_prompt, extract_findings

DEFAULT_SKILL_PATH = Path(__file__).resolve().parent.parent / "skills" / "SKILL.md"

_MODEL_DIR = Path(__file__).resolve().parent.parent / "model"
_BAKED = _MODEL_DIR / "getdebug-edge-3b-q4_k_m.gguf"          # persona-baked (see tools/bake_persona.py)
_BASE = _MODEL_DIR / "qwen2.5-coder-3b-instruct-q4_k_m.gguf"  # upstream weights
DEFAULT_MODEL_PATH = _BAKED if _BAKED.exists() else _BASE


def physical_core_count() -> int:
    """Physical cores, not logical CPUs. llama.cpp generation is memory-
    bandwidth-bound, so running one thread per SMT sibling is slower AND
    hotter than one per physical core (measured: see module docstring)."""
    try:
        if sys.platform == "darwin":
            out = subprocess.run(
                ["sysctl", "-n", "hw.physicalcpu"], capture_output=True, text=True, check=True,
            )
            return max(int(out.stdout.strip()), 1)
        if sys.platform.startswith("linux"):
            # Count unique (physical id, core id) pairs from /proc/cpuinfo.
            cores: set[tuple[str, str]] = set()
            phys, core = "", ""
            for line in Path("/proc/cpuinfo").read_text().splitlines():
                if line.startswith("physical id"):
                    phys = line.split(":")[1].strip()
                elif line.startswith("core id"):
                    core = line.split(":")[1].strip()
                    cores.add((phys, core))
            if cores:
                return len(cores)
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    # Fallback: half the logical CPUs approximates physical cores on SMT machines.
    return max((os.cpu_count() or 2) // 2, 1)

# Extensions considered "code" for a first pass. Extend as needed.
CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java", ".rb", ".php",
    ".c", ".cpp", ".h", ".hpp", ".cs", ".sql",
}

# Directories to skip entirely.
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}

# ~4 chars/token is a rough, language-agnostic estimate for code. Chunk size
# is derived from --ctx-size at runtime (see build_chars_per_chunk) rather
# than hardcoded, so it scales if you change the context cap.
CHARS_PER_TOKEN_ESTIMATE = 4
# System prompt + skill file (~450 tokens) + lint output (~150) + chunk
# instructions + the model's own generation budget. Grew from 700 when the
# skill/linter context was added — if you extend SKILL.md, grow this too or
# long chunks will overflow the 3072-token context.
RESERVED_TOKENS = 1400

# Pause between chunk requests on large runs, to avoid pinning all cores at
# 100% for extended stretches (thermal-penalty avoidance). Tune per machine —
# 0 disables pacing entirely.
INTER_CHUNK_PAUSE_SECONDS = 0.3


@dataclass
class Finding:
    file: str
    chunk_index: int
    findings: list[str]
    raw_response: str


@dataclass
class ReviewReport:
    target: str
    model: str
    files_scanned: int = 0
    chunks_reviewed: int = 0
    findings: list[Finding] = field(default_factory=list)


# Bump when SYSTEM_PROMPT/SKILL/review-prompt shape changes — invalidates
# cached responses produced under the old prompts.
PROMPT_VERSION = "2026-07-12"
CACHE_DIR = Path.home() / ".cache" / "getdebug-edge"


class ResultCache:
    """Persistent chunk-level result cache: identical (chunk, system prompt,
    model, prompt version) -> reuse the previous response without inference.

    Deterministic decoding makes this exact: the model would produce the
    same response anyway, so a cache hit is a pure time/energy win on
    re-runs over unchanged files (the pre-commit workflow's common case).
    """

    def __init__(self, model_name: str, system: str, enabled: bool = True):
        self.enabled = enabled
        self.path = CACHE_DIR / "results.json"
        self.prefix = hashlib.sha256(
            f"{model_name}|{PROMPT_VERSION}|{system}".encode()
        ).hexdigest()[:16]
        self.data: dict[str, str] = {}
        self.hits = 0
        if enabled and self.path.exists():
            try:
                self.data = json.loads(self.path.read_text())
            except (OSError, ValueError):
                self.data = {}

    def key(self, prompt: str) -> str:
        return self.prefix + hashlib.sha256(prompt.encode()).hexdigest()[:32]

    def get(self, prompt: str) -> str | None:
        if not self.enabled:
            return None
        hit = self.data.get(self.key(prompt))
        if hit is not None:
            self.hits += 1
        return hit

    def put(self, prompt: str, response: str) -> None:
        if self.enabled and not response.startswith("[agent error"):
            self.data[self.key(prompt)] = response

    def save(self) -> None:
        if not self.enabled:
            return
        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self.data))
        except OSError:
            pass  # cache is best-effort — never fail a run over it


def run_linters(path: Path, max_chars: int = 600) -> str:
    """Run whatever linter is available for this file type and return trimmed
    output for the model to verify against the code. Degrades gracefully:
    ruff -> pyflakes -> py_compile for Python (py_compile is always present,
    so even a bare offline laptop gets syntax checking); `node --check` for
    JavaScript if node exists. Never raises; empty string means no hints.
    """
    cmds: list[list[str]] = []
    if path.suffix == ".py":
        if shutil.which("ruff"):
            cmds.append(["ruff", "check", "--output-format", "concise", "--quiet", str(path)])
        else:
            cmds.append([sys.executable, "-m", "pyflakes", str(path)])
            cmds.append([sys.executable, "-m", "py_compile", str(path)])
    elif path.suffix in (".js", ".mjs", ".cjs") and shutil.which("node"):
        cmds.append(["node", "--check", str(path)])

    for cmd in cmds:
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        except (OSError, subprocess.SubprocessError):
            continue
        output = (proc.stdout + proc.stderr).strip()
        if "No module named" in output:  # pyflakes not installed — try next
            continue
        if output:
            return output[:max_chars]
        return ""  # linter ran clean — no hints needed
    return ""


def discover_files(target: Path) -> list[Path]:
    files = []
    for path in target.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.is_file() and path.suffix in CODE_EXTENSIONS:
            files.append(path)
    return sorted(files)


def chars_per_chunk(ctx_size: int) -> int:
    """Derive a char budget per chunk from the context window, leaving room
    for the system prompt, instructions, and the model's own output."""
    usable_tokens = max(ctx_size - RESERVED_TOKENS, 256)
    return usable_tokens * CHARS_PER_TOKEN_ESTIMATE


def chunk_file(path: Path, char_budget: int) -> list[str]:
    text = path.read_text(errors="ignore")
    if not text.strip():
        return []
    lines = text.splitlines()
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for line in lines:
        line_len = len(line) + 1
        if current and current_len + line_len > char_budget:
            chunks.append("\n".join(current))
            current, current_len = [], 0
        current.append(line)
        current_len += line_len
    if current:
        chunks.append("\n".join(current))
    return chunks


class LlamaServer:
    """Manages a single persistent llama-server process for the whole run.

    Loading the model once and reusing it across chunks is the single
    biggest throughput/thermal win available here — avoid reintroducing
    per-chunk process spawns.
    """

    def __init__(self, model_path: Path, ctx_size: int, threads: int, port: int = 0):
        self.model_path = model_path
        self.ctx_size = ctx_size
        self.threads = threads
        # port 0 = pick a free ephemeral port. Never assume a fixed port is
        # ours: in testing, an unrelated app on 8080 answered /health with
        # 200 and the agent happily reviewed code against a server that
        # wasn't running the model.
        self.port = port or self._free_port()
        self.base_url = f"http://127.0.0.1:{self.port}"
        self.proc: subprocess.Popen | None = None

    @staticmethod
    def _free_port() -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]

    def start(self, startup_timeout: float = 60.0) -> None:
        cmd = [
            "llama-server",
            "-m", str(self.model_path),
            "--ctx-size", str(self.ctx_size),
            "--threads", str(self.threads),
            "--threads-batch", str(self.threads),
            "--batch-size", "512",
            # Quantized V cache requires flash attention — without -fa,
            # llama-server refuses to start with --cache-type-v != f16.
            # (Older llama.cpp builds take bare `--flash-attn` with no value;
            # verify against the installed version.)
            "--flash-attn", "on",
            "--cache-type-k", "q8_0",
            "--cache-type-v", "q8_0",
            "--n-gpu-layers", "0",   # CPU-only: integrated-graphics-only reference hardware
            # Reuse KV-cache chunks matching the previous request's prefix.
            # The system prompt + skill (~450 tokens) is identical on every
            # chunk request — without this, that prefix is re-processed per
            # chunk; with it, prompt processing restarts at the first
            # differing token (the chunk itself).
            "--cache-reuse", "256",
            "--host", "127.0.0.1",
            "--port", str(self.port),
            # No --mlock: let the OS page the model via mmap rather than
            # force-pinning it fully resident, which helps stay inside the
            # 7GB budget alongside the rest of the agent process.
        ]
        try:
            self.proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            )
        except FileNotFoundError:
            raise SystemExit(
                "llama-server not found on PATH. Install llama.cpp first "
                "(e.g. `brew install llama.cpp` on macOS)."
            )

        deadline = time.monotonic() + startup_timeout
        while time.monotonic() < deadline:
            if self.proc.poll() is not None:
                raise SystemExit("llama-server exited during startup — check llama.cpp install/flags.")
            try:
                urllib.request.urlopen(f"{self.base_url}/health", timeout=2)
                return
            except (urllib.error.URLError, ConnectionError, OSError):
                time.sleep(0.5)
        raise SystemExit(f"llama-server did not become healthy within {startup_timeout}s.")

    # temperature 0 (greedy): identical input must produce an identical
    # report. At temp 0.2 the same chunk alternated between bullet and
    # numbered-list findings formats across runs — one of which evaded the
    # parser — and a scanner that flags a bug only sometimes is worse than
    # one that misses it consistently.
    def complete(self, prompt: str, max_tokens: int = 512, temperature: float = 0.0,
                 system: str = SYSTEM_PROMPT) -> str:
        # /v1/chat/completions (not raw /completion) so llama-server applies
        # the model's chat template from the GGUF metadata. Bypassing the
        # template noticeably degrades instruct-model quality.
        payload = json.dumps({
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
            # Still deterministic (penalty is a fixed transform), but stops
            # greedy decoding from degenerating into repetition loops —
            # observed on a real Paystack file where the model emitted 8
            # near-identical "signatureHeader is not a valid X" findings.
            "repeat_penalty": 1.1,
            # Keep this request's prompt KV resident so --cache-reuse can
            # match the shared system+skill prefix on the next request.
            "cache_prompt": True,
        }).encode()
        req = urllib.request.Request(
            f"{self.base_url}/v1/chat/completions", data=payload,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                body = json.loads(resp.read())
                return body["choices"][0]["message"]["content"].strip()
        except Exception as e:  # noqa: BLE001 — surface as a finding, don't crash the run
            return f"[agent error: llama-server request failed: {e}]"

    def stop(self) -> None:
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.proc.kill()


def review_repo(target: Path, server: LlamaServer, char_budget: int, verbose: bool = False,
                system: str = SYSTEM_PROMPT, lint: bool = True,
                cache: ResultCache | None = None) -> ReviewReport:
    report = ReviewReport(target=str(target), model=str(server.model_path))
    files = discover_files(target)
    report.files_scanned = len(files)

    for path in files:
        chunks = chunk_file(path, char_budget)
        lint_output = run_linters(path) if lint else ""
        for idx, chunk in enumerate(chunks):
            prompt = build_review_prompt(str(path.relative_to(target)), chunk, idx, len(chunks),
                                         lint_output=lint_output)
            cached = cache.get(prompt) if cache else None
            response = cached
            if response is None:
                response = server.complete(prompt, system=system)
                if cache:
                    cache.put(prompt, response)
            report.chunks_reviewed += 1
            # Flag on parsed `- [severity]` lines, never on the NO_ISSUES
            # sentinel: in testing the model sometimes appended NO_ISSUES
            # after a valid findings list, which a substring check would
            # have silently swallowed as a clean chunk (see prompts.py).
            found = extract_findings(response)
            if verbose:
                print(f"--- {path} chunk {idx + 1}: {len(found)} finding(s) ---\n{response}\n",
                      file=sys.stderr)
            if found or response.startswith("[agent error"):
                report.findings.append(
                    Finding(file=str(path.relative_to(target)), chunk_index=idx,
                            findings=found, raw_response=response)
                )
            # Thermal pacing only matters after real inference — cache hits
            # cost no compute, so don't sleep on them.
            if INTER_CHUNK_PAUSE_SECONDS and cached is None:
                time.sleep(INTER_CHUNK_PAUSE_SECONDS)

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=Path, help="Path to the codebase to review")
    parser.add_argument("--prompt", help="One-shot mode: send a single question/code snippet to the model and print the answer (used for demos and the contest test_prompts)")
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL_PATH, help="Path to the .gguf model file")
    parser.add_argument("--out", type=Path, default=Path("findings.json"), help="Where to write the JSON report")
    parser.add_argument("--ctx-size", type=int, default=3072, help="llama.cpp context window (tokens). Bounds KV-cache RAM.")
    parser.add_argument("--threads", type=int, default=physical_core_count(), help="CPU threads for llama-server (defaults to physical core count — faster and cooler than logical CPUs for memory-bound generation)")
    parser.add_argument("--port", type=int, default=0, help="llama-server port (default 0 = auto-pick a free port)")
    parser.add_argument("--verbose", action="store_true", help="Print every raw model response to stderr")
    parser.add_argument("--lang", default="", help="Write finding explanations in this language (e.g. 'Twi', 'Swahili', 'French'); code terms stay in English")
    parser.add_argument("--skill", type=Path, default=DEFAULT_SKILL_PATH, help="Path to a skill .md file appended to the system prompt (default skills/SKILL.md)")
    parser.add_argument("--no-skill", action="store_true", help="Disable the skill file")
    parser.add_argument("--no-lint", action="store_true", help="Skip running local linters for extra context")
    parser.add_argument("--diagnostics", action="store_true",
                        help="Also print findings as 'file:line: severity: message' lines "
                             "(VS Code problemMatcher-compatible; see USER_MANUAL.md)")
    parser.add_argument("--no-cache", action="store_true",
                        help="Disable the chunk result cache (unchanged files normally skip re-review on repeat runs)")
    args = parser.parse_args()

    if not args.target and not args.prompt:
        parser.error("provide --target (repo review) or --prompt (one-shot question)")
    if args.target and not args.target.exists():
        sys.exit(f"Target path does not exist: {args.target}")
    if not args.model.exists():
        sys.exit(f"Model not found at {args.model} — run `bash download_model.sh` first.")

    skill_text = ""
    if not args.no_skill and args.skill.exists():
        skill_text = args.skill.read_text(errors="ignore")
    system = build_system_prompt(skill_text, args.lang)

    server = LlamaServer(args.model, args.ctx_size, args.threads, args.port)
    server.start()
    try:
        if args.prompt:
            print(server.complete(args.prompt, system=system))
            return
        budget = chars_per_chunk(args.ctx_size)
        cache = ResultCache(args.model.name, system, enabled=not args.no_cache)
        report = review_repo(args.target, server, budget, verbose=args.verbose,
                             system=system, lint=not args.no_lint, cache=cache)
        cache.save()
    finally:
        server.stop()

    args.out.write_text(json.dumps(
        {
            "target": report.target,
            "model": report.model,
            "files_scanned": report.files_scanned,
            "chunks_reviewed": report.chunks_reviewed,
            "findings": [f.__dict__ for f in report.findings],
        },
        indent=2,
    ))
    if args.diagnostics:
        # Map to the error/warning/info vocabulary VS Code problemMatchers
        # expect. Line numbers are the model's best estimate ("line ~N"),
        # so default to 1 when it didn't give one.
        severity_map = {"high": "error", "medium": "warning", "low": "info"}
        import re as _re
        for f in report.findings:
            for line in f.findings:
                sev_m = _re.search(r"\b(high|medium|low)\b", line, _re.IGNORECASE)
                line_m = _re.search(r"line\s*~?\s*(\d+)", line, _re.IGNORECASE)
                sev = severity_map[sev_m.group(1).lower()] if sev_m else "warning"
                lineno = line_m.group(1) if line_m else "1"
                msg = _re.sub(r"^\s*[-*]\s*[*\[(]*\s*(?:high|medium|low)[])*]*\s*", "", line, flags=_re.IGNORECASE)
                print(f"{Path(report.target) / f.file}:{lineno}: {sev}: {msg.strip()}")

    cache_note = f" ({cache.hits} chunk(s) from cache)" if cache.hits else ""
    print(f"Scanned {report.files_scanned} files, {report.chunks_reviewed} chunks{cache_note}. "
          f"{len(report.findings)} chunk(s) flagged. Report: {args.out}")


if __name__ == "__main__":
    main()
