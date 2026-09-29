import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import bib_files  # noqa: E402

BIB = """% a comment
@article{has2020pdf,
  title      = {One},
  doi        = {10.1/one},
}

@article{no2021pdf,
  title      = {Two},
  file       = {refs/no2021pdf.pdf},
}
"""


class BibFiles(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        (self.root / "refs").mkdir()
        (self.root / "refs" / "has2020pdf.pdf").write_bytes(b"%PDF")

    def tearDown(self):
        self.tmp.cleanup()

    def test_adds_and_removes(self):
        out = bib_files.with_files(BIB, self.root)
        self.assertIn("  file       = {refs/has2020pdf.pdf},\n}", out)
        self.assertNotIn("no2021pdf.pdf", out)
        self.assertIn("% a comment", out)

    def test_idempotent(self):
        once = bib_files.with_files(BIB, self.root)
        self.assertEqual(bib_files.with_files(once, self.root), once)

    def test_check_flags_stale(self):
        bib = self.root / "references.bib"
        bib.write_text(BIB)
        self.assertEqual(bib_files.main([str(bib), "--check"]), 1)
        self.assertEqual(bib_files.main([str(bib)]), 0)
        self.assertEqual(bib_files.main([str(bib), "--check"]), 0)


if __name__ == "__main__":
    unittest.main()
