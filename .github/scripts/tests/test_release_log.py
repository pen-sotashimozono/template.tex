"""Tests for release_log.py: which releases are a document's, which files are fetched, what the page says.

    python3 -m unittest discover -s .github/scripts/tests -v

Nothing here talks to GitHub.
"""
import importlib.util
import pathlib
import unittest

SCRIPTS = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("release_log", SCRIPTS / "release_log.py")
log = importlib.util.module_from_spec(spec)
spec.loader.exec_module(log)


def release(tag, date="2026-01-02T03:04:05Z", extra=(), draft=False):
    return {"tag_name": tag, "published_at": date, "draft": draft,
            "assets": [{"name": name} for name in (f"{tag}.pdf", f"arxiv-bundle-{tag}.zip", *extra)]}


RELEASES = [
    release("v0.1.9-notes"), release("v0.1.10-notes", extra=("diff-v0.1.10-notes.pdf", "clean-v0.1.10-notes.pdf")),
    release("notes-v0.0.9"), release("v0.1.0-main"), release("v0.2.0-notes", draft=True), release("v0.1.0-subnotes"),
]


class Versions(unittest.TestCase):
    def test_a_documents_releases_newest_first_by_number_not_by_spelling(self):
        found = log.versions(RELEASES, "notes")
        self.assertEqual([r["version"] for r in found], ["0.1.10", "0.1.9", "0.0.9"])
        self.assertEqual(found[0]["date"], "2026-01-02")

    def test_the_default_is_the_last_three_and_a_version_can_be_named(self):
        found = log.versions(RELEASES, "notes")
        self.assertEqual(len(log.select(found, [], None, False)), 3)
        self.assertEqual([r["version"] for r in log.select(found, [], 1, False)], ["0.1.10"])
        self.assertEqual([r["version"] for r in log.select(found, ["v0.1.9", "0.0.9"], None, False)], ["0.1.9", "0.0.9"])
        with self.assertRaises(SystemExit):
            log.select(found, ["0.3.0"], None, False)

    def test_only_the_pdf_and_its_diff_are_fetched(self):
        found = log.versions(RELEASES, "notes")
        self.assertEqual(log.wanted_files(found[0]), ["v0.1.10-notes.pdf", "diff-v0.1.10-notes.pdf"])
        self.assertEqual(log.wanted_files(found[1]), ["v0.1.9-notes.pdf"], "a first version has no diff")


class Page(unittest.TestCase):
    def test_the_changelog_gives_one_line_per_tag(self):
        text = "# Changelog\n\nIntro.\n\n## v0.1.10-notes — 2026-01-02\n\nA proof was\nrewritten.\n\nMore detail.\n\n## v0.1.9-notes\n\nFirst | draft.\n"
        self.assertEqual(log.changelog_lines(text), {"v0.1.10-notes": "A proof was rewritten.", "v0.1.9-notes": "First | draft."})

    def test_a_row_per_version_with_pages_and_only_the_files_that_are_here(self):
        found = log.versions(RELEASES, "notes")
        lines = {"v0.1.10-notes": "A proof was rewritten.", "v0.1.9-notes": "First | draft."}
        counts = {"v0.1.10-notes": 14, "v0.1.9-notes": 12, "notes-v0.0.9": None}
        page = log.index("notes", found, lines, counts, {"v0.1.10-notes.pdf", "diff-v0.1.10-notes.pdf"})
        self.assertIn("| 0.1.10 | 2026-01-02 | 14 (+2) | A proof was rewritten. | [pdf](v0.1.10-notes.pdf) · [diff](diff-v0.1.10-notes.pdf) |", page)
        self.assertIn("| 0.1.9 | 2026-01-02 | 12 | First \\| draft. |  |", page)
        self.assertIn("| 0.0.9 | 2026-01-02 |  |  |  |", page)


if __name__ == "__main__":
    unittest.main()
