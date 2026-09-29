"""Tests for the figure tools under .github/tools/figures/ and the arXiv bundle.

    python3 -m unittest discover -s .github/scripts/tests -v

No TeX and no network: build.sh is driven with Python pages only (they write
their SVG directly), arxiv_bundle.sh with stub latexpand / latexmk, and
update-tikz-tensors.sh with local file:// tarballs.
"""
import importlib.util
import io
import os
import pathlib
import shutil
import subprocess
import tarfile
import tempfile
import time
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[3]
TOOLS = ROOT / ".github" / "tools" / "figures"
SCRIPTS = ROOT / ".github" / "scripts"
PAGE = 'import sys\nopen(sys.argv[1], "w").write("<svg/>")\n'


def tmpdir(test):
    d = pathlib.Path(tempfile.mkdtemp())
    test.addCleanup(shutil.rmtree, d)
    return d


class FigureRepo:
    """A throwaway repository with build.sh at .github/tools/figures/ and one topic of Python pages."""

    def __init__(self, test):
        self.test = test
        self.root = tmpdir(test)
        self.tools = self.root / ".github" / "tools" / "figures"
        self.tools.mkdir(parents=True)
        for name in ("build.sh", "latexmkrc"):
            shutil.copy(TOOLS / name, self.tools)
        (self.tools / "schematic.py").write_text("# shared module\n")
        (self.tools / "paper_figures.py").write_text("# separate tool\n")
        self.write("figures/src/t/a.py", PAGE)
        self.write("figures/src/t/b.py", PAGE)

    def write(self, rel, text):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def build(self, *args):
        # From an unrelated working directory: the script must find the repository itself.
        r = subprocess.run(["bash", str(self.tools / "build.sh"), *args], cwd=tempfile.gettempdir(),
                           capture_output=True, text=True)
        self.test.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout.split()

    def age(self, rel, seconds):
        """Set a file's mtime to `seconds` from now (negative: in the past)."""
        t = time.time() + seconds
        os.utime(self.root / rel, (t, t))


class BuildScript(unittest.TestCase):
    def test_every_documented_argument_form_builds_the_page(self):
        repo = FigureRepo(self)
        page = repo.root / "figures/src/t/a.py"
        for arg in ("t", "src/t", "figures/src/t", "figures/src/t/a.py", str(page)):
            with self.subTest(arg=arg):
                shutil.rmtree(repo.root / "figures/assets", ignore_errors=True)
                out = repo.build(arg)
                self.assertIn("figures/assets/t/a.svg", out)
                self.assertTrue((repo.root / "figures/assets/t/a.svg").is_file())

    def test_up_to_date_is_a_no_op_and_force_rebuilds(self):
        repo = FigureRepo(self)
        repo.build()
        for rel in ("figures/src/t/a.py", "figures/src/t/b.py",
                    ".github/tools/figures/schematic.py", ".github/tools/figures/paper_figures.py"):
            repo.age(rel, -100)
        self.assertEqual(repo.build(), [])
        self.assertEqual(sorted(repo.build("--force")), ["figures/assets/t/a.svg", "figures/assets/t/b.svg"])

    def test_shared_module_marks_pages_stale_but_paper_figures_does_not(self):
        repo = FigureRepo(self)
        repo.build()
        for rel in ("figures/src/t/a.py", "figures/src/t/b.py",
                    ".github/tools/figures/schematic.py", ".github/tools/figures/paper_figures.py"):
            repo.age(rel, -100)
        repo.age(".github/tools/figures/paper_figures.py", 100)
        self.assertEqual(repo.build(), [], "editing paper_figures.py must not rerun the pages")
        repo.age(".github/tools/figures/schematic.py", 100)
        self.assertEqual(len(repo.build()), 2, "editing schematic.py must rerun the pages that import it")

    def test_orphans_are_removed_from_assets_only(self):
        repo = FigureRepo(self)
        repo.build()
        repo.write("figures/assets/t/gone.svg", "<svg/>")
        repo.write("figures/assets/t/gone.pdf", "%PDF")
        repo.write("figures/assets/old/x.svg", "<svg/>")
        doc = repo.write("figures/document-figure.pdf", "%PDF")
        repo.build()
        self.assertFalse((repo.root / "figures/assets/t/gone.svg").exists())
        self.assertFalse((repo.root / "figures/assets/t/gone.pdf").exists())
        self.assertFalse((repo.root / "figures/assets/old").exists(), "an emptied topic goes too")
        self.assertTrue(doc.exists(), "the documents' own figures are not build.sh's to delete")
        self.assertTrue((repo.root / "figures/assets/t/a.svg").exists())


class PaperFigures(unittest.TestCase):
    def test_root_is_the_repository(self):
        spec = importlib.util.spec_from_file_location("paper_figures", TOOLS / "paper_figures.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.assertEqual(mod.ROOT, ROOT)
        self.assertTrue((mod.ROOT / "references.bib").is_file())
        self.assertEqual(mod.OUT, ROOT / "figures" / "papers")


class ArxivBundle(unittest.TestCase):
    def test_figures_keep_their_path_and_build_and_papers_stay_out(self):
        root = tmpdir(self)
        scripts = root / ".github" / "scripts"
        scripts.mkdir(parents=True)
        shutil.copy(SCRIPTS / "arxiv_bundle.sh", scripts)
        (scripts / "docs.py").write_text("print('main.tex')\n")      # `docs.py root main`
        bin_ = root / "bin"
        bin_.mkdir()
        (bin_ / "latexpand").write_text('#!/bin/sh\ncat "$1"\n')
        (bin_ / "latexmk").write_text("#!/bin/sh\nexit 0\n")
        for f in bin_.iterdir():
            f.chmod(0o755)
        (root / "main.tex").write_text("\\documentclass{article}\n")
        (root / "out").mkdir()
        (root / "out/main.bbl").write_text("")
        for rel in ("figures/top.pdf", "figures/assets/t/page.pdf",
                    "figures/.build/t/junk.pdf", "figures/papers/other-fig1.pdf"):
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            (root / rel).write_text("%PDF")
        env = dict(os.environ, PATH=f"{bin_}{os.pathsep}{os.environ['PATH']}", PYTHON="python3")
        r = subprocess.run(["sh", ".github/scripts/arxiv_bundle.sh", "main", "dest"], cwd=root,
                           capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        dest = root / "dest"
        self.assertTrue((dest / "top.pdf").is_file())
        self.assertTrue((dest / "assets/t/page.pdf").is_file(), "nested figure path must survive")
        shipped = {p.name for p in dest.rglob("*.pdf")}
        self.assertNotIn("junk.pdf", shipped)
        self.assertNotIn("other-fig1.pdf", shipped)


def release_tarball(path, tag, files):
    """A GitHub-style source tarball: everything under one top-level directory."""
    with tarfile.open(path, "w:gz") as tar:
        for rel, text in files.items():
            data = text.encode()
            info = tarfile.TarInfo(f"tikz-tensors-{tag.lstrip('v')}/{rel}")
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))


FULL = {"tex/tikz-tensors.sty": "% new sty\n", "tex/tikz-tensors-colors.tex": "% new colours\n",
        "theme/theme.css": "/* new */\n", "theme/tokens.toml": "# new\n", "LICENSE": "MIT\n"}


class UpdateTikzTensors(unittest.TestCase):
    def setUp(self):
        self.root = tmpdir(self)
        tools = self.root / "tools"
        tools.mkdir()
        shutil.copy(TOOLS / "update-tikz-tensors.sh", tools)
        self.script = tools / "update-tikz-tensors.sh"
        self.vendored = tools / "tikz-tensors"
        (self.vendored / "tex").mkdir(parents=True)
        (self.vendored / "tex/tikz-tensors.sty").write_text("% old sty\n")
        (self.vendored / "VERSION").write_text("v0.1.0\n")

    def run_script(self, tag, url):
        return subprocess.run(["sh", str(self.script), tag], cwd=self.root, capture_output=True, text=True,
                              env=dict(os.environ, TIKZ_TENSORS_URL=url))

    def assert_untouched(self):
        self.assertEqual((self.vendored / "VERSION").read_text(), "v0.1.0\n")
        self.assertEqual((self.vendored / "tex/tikz-tensors.sty").read_text(), "% old sty\n")
        self.assertEqual(sorted(p.name for p in self.vendored.parent.iterdir()),
                         ["tikz-tensors", "update-tikz-tensors.sh"], "no half-built copy left behind")

    def test_a_release_replaces_the_copy_whole(self):
        tarball = self.root / "rel.tar.gz"
        release_tarball(tarball, "v0.2.0", FULL)
        r = self.run_script("v0.2.0", tarball.as_uri())
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual((self.vendored / "VERSION").read_text(), "v0.2.0\n")
        self.assertEqual((self.vendored / "tex/tikz-tensors.sty").read_text(), "% new sty\n")
        self.assertTrue((self.vendored / "LICENSE").is_file())

    def test_a_failed_download_says_so_and_changes_nothing(self):
        r = self.run_script("v9.9.9", (self.root / "no-such.tar.gz").as_uri())
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("could not download", r.stderr)
        self.assert_untouched()

    def test_an_incomplete_release_changes_nothing(self):
        tarball = self.root / "rel.tar.gz"
        release_tarball(tarball, "v0.2.0", {k: v for k, v in FULL.items() if k != "LICENSE"})
        r = self.run_script("v0.2.0", tarball.as_uri())
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("has no LICENSE", r.stderr)
        self.assert_untouched()


if __name__ == "__main__":
    unittest.main()
