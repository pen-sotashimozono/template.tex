"""Tests for rename_releases.py: what it decides to rename. Nothing here talks to GitHub.

    python3 -m unittest discover -s .github/scripts/tests -v
"""
import importlib.util
import pathlib
import unittest

SCRIPTS = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("rename_releases", SCRIPTS / "rename_releases.py")
rename = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rename)

TAGS = ["v0.0.1", "v0.1.0-main", "v0.1.0-notes", "v0.1.1-notes", "v0.2.0-notes", "v0.1.0-notes_old", "v0.1.0-subnotes"]
RELEASES = [
    {"id": 11, "tag_name": "v0.1.1-notes", "name": "v0.1.1-notes", "assets": [
        {"id": 1, "name": "v0.1.1-notes.pdf"}, {"id": 2, "name": "diff-v0.1.1-notes.pdf"},
        {"id": 3, "name": "arxiv-bundle-v0.1.1-notes.zip"}, {"id": 4, "name": "supplement.pdf"}]},
    {"id": 12, "tag_name": "v0.2.0-notes", "name": "The spring version", "assets": []},
    {"id": 13, "tag_name": "v0.1.0-main", "name": "v0.1.0-main", "assets": [{"id": 5, "name": "v0.1.0-main.pdf"}]},
]


class Plan(unittest.TestCase):
    def test_only_the_tags_of_that_id_and_every_one_of_them(self):
        steps = rename.plan("notes", "lecture", TAGS, RELEASES)
        self.assertEqual([(s["old"], s["new"]) for s in steps], [
            ("v0.1.0-notes", "v0.1.0-lecture"), ("v0.1.1-notes", "v0.1.1-lecture"), ("v0.2.0-notes", "v0.2.0-lecture")])

    def test_a_release_follows_its_tag_with_its_files(self):
        by_old = {s["old"]: s for s in rename.plan("notes", "lecture", TAGS, RELEASES)}
        self.assertIsNone(by_old["v0.1.0-notes"]["release"], "a tag that was never released is still renamed")
        step = by_old["v0.1.1-notes"]
        self.assertEqual((step["release"], step["title"]), (11, "v0.1.1-lecture"))
        self.assertEqual(step["assets"], [
            (1, "v0.1.1-notes.pdf", "v0.1.1-lecture.pdf"), (2, "diff-v0.1.1-notes.pdf", "diff-v0.1.1-lecture.pdf"),
            (3, "arxiv-bundle-v0.1.1-notes.zip", "arxiv-bundle-v0.1.1-lecture.zip")])
        self.assertEqual(by_old["v0.2.0-notes"]["title"], "The spring version", "a title written by hand is kept")

    def test_it_refuses_before_changing_anything(self):
        for old, new, tags in (("notes", "main", TAGS), ("notes", "notes", TAGS), ("notes", "my-notes", TAGS)):
            with self.subTest(new=new), self.assertRaises(SystemExit):
                rename.plan(old, new, tags, RELEASES)
        self.assertEqual(rename.plan("absent", "lecture", TAGS, RELEASES), [])


class Changelog(unittest.TestCase):
    def test_headings_of_that_id_only(self):
        text = "## v0.1.1-notes — 2026-01-02\n\nSee v0.1.0-notes for the rest.\n\n## v0.1.0-notes_old\n\n## v0.1.0-main — 2026-01-01\n"
        self.assertEqual(rename.rewrite_changelog(text, "notes", "lecture"),
                         "## v0.1.1-lecture — 2026-01-02\n\nSee v0.1.0-notes for the rest.\n\n## v0.1.0-notes_old\n\n## v0.1.0-main — 2026-01-01\n")


if __name__ == "__main__":
    unittest.main()
