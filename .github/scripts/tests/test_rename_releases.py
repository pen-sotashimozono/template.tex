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

    def test_the_older_form_of_tag_keeps_its_form(self):
        steps = rename.plan("notes", "lecture", ["notes-v0.0.11", "main-v0.0.11", "subnotes-v0.0.1", "v0.0.9"], [])
        self.assertEqual([(s["old"], s["new"]) for s in steps], [("notes-v0.0.11", "lecture-v0.0.11")])

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


class Detect(unittest.TestCase):
    """Which change of docs.toml is a rename: only one the files bear out."""

    BEFORE = {"main": "main.tex", "notes": "notes.tex", "talk": "slides/talk.pptx"}

    def test_a_table_renamed_with_its_file(self):
        after = {"main": "main.tex", "lecture": "lecture.tex", "talk": "slides/talk.pptx"}
        self.assertEqual(rename.detect(self.BEFORE, after, {"notes.tex": "lecture.tex"}), {"notes": "lecture"})

    def test_a_table_renamed_over_the_same_file(self):
        after = {"main": "main.tex", "lecture": "notes.tex", "talk": "slides/talk.pptx"}
        self.assertEqual(rename.detect(self.BEFORE, after, {}), {"notes": "lecture"})

    def test_an_export_and_a_document_renamed_at_once(self):
        after = {"main": "main.tex", "lecture": "lecture.tex", "seminar": "slides/seminar.pptx"}
        moved = {"notes.tex": "lecture.tex", "slides/talk.pptx": "slides/seminar.pptx"}
        self.assertEqual(rename.detect(self.BEFORE, after, moved), {"notes": "lecture", "talk": "seminar"})

    def test_two_documents_that_trade_ids(self):
        # The files traded contents (git, with --break-rewrites, reports both as renamed) ...
        moved = {"main.tex": "notes.tex", "notes.tex": "main.tex"}
        self.assertEqual(rename.detect(self.BEFORE, self.BEFORE, moved), {"main": "notes", "notes": "main"})
        # ... or the tables traded their `root`.
        before = {"main": "paper.tex", "notes": "book.tex"}
        after = {"main": "book.tex", "notes": "paper.tex"}
        self.assertEqual(rename.detect(before, after, {}), {"main": "notes", "notes": "main"})

    def test_three_documents_in_a_ring(self):
        before = {"a": "a.tex", "b": "b.tex", "c": "c.tex"}
        moved = {"a.tex": "b.tex", "b.tex": "c.tex", "c.tex": "a.tex"}
        self.assertEqual(rename.detect(before, before, moved), {"a": "b", "b": "c", "c": "a"})

    def test_one_removed_and_another_added_is_not_a_rename(self):
        after = {"main": "main.tex", "thesis": "thesis.tex", "talk": "slides/talk.pptx"}
        self.assertEqual(rename.detect(self.BEFORE, after, {}), {})
        self.assertEqual(rename.detect(self.BEFORE, after, {"old.tex": "thesis.tex"}), {})

    def test_a_bump_or_a_new_document_is_nothing(self):
        self.assertEqual(rename.detect(self.BEFORE, dict(self.BEFORE, thesis="thesis.tex"), {}), {})
        self.assertEqual(rename.detect(self.BEFORE, self.BEFORE, {"a.tex": "b.tex"}), {})

    def test_what_does_not_hold_together_moves_nothing(self):
        # A root rewritten so far that git pairs it with a new document's: main keeps its table.
        after = dict(self.BEFORE, thesis="thesis.tex")
        self.assertEqual(rename.detect(self.BEFORE, after, {"main.tex": "thesis.tex"}), {})
        # One file's worth of history cannot go to an id whose document stays.
        after = {"main": "main.tex", "talk": "slides/talk.pptx"}
        self.assertEqual(rename.detect(self.BEFORE, after, {"notes.tex": "main.tex"}), {})
        # Two documents cannot become one.
        before = {"a": "a.tex", "b": "b.tex"}
        self.assertEqual(rename.detect(before, {"c": "a.tex"}, {"b.tex": "a.tex"}), {})

    def test_the_file_of_a_table(self):
        manifest = '[main]\nversion = "0.1.0"\n[notes]\nroot = "n/root.tex"\nversion = "0.1.0"\n[talk]\nsource = "s/t.pptx"\nversion = "0.1.0"\n[settings]\nstrict = "false"\n'
        self.assertEqual(rename.files(manifest), {"main": "main.tex", "notes": "n/root.tex", "talk": "s/t.pptx"})


class Order(unittest.TestCase):
    """The renames in an order that never lands on tags still in use."""

    def replay(self, pairs):
        ids = {doc_id: doc_id for doc_id in set(pairs) | set(pairs.values())}   # id -> the document now under it
        ids = {doc_id: doc_id for doc_id in pairs}
        for old, new in rename.order(pairs):
            self.assertNotIn(new, ids, f"{old} -> {new} lands on a document that has not moved yet")
            ids[new] = ids.pop(old)
        return ids

    def test_a_plain_rename_is_one_step(self):
        self.assertEqual(rename.order({"notes": "lecture"}), [("notes", "lecture")])

    def test_a_chain_goes_from_its_free_end(self):
        self.assertEqual(rename.order({"a": "b", "b": "c"}), [("b", "c"), ("a", "b")])

    def test_a_swap_goes_through_an_id_of_its_own(self):
        steps = rename.order({"main": "notes", "notes": "main"})
        self.assertEqual(steps, [("main", "renaming_main"), ("notes", "main"), ("renaming_main", "notes")])
        self.assertEqual(self.replay({"main": "notes", "notes": "main"}), {"notes": "main", "main": "notes"})

    def test_a_ring_of_three_ends_where_it_should(self):
        pairs = {"a": "b", "b": "c", "c": "a"}
        self.assertEqual(self.replay(pairs), {"b": "a", "c": "b", "a": "c"})
        for step in rename.order(pairs):
            self.assertTrue(rename.ID.fullmatch(step[1]), "a temporary id is still an id")


class Changelog(unittest.TestCase):
    def test_headings_of_that_id_only(self):
        text = ("## v0.1.1-notes — 2026-01-02\n\nSee v0.1.0-notes for the rest.\n\n## v0.1.0-notes_old\n\n"
                "## v0.1.0-main — 2026-01-01\n\n## notes-v0.0.9 — 2025-12-01\n")
        self.assertEqual(rename.rewrite_changelog(text, "notes", "lecture"),
                         "## v0.1.1-lecture — 2026-01-02\n\nSee v0.1.0-notes for the rest.\n\n## v0.1.0-notes_old\n\n"
                         "## v0.1.0-main — 2026-01-01\n\n## lecture-v0.0.9 — 2025-12-01\n")
        self.assertEqual(rename.heading_tags(text, "notes"), ["v0.1.1-notes", "notes-v0.0.9"])


if __name__ == "__main__":
    unittest.main()
