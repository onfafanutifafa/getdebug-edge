"""Unit tests for the offline pieces of the agent (no model required).

Run: python3 -m unittest discover tests
"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "agent"))

from agent import ResultCache, chars_per_chunk, chunk_file, physical_core_count, run_linters  # noqa: E402
from prompts import build_review_prompt, build_system_prompt, extract_findings  # noqa: E402
from detectors import scan_text  # noqa: E402


class ExtractFindingsTest(unittest.TestCase):
    """Formats observed from the real model during testing — each of these
    styles appeared in actual runs, including the decorated ones that the
    original strict regex missed."""

    def test_plain_bracket_format(self):
        self.assertEqual(len(extract_findings(
            "- [high] SQL injection (line ~4) — fix: parameterize")), 1)

    def test_bold_bracket_format(self):
        self.assertEqual(len(extract_findings(
            "- **[medium]** - string concat in query. **Fix:** use params")), 1)

    def test_bold_bare_format(self):
        self.assertEqual(len(extract_findings(
            "- **high** Division by zero — fix: guard empty list")), 1)

    def test_asterisk_bullet(self):
        self.assertEqual(len(extract_findings("* [low] unused variable")), 1)

    def test_sentinel_not_a_finding(self):
        self.assertEqual(extract_findings("NO_ISSUES"), [])
        self.assertEqual(extract_findings("### NO_ISSUES"), [])

    def test_prose_bullet_not_a_finding(self):
        self.assertEqual(extract_findings("- The function updates the fees table"), [])

    def test_findings_followed_by_stray_sentinel(self):
        # Observed: model appends NO_ISSUES after a valid findings list.
        text = ("- **[medium]** - SQL injection risk. **Fix:** parameterize.\n"
                "- **[low]** - Division by zero. **Fix:** guard.\n"
                "### NO_ISSUES")
        self.assertEqual(len(extract_findings(text)), 2)


class ChunkingTest(unittest.TestCase):
    def test_budget_scales_with_ctx(self):
        self.assertGreater(chars_per_chunk(8192), chars_per_chunk(3072))
        self.assertGreaterEqual(chars_per_chunk(256), 256 * 4 // 4)  # floor applies

    def test_chunks_respect_budget(self):
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f.write("\n".join(f"x{i} = {i}  # padding line" for i in range(500)))
            path = Path(f.name)
        budget = 1000
        chunks = chunk_file(path, budget)
        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            self.assertLessEqual(len(chunk), budget + 80)  # one line of slack
        # No content lost
        self.assertEqual("\n".join(chunks).count("\n"), 499)
        path.unlink()

    def test_empty_file_no_chunks(self):
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f.write("   \n\n")
            path = Path(f.name)
        self.assertEqual(chunk_file(path, 1000), [])
        path.unlink()


class PromptsTest(unittest.TestCase):
    def test_system_prompt_composes_skill_and_lang(self):
        s = build_system_prompt("REVIEW METHODOLOGY", "Swahili")
        self.assertIn("REVIEW METHODOLOGY", s)
        self.assertIn("Swahili", s)

    def test_lint_section_included_when_present(self):
        p = build_review_prompt("a.py", "code", 0, 1, lint_output="a.py:1: unused import")
        self.assertIn("Linter output", p)
        p2 = build_review_prompt("a.py", "code", 0, 1)
        self.assertNotIn("Linter output", p2)


class ResultCacheTest(unittest.TestCase):
    def test_round_trip_and_isolation(self):
        c = ResultCache("model-a.gguf", "system prompt v1")
        c.put("prompt X", "response X")
        self.assertEqual(c.get("prompt X"), "response X")
        self.assertIsNone(c.get("prompt Y"))
        # Different model or system prompt must not share entries.
        other = ResultCache("model-b.gguf", "system prompt v1")
        other.data = c.data
        self.assertIsNone(other.get("prompt X"))

    def test_error_responses_never_cached(self):
        c = ResultCache("m.gguf", "s")
        c.put("p", "[agent error: llama-server request failed: timeout]")
        self.assertIsNone(c.get("p"))

    def test_disabled_cache_is_inert(self):
        c = ResultCache("m.gguf", "s", enabled=False)
        c.put("p", "r")
        self.assertIsNone(c.get("p"))


class DetectorTest(unittest.TestCase):
    """The deterministic hybrid pass must catch the pattern-matchable classes
    the model misses, and — critically — never fire on clean code."""

    def _has(self, findings, needle):
        return any(needle.lower() in f.lower() for f in findings)

    def test_hardcoded_stripe_key(self):
        f = scan_text('API_KEY = "sk_live_abc123DEF456ghi789"\n')
        self.assertTrue(self._has(f, "hardcoded secret"))

    def test_jwt_secret_by_varname(self):
        f = scan_text('JWT_SECRET = "supersecret123"\n')
        self.assertTrue(self._has(f, "hardcoded secret"))

    def test_md5_weak_hash(self):
        f = scan_text("import hashlib\nh = hashlib.md5(pw.encode())\n")
        self.assertTrue(self._has(f, "weak hash"))

    def test_ecb_mode(self):
        f = scan_text("cipher = AES.new(KEY, AES.MODE_ECB)\n")
        self.assertTrue(self._has(f, "ecb"))

    def test_password_in_logs(self):
        f = scan_text('logging.info("user=%s pass=%s", user, password)\n')
        self.assertTrue(self._has(f, "sensitive data"))

    def test_env_ref_not_flagged(self):
        # A secret read from the environment is correct, not a finding.
        self.assertEqual(scan_text('API_KEY = os.environ["API_KEY"]\n'), [])

    def test_placeholder_not_flagged(self):
        self.assertEqual(scan_text('API_KEY = "changeme"\n'), [])

    def test_clean_code_silent(self):
        clean = ("def add(a, b):\n    return a + b\n\n"
                 "import bcrypt\nh = bcrypt.hashpw(pw, bcrypt.gensalt())\n")
        self.assertEqual(scan_text(clean), [])


class EnvironmentTest(unittest.TestCase):
    def test_physical_core_count_sane(self):
        n = physical_core_count()
        self.assertGreaterEqual(n, 1)
        self.assertLessEqual(n, 128)

    def test_linters_flag_syntax_error(self):
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f.write("def broken(:\n    pass\n")
            path = Path(f.name)
        out = run_linters(path)
        self.assertTrue(out, "expected linter output for a syntax error")
        path.unlink()


if __name__ == "__main__":
    unittest.main()
