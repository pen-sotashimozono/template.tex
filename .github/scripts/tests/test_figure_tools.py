"""Tests for the figure tools under .github/tools/figures/ and the arXiv bundle.

    python3 -m unittest discover -s .github/scripts/tests -v

No TeX and no network: build.sh is driven with Python pages only (they write
their SVG directly), arxiv_bundle.sh with stub latexpand / latexmk, and
tikz-tensors.sh with a local tikz-tensors repository and throwaway projects.
"""
import importlib.util
import os
import pathlib
import shutil
import subprocess
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


def sty(version):
    return f"\\ProvidesPackage{{tikz-tensors}}[2026/09/29 v{version} test]\n"


class TikzTensorsSubmodule(unittest.TestCase):
    """tikz-tensors.sh against a local tikz-tensors with releases v0.1.0 and v0.2.0
    (and a v0.3.0 whose \\ProvidesPackage line wrongly says 0.2.9)."""

    def setUp(self):
        root = tmpdir(self)
        self.env = dict(os.environ, GIT_CONFIG_COUNT="1", GIT_CONFIG_KEY_0="protocol.file.allow",
                        GIT_CONFIG_VALUE_0="always", GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
                        GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
        self.origin = root / "tikz-tensors"
        (self.origin / "tex").mkdir(parents=True)
        self.git(self.origin, "init", "-q", "-b", "main")
        for tag, version in (("v0.1.0", "0.1.0"), ("v0.2.0", "0.2.0"), ("v0.3.0", "0.2.9")):
            (self.origin / "tex/tikz-tensors.sty").write_text(sty(version))
            self.git(self.origin, "add", "-A")
            self.git(self.origin, "commit", "-qm", tag)
            self.git(self.origin, "tag", tag)
        # v0.3.0 is broken on purpose; the newest good release is what "latest" must not
        # guess around, so tests that want "latest" delete it first.
        self.env["TIKZ_TENSORS_URL"] = str(self.origin)
        self.repo = root / "project"
        (self.repo / ".github/tools/figures").mkdir(parents=True)
        shutil.copy(TOOLS / "tikz-tensors.sh", self.repo / ".github/tools/figures/")
        self.git(self.repo, "init", "-q", "-b", "main")
        self.git(self.repo, "add", "-A")
        self.git(self.repo, "commit", "-qm", "project")
        self.sub = self.repo / ".github/tools/figures/tikz-tensors"

    def git(self, where, *args):
        r = subprocess.run(["git", "-C", str(where), *args], capture_output=True, text=True, env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def script(self, *args, repo=None):
        return subprocess.run(["sh", ".github/tools/figures/tikz-tensors.sh", *args], cwd=repo or self.repo,
                              capture_output=True, text=True, env=self.env)

    def version(self, repo=None):
        return ((repo or self.repo) / ".github/tools/figures/tikz-tensors/tex/tikz-tensors.sty").read_text()

    def staged_gitlink(self):
        return self.git(self.repo, "ls-files", "-s", "--", ".github/tools/figures/tikz-tensors").split()[:2]

    def drop_broken_release(self):
        self.git(self.origin, "tag", "-d", "v0.3.0")

    def test_ensure_adds_it_at_the_newest_release(self):
        self.drop_broken_release()
        r = self.script("ensure")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("v0.2.0", r.stderr)
        self.assertEqual(self.version(), sty("0.2.0"))
        self.assertEqual(self.staged_gitlink()[0], "160000", "the pin is staged as a submodule")
        self.assertIn("tikz-tensors", (self.repo / ".gitmodules").read_text())

    def test_ensure_restores_what_use_this_template_drops(self):
        """A template copy has .gitmodules and an empty directory, but no pinned commit."""
        self.drop_broken_release()
        (self.repo / ".gitmodules").write_text(
            '[submodule ".github/tools/figures/tikz-tensors"]\n'
            "\tpath = .github/tools/figures/tikz-tensors\n"
            "\turl = https://github.com/pen-sotashimozono/tikz-tensors\n")
        self.sub.mkdir()
        r = self.script("ensure")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.version(), sty("0.2.0"))
        self.assertEqual(self.staged_gitlink()[0], "160000")

    def test_a_fresh_clone_is_initialised_at_the_recorded_pin(self):
        self.assertEqual(self.script("pin", "v0.1.0").returncode, 0)
        self.git(self.repo, "commit", "-qm", "pin v0.1.0")
        clone = self.repo.parent / "clone"
        self.git(self.repo.parent, "clone", "-q", str(self.repo), str(clone))
        self.assertFalse((clone / ".github/tools/figures/tikz-tensors/tex").exists())
        r = self.script("ensure", repo=clone)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.version(clone), sty("0.1.0"), "the recorded pin, not the newest")

    def test_pin_moves_to_a_release_and_stages_it(self):
        self.assertEqual(self.script("pin", "v0.2.0").returncode, 0)
        before = self.staged_gitlink()[1]
        r = self.script("pin", "v0.1.0")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.version(), sty("0.1.0"))
        self.assertNotEqual(self.staged_gitlink()[1], before)

    def test_pin_refuses_a_missing_tag(self):
        self.assertEqual(self.script("pin", "v0.2.0").returncode, 0)
        r = self.script("pin", "v9.9.9")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("no tag v9.9.9", r.stderr)
        self.assertEqual(self.version(), sty("0.2.0"))

    def test_pin_refuses_a_tag_whose_version_line_disagrees(self):
        r = self.script("pin", "v0.3.0")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("says v0.2.9", r.stderr)

    def test_status_names_the_release_or_says_it_is_not_one(self):
        self.assertEqual(self.script("pin", "v0.2.0").returncode, 0)
        self.assertIn("= release v0.2.0", self.script("status").stdout)
        (self.sub / "tex/tikz-tensors.sty").write_text(sty("0.2.0") + "% an edit in place\n")
        self.git(self.sub, "commit", "-qam", "edit")
        out = self.script("status").stdout
        self.assertIn("not a release", out)
        self.assertIn("differs from the commit this repository records", out)


if __name__ == "__main__":
    unittest.main()
