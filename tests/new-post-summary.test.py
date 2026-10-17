"""Regression tests for tools/new-post.py summarize(): descriptions must never end mid-phrase.
Run: python3 tests/new-post-summary.test.py"""
import importlib.util
import pathlib
import unittest

spec = importlib.util.spec_from_file_location(
    "new_post", pathlib.Path(__file__).resolve().parent.parent / "tools" / "new-post.py")
new_post = importlib.util.module_from_spec(spec)
spec.loader.exec_module(new_post)
summarize = new_post.summarize


class SummarizeTests(unittest.TestCase):
    def test_short_text_unchanged(self):
        self.assertEqual(summarize("Short lede."), "Short lede.")

    def test_whole_sentences_within_limit(self):
        text = ("I ran thirty agents against five domains and asked each to refute the others. "
                "Fourteen findings survived. Ten were killed by the verifiers, which was the point of the exercise.")
        out = summarize(text)
        self.assertLessEqual(len(out), 160)
        self.assertTrue(out.endswith("."))
        self.assertTrue(text.startswith(out))

    def test_abbreviation_is_not_a_sentence_end(self):
        # Codex review of PR #5: "Dr." used to end the summary at 96 chars with no ellipsis.
        text = ("I met Dr. Camera at a conference about verification, and we argued for an hour about whether "
                "a passing test suite proves anything when the tests were written by the same agent that wrote the code.")
        out = summarize(text)
        self.assertFalse(out.endswith("Dr."))
        self.assertTrue(out.endswith("…"))
        self.assertLessEqual(len(out), 160)

    def test_no_punctuation_cuts_at_word_boundary(self):
        out = summarize("word " * 60)
        self.assertTrue(out.endswith("…"))
        self.assertLessEqual(len(out), 160)
        self.assertNotIn("wor…", out)

    def test_the_original_bug_input(self):
        text = ("I own six domains. Across three working sessions I wired five of them into a single person entity: "
                "one @id, defined once, referenced by every property, so that search engines resolve one person "
                "instead of six unrelated mentions. That build was agent-driven too, one file at a time, and at the "
                "end of it I had a passing test suite and a good feeling.")
        out = summarize(text)
        self.assertFalse(out.rstrip().endswith("of"))
        self.assertLessEqual(len(out), 160)


if __name__ == "__main__":
    unittest.main()
