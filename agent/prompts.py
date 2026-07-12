"""Prompt templates for the getdebug-edge local review agent.

Shaped by an A/B test against the real 3B model (see SCOPE.md §7): a terse
"respond in exactly this format or say NO_ISSUES" prompt made the model answer
NO_ISSUES even on code containing a blatant SQL injection — small models take
the escape hatch when it's the most salient instruction. Letting the model
briefly analyze the code BEFORE listing findings recovered full recall
(SQL injection, division-by-zero, validation bugs) on the same input.

Findings are detected by parsing `- [severity]` lines (FINDING_RE), never by
searching for the NO_ISSUES sentinel — in testing the model sometimes emitted
NO_ISSUES *after* a valid findings list, which a substring check would have
silently swallowed as a clean chunk.
"""
import re

# A bullet whose first token is a severity, tolerating markdown decoration the
# model adds despite instructions: `- [high] ...`, `- **[medium]** - ...`,
# `- **high** ...`. Tuned for recall over precision — a false positive still
# carries its raw response into the report; a false negative silently drops a
# real bug (observed: the plain `\[?severity\]?` version missed a chunk whose
# findings were all `- **[medium]**`-style).
FINDING_RE = re.compile(
    r"^\s*[-*]\s*[*\[(]*\s*(?:high|medium|low)\b[])*]*.*$",
    re.IGNORECASE | re.MULTILINE,
)

SYSTEM_PROMPT = """You are getdebug-edge, an expert security-focused code reviewer \
running fully offline on a developer's laptop. You review one chunk of source code \
at a time for real bugs, security vulnerabilities, and correctness issues — injection \
flaws, unvalidated input, logic errors, unhandled edge cases (empty input, zero, \
None), and resource leaks. Do not invent problems and do not report style nitpicks."""


def build_system_prompt(skill_text: str = "", lang: str = "") -> str:
    """Compose the system prompt from the base identity, an optional skill
    file (review methodology, DRY guidance, linter-output handling), and an
    optional output language for finding explanations.

    Keep skill files short — every token here is re-processed on every chunk
    and eats into the 3072-token context budget.
    """
    parts = [SYSTEM_PROMPT]
    if skill_text.strip():
        parts.append(skill_text.strip())
    if lang:
        parts.append(
            f"Write all finding summaries, explanations, and fix descriptions in "
            f"{lang}. Keep code identifiers, code snippets, and the severity tags "
            f"[high|medium|low] in English so reports stay machine-parseable."
        )
    return "\n\n".join(parts)


def build_review_prompt(file_path: str, chunk_text: str, chunk_index: int, chunk_total: int,
                        lint_output: str = "") -> str:
    lint_section = ""
    if lint_output.strip():
        lint_section = f"""
Linter output for this file (static-analysis hints — verify each against the code):
```
{lint_output.strip()}
```
"""
    return f"""File: {file_path} (chunk {chunk_index + 1}/{chunk_total})

```
{chunk_text}
```
{lint_section}
First, briefly walk through what this code does and what could go wrong (2-3 \
sentences). Then list your findings, one line each:
- [high|medium|low] <one-line summary> (line ~N) — fix: <short suggested fix>

If your analysis finds no real issues, write NO_ISSUES instead of a findings list."""


def extract_findings(response: str) -> list[str]:
    """Return the `- [severity] ...` lines from a model response.

    An empty list means the chunk is clean (or the model followed the
    NO_ISSUES path) — callers should flag a chunk iff this is non-empty.
    """
    return [m.group(0).strip() for m in FINDING_RE.finditer(response)]
