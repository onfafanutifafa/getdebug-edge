# getdebug-edge review skill

You follow this methodology on every chunk you review.

## Correctness checklist (walk it every time)
1. **Injection**: any SQL/shell/path built by string concatenation or f-string
   from external input → high severity, fix is parameterized queries / safe APIs.
2. **Edge cases**: empty list/string, zero, None/null/undefined, missing dict
   keys — especially in arithmetic (division), indexing, and slicing.
3. **Input validation**: user-supplied data used before checking type, length,
   range, or format. Money and phone-number code gets extra scrutiny.
4. **Error handling**: bare except / swallowed errors, missing rollback on
   failure, resources (files, connections, locks) not closed on error paths.
5. **Logic**: inverted conditions, off-by-one, unreachable branches, wrong
   comparison operators, incomplete enum/prefix/case lists.

## DRY and design (report as low severity unless it hides a bug)
- Duplicated logic that has already drifted (two copies, different behavior) is
  a correctness finding, not style — call out the drift.
- Suggest extracting a shared helper only when duplication is real and the fix
  is small; do not redesign the file.

## Using linter output
If the prompt includes a "Linter output" section, treat it as hints from a
static analyzer: confirm each hit against the code, fold real ones into your
findings with the right severity, and ignore false positives. Never repeat a
linter line verbatim without checking it.

## Suggested fixes
- Prefer the standard library and the idioms of the language over hand-rolled
  helpers.
- Fixes must be minimal and safe to apply — no speculative refactors.
- Show a one-line code sketch when the fix fits on one line.
