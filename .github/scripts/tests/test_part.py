"""Tests for part.py, which compiles only some sections of a document.

    python3 -m unittest discover -s .github/scripts/tests -v

No TeX: what is tested is which files are taken for sections and what is
handed to LaTeX, not the compile.
"""
import importlib.util
import pathlib
import shutil
import sys
import tempfile
import unittest

SCRIPTS = pathlib.Path(__file__).resolve().parents[1]


class Part(unittest.TestCase):
    def setUp(self):
        sys.path.insert(0, str(SCRIPTS))
        self.addCleanup(sys.path.remove, str(SCRIPTS))
        spec = importlib.util.spec_from_file_location("part", SCRIPTS / "part.py")
        self.part = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.part)
        self.root = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        self.part.ROOT = self.root
        (self.root / "notes").mkdir()
        (self.root / "out").mkdir()
        (self.root / "notes/01-intro.tex").write_text("\\section{Intro}\n\\label{sec:intro}\n")
        (self.root / "notes/02-mps.tex").write_text("\\section{MPS}\n\\label{sec:mps}\n\\label{eq:x}\n")
        (self.root / "notes/A1-code.tex").write_text("\\section{Code}\n\\label{sec:code}\n")
        (self.root / "notes.tex").write_text(
            "\\input{preamble-that-is-not-here}\n\\begin{document}\n"
            "\\input{notes/01-intro}\n  \\input{notes/02-mps.tex}  % the second\n"
            "Text with \\input{notes/01-intro} inside a line.\n\\input{notes/A1-code}\n\\end{document}\n")

    def test_sections_are_the_existing_files_input_on_their_own_line(self):
        self.assertEqual(self.part.sections(self.root / "notes.tex"),
                         ["notes/01-intro.tex", "notes/02-mps.tex", "notes/A1-code.tex"])

    def test_a_section_is_chosen_by_any_part_of_its_path(self):
        every = self.part.sections(self.root / "notes.tex")
        self.assertEqual(self.part.select(every, ["mps", "01"]), ["notes/02-mps.tex", "notes/01-intro.tex"])
        with self.assertRaises(SystemExit):
            self.part.select(every, ["dmrg"])

    def test_the_others_are_replaced_and_numbers_come_from_the_full_build(self):
        (self.root / "out/notes.aux").write_text(
            "\\newlabel{sec:intro}{{1}{3}{Intro}{section.1}{}}\n"
            "\\newlabel{sec:mps}{{2}{7}{MPS}{section.2}{}}\n"
            "\\newlabel{eq:x}{{2.1}{7}{MPS}{equation.2.1}{}}\n"
            "\\newlabel{sec:code}{{A}{90}{Code}{appendix.A}{}}\n")
        every = self.part.sections(self.root / "notes.tex")
        tex = self.part.pretex(every, ["notes/02-mps.tex", "notes/A1-code.tex"], "notes")
        self.assertIn("\\declare@file@substitution{notes/01-intro.tex}{out/notes-part.skip.tex}", tex)
        self.assertNotIn("substitution{notes/02-mps.tex}", tex)
        self.assertIn("\\AddToHook{file/02-mps.tex/before}{\\setcounter{section}{1}}", tex)
        self.assertNotIn("file/A1-code.tex/before", tex, "an appendix letter is not a number to start from")
        self.assertIn("\\externaldocument{out/notes}", tex)

    def test_without_a_full_build_nothing_is_borrowed(self):
        every = self.part.sections(self.root / "notes.tex")
        tex = self.part.pretex(every, ["notes/02-mps.tex"], "notes")
        self.assertNotIn("externaldocument", tex)
        self.assertNotIn("setcounter", tex)


if __name__ == "__main__":
    unittest.main()
