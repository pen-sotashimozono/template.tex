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
                shutil.rmtree(repo.root / "figures/generated", ignore_errors=True)
                out = repo.build(arg)
                self.assertIn("figures/generated/t/a.svg", out)
                self.assertTrue((repo.root / "figures/generated/t/a.svg").is_file())

    def test_up_to_date_is_a_no_op_and_force_rebuilds(self):
        repo = FigureRepo(self)
        repo.build()
        for rel in ("figures/src/t/a.py", "figures/src/t/b.py",
                    ".github/tools/figures/schematic.py", ".github/tools/figures/paper_figures.py"):
            repo.age(rel, -100)
        self.assertEqual(repo.build(), [])
        self.assertEqual(sorted(repo.build("--force")), ["figures/generated/t/a.svg", "figures/generated/t/b.svg"])

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

    def test_orphans_are_removed_from_generated_only(self):
        repo = FigureRepo(self)
        repo.build()
        repo.write("figures/generated/t/gone.svg", "<svg/>")
        repo.write("figures/generated/t/gone.pdf", "%PDF")
        repo.write("figures/generated/old/x.svg", "<svg/>")
        doc = repo.write("figures/document-figure.pdf", "%PDF")
        mine = repo.write("figures/assets/plot.pdf", "%PDF")
        repo.build()
        self.assertFalse((repo.root / "figures/generated/t/gone.svg").exists())
        self.assertFalse((repo.root / "figures/generated/t/gone.pdf").exists())
        self.assertFalse((repo.root / "figures/generated/old").exists(), "an emptied topic goes too")
        self.assertTrue(doc.exists(), "the documents' own figures are not build.sh's to delete")
        self.assertTrue(mine.exists(), "assets/ holds figures made by hand, which have no page under src/")
        self.assertTrue((repo.root / "figures/generated/t/a.svg").exists())


TEX_STUBS = {
    # latexmk -r <rc> -outdir=<dir> <page>.tex  ->  <dir>/<page>.pdf
    "latexmk": '#!/bin/sh\nfor a in "$@"; do case "$a" in -outdir=*) d="${a#-outdir=}";; *.tex) n="$(basename "$a" .tex)";; esac; done\n'
               'mkdir -p "$d" && printf "%%PDF" > "$d/$n.pdf"\n',
    "pdfinfo": '#!/bin/sh\necho "Pages: 1"\n',
    "pdftocairo": '#!/bin/sh\nfor a in "$@"; do last="$a"; done\necho "<svg/>" > "$last"\n',
}


class PdfOnly(unittest.TestCase):
    """--pdf-only, what the root .latexmkrc runs: the PDFs a checkout lacks, and no committed file."""

    def repo(self):
        repo = FigureRepo(self)
        (repo.tools / "tikz-tensors.sh").write_text("#!/bin/sh\n")
        (repo.tools / "tikz-tensors.sh").chmod(0o755)
        repo.write("figures/src/t/c.tex", "a page\n")
        self.bin = tmpdir(self)
        for name, body in TEX_STUBS.items():
            (self.bin / name).write_text(body)
            (self.bin / name).chmod(0o755)
        return repo

    def build(self, repo, *args):
        env = dict(os.environ, PATH=f"{self.bin}{os.pathsep}{os.environ['PATH']}")
        r = subprocess.run(["bash", str(repo.tools / "build.sh"), *args], cwd=tempfile.gettempdir(),
                           capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout.split()

    def test_builds_the_missing_pdf_and_leaves_every_svg_alone(self):
        repo = self.repo()
        svg = repo.write("figures/generated/t/c.svg", "committed")
        repo.age("figures/generated/t/c.svg", -100)          # older than its page, as after a checkout
        self.assertEqual(self.build(repo, "--pdf-only"), ["figures/generated/t/c.pdf"])
        self.assertEqual(svg.read_text(), "committed", "a checkout's SVG must not be rewritten")
        self.assertFalse((repo.root / "figures/generated/t/a.svg").exists(), "Python pages have no PDF")
        self.assertEqual(self.build(repo, "--pdf-only"), [], "up to date is a no-op")

    def test_a_page_newer_than_its_pdf_is_rebuilt(self):
        repo = self.repo()
        self.build(repo, "--pdf-only")
        repo.age("figures/generated/t/c.pdf", -100)
        self.assertEqual(self.build(repo, "--pdf-only"), ["figures/generated/t/c.pdf"])

    def test_the_full_build_still_writes_both(self):
        repo = self.repo()
        self.assertIn("figures/generated/t/c.svg", self.build(repo, "--pdf"))
        self.assertTrue((repo.root / "figures/generated/t/c.pdf").is_file())

    def test_nothing_to_build_needs_neither_git_nor_the_network(self):
        repo = self.repo()
        self.build(repo, "--pdf-only")
        (repo.tools / "tikz-tensors.sh").write_text("#!/bin/sh\necho 'no network' >&2\nexit 1\n")
        self.assertEqual(self.build(repo, "--pdf-only"), [], "up to date: the submodule is not asked for")

    def test_a_repository_without_pages_is_silent(self):
        # /bin/bash on macOS is 3.2, where an empty array is unbound under set -u.
        repo = self.repo()
        shutil.rmtree(repo.root / "figures/src/t")
        r = subprocess.run(["bash", str(repo.tools / "build.sh"), "--pdf-only"], capture_output=True, text=True)
        self.assertEqual((r.returncode, r.stdout, r.stderr), (0, "", ""))

    def test_pages_are_built_several_at_a_time_and_one_failure_fails_the_run(self):
        repo = self.repo()
        for name in "defgh":
            repo.write(f"figures/src/t/{name}.tex", "a page\n")
        slow = TEX_STUBS["latexmk"].replace('mkdir -p "$d" && printf', 'sleep 0.5; printf')
        (self.bin / "latexmk").write_text(slow)
        env = dict(os.environ, PATH=f"{self.bin}{os.pathsep}{os.environ['PATH']}", FIGURE_JOBS="6")
        cmd = ["bash", str(repo.tools / "build.sh"), "--pdf-only"]
        start = time.time()
        r = subprocess.run(cmd, capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(sorted(r.stdout.split()), [f"figures/generated/t/{n}.pdf" for n in "cdefgh"])
        self.assertLess(time.time() - start, 2.0, "six pages of 0.5 s each, one after another, take 3 s")
        (self.bin / "latexmk").write_text('#!/bin/sh\ncase "$*" in *e.tex*) exit 1;; esac\n' + slow.split("\n", 1)[1])
        r = subprocess.run(cmd + ["--force"], capture_output=True, text=True, env=env)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("src/t/e.tex failed", r.stderr)
        self.assertEqual(sorted(r.stdout.split()), [f"figures/generated/t/{n}.pdf" for n in "cdfgh"],
                         "one broken page does not keep the others from being built")

    def test_an_svg_whose_page_is_gone_is_left_for_the_writer(self):
        repo = self.repo()
        svg = repo.write("figures/generated/t/gone.svg", "committed")
        repo.write("figures/generated/t/gone.pdf", "%PDF")
        self.build(repo, "--pdf-only")
        self.assertTrue(svg.exists(), "a build of a document must not delete a committed SVG")
        self.assertFalse((repo.root / "figures/generated/t/gone.pdf").exists(), "the built PDF does go")

    def test_two_runs_at_once_do_not_share_a_build_directory(self):
        # What `latexmk main.tex` and `latexmk notes.tex` side by side amount to. The
        # first run exits, and cleans up, while the second is in the middle of the page.
        repo = self.repo()
        slow = TEX_STUBS["latexmk"].replace('mkdir -p "$d" && printf', 'sleep 0.6; printf')
        self.assertNotEqual(slow, TEX_STUBS["latexmk"])
        (self.bin / "latexmk").write_text(slow)
        env = dict(os.environ, PATH=f"{self.bin}{os.pathsep}{os.environ['PATH']}")
        cmd = ["bash", str(repo.tools / "build.sh"), "--pdf-only"]
        first = subprocess.Popen(cmd, cwd=repo.root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        time.sleep(0.3)
        second = subprocess.run(cmd, cwd=repo.root, env=env, capture_output=True, text=True)
        _, err = first.communicate()
        self.assertEqual((first.returncode, second.returncode), (0, 0), err.decode() + second.stderr)
        self.assertEqual((repo.root / "figures/generated/t/c.pdf").read_text(), "%PDF")
        self.assertFalse((repo.root / "figures/.build").exists(), "nothing but src/ and generated/ remains")


class Closure(unittest.TestCase):
    """A built figure PDF is not tracked; the closure reads it as the sources it was built from."""

    def test_a_figure_pdf_stands_for_its_page_and_the_shared_files(self):
        spec = importlib.util.spec_from_file_location("closure", SCRIPTS / "closure.py")
        import sys
        sys.path.insert(0, str(SCRIPTS))
        self.addCleanup(sys.path.remove, str(SCRIPTS))
        closure = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(closure)
        tracked = {
            "figures/src/t/page.tex", ".github/tools/figures/preamble.tex",
            ".github/tools/figures/notation.tex", ".github/tools/figures/build.sh",
            ".github/tools/figures/tikz-tensors", "notes.tex",
        }
        # Through a build record, as `affected` reads it: the line latexmk writes for
        # \includegraphics{generated/t/page} is the only trace of the figure in out/.
        root = tmpdir(self)
        (root / "out").mkdir()
        (root / "out/notes.fls").write_text(f"PWD {root}\nINPUT ./notes.tex\nINPUT ./figures/generated/t/page.pdf\n")
        self.addCleanup(setattr, closure, "ROOT", closure.ROOT)
        closure.ROOT = root
        self.assertEqual(closure.closure("notes", {"version": "0.1.0"}, tracked), tracked - {
            ".github/tools/figures/build.sh"})
        self.assertEqual(closure.closure("notes", {"version": "0.1.0"}, {"notes.tex"}), {"notes.tex"})

        got = closure.figure_sources("figures/generated/t/page.pdf", tracked)
        self.assertEqual(got & tracked, {
            "figures/src/t/page.tex", ".github/tools/figures/preamble.tex",
            ".github/tools/figures/notation.tex", ".github/tools/figures/tikz-tensors",
        })
        self.assertEqual(closure.figure_sources("figures/papers/x-fig1.pdf", tracked), set())
        self.assertEqual(closure.figure_sources("notes.tex", tracked), set())


class RootLatexmkrc(unittest.TestCase):
    """The figure hook in the root .latexmkrc, run as the Perl it is, with a stub bash."""

    def run_rc(self, *argv, bash="exit 0", path=None, ci=None):
        root = tmpdir(self)
        shutil.copy(ROOT / ".latexmkrc", root)
        (root / "figures/src").mkdir(parents=True)
        (root / ".github/tools/figures").mkdir(parents=True)
        (root / ".github/tools/figures/build.sh").write_text("")
        bin = tmpdir(self)
        if bash is not None:
            (bin / "bash").write_text(f"#!/bin/sh\necho \"$@\" > '{root}/called'\n{bash}\n")
            (bin / "bash").chmod(0o755)
        env = dict(os.environ, PATH=f"{bin}{os.pathsep}/usr/bin{os.pathsep}/bin" if path is None else path)
        for name in ("CI", "GITHUB_ACTIONS", "GITHUB_RUN_ID"):       # these tests run in CI too
            env.pop(name, None)
        if ci:
            env[ci] = "true"
        r = subprocess.run([shutil.which("perl"), ".latexmkrc", *argv], cwd=root, capture_output=True, text=True, env=env)
        called = (root / "called").read_text().split() if (root / "called").exists() else None
        return r, called

    def test_a_build_runs_the_pdf_only_figure_build_first(self):
        r, called = self.run_rc("notes.tex")
        self.assertEqual((r.returncode, called), (0, [".github/tools/figures/build.sh", "--pdf-only"]), r.stderr)

    def test_a_page_that_fails_stops_the_build_in_ci(self):
        # GITHUB_RUN_ID is the one the LaTeX container is handed; CI is what a runner sets.
        for name in ("CI", "GITHUB_ACTIONS", "GITHUB_RUN_ID"):
            with self.subTest(variable=name):
                r, _ = self.run_rc("notes.tex", bash="exit 1", ci=name)
                self.assertNotEqual(r.returncode, 0)
                self.assertIn("build.sh --pdf-only", r.stderr)

    def test_a_page_that_fails_is_a_warning_on_a_writers_machine(self):
        r, _ = self.run_rc("notes.tex", bash="exit 1")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("did not build", r.stderr)

    def test_calls_that_compile_nothing_build_no_page(self):
        for argv in (["-c", "notes.tex"], ["-C"], ["-v"], ["--version"], ["-h"]):
            with self.subTest(argv=argv):
                r, called = self.run_rc(*argv, bash="exit 1")
                self.assertEqual((r.returncode, called), (0, None), r.stderr)

    def test_without_bash_the_build_goes_on_with_a_warning(self):
        r, _ = self.run_rc("notes.tex", bash=None, path=str(tmpdir(self)))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("no bash", r.stderr)


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
        for rel in ("figures/top.pdf", "figures/generated/t/page.pdf",
                    "figures/.build/t/junk.pdf", "figures/papers/other-fig1.pdf"):
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            (root / rel).write_text("%PDF")
        env = dict(os.environ, PATH=f"{bin_}{os.pathsep}{os.environ['PATH']}", PYTHON="python3")
        r = subprocess.run(["sh", ".github/scripts/arxiv_bundle.sh", "main", "dest"], cwd=root,
                           capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        dest = root / "dest"
        self.assertTrue((dest / "top.pdf").is_file())
        self.assertTrue((dest / "generated/t/page.pdf").is_file(), "nested figure path must survive")
        shipped = {p.name for p in dest.rglob("*.pdf")}
        self.assertNotIn("junk.pdf", shipped)
        self.assertNotIn("other-fig1.pdf", shipped)


def sty(version):
    return f"\\ProvidesPackage{{tikz-tensors}}[2026/09/29 v{version} test]\n"


class TikzTensorsSubmodule(unittest.TestCase):
    """tikz-tensors.sh against a local tikz-tensors: main carries releases v0.1.0 and
    v0.2.0 and then a docs-only commit (still v0.2.0, as the gates keep main); a side
    branch carries v0.3.0, a tag whose \\ProvidesPackage line wrongly says 0.2.9."""

    def setUp(self):
        root = tmpdir(self)
        self.env = dict(os.environ, GIT_CONFIG_COUNT="1", GIT_CONFIG_KEY_0="protocol.file.allow",
                        GIT_CONFIG_VALUE_0="always", GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
                        GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
        self.origin = root / "tikz-tensors"
        (self.origin / "tex").mkdir(parents=True)
        self.git(self.origin, "init", "-q", "-b", "main")
        for version in ("0.1.0", "0.2.0"):
            self.origin_commit({"tex/tikz-tensors.sty": sty(version)}, f"v{version}")
            self.git(self.origin, "tag", f"v{version}")
        self.origin_commit({"README.md": "docs\n"}, "docs after v0.2.0")
        self.git(self.origin, "switch", "-q", "-c", "broken")
        self.origin_commit({"tex/tikz-tensors.sty": sty("0.2.9")}, "broken")
        self.git(self.origin, "tag", "v0.3.0")
        self.git(self.origin, "switch", "-q", "main")
        self.env["TIKZ_TENSORS_URL"] = str(self.origin)
        self.repo = root / "project"
        (self.repo / ".github/tools/figures").mkdir(parents=True)
        shutil.copy(TOOLS / "tikz-tensors.sh", self.repo / ".github/tools/figures/")
        self.git(self.repo, "init", "-q", "-b", "main")
        self.git(self.repo, "remote", "add", "origin", "https://example.org/me/My-Paper.git")
        self.git(self.repo, "add", "-A")
        self.git(self.repo, "commit", "-qm", "project")
        self.sub = self.repo / ".github/tools/figures/tikz-tensors"

    def git(self, where, *args):
        r = subprocess.run(["git", "-C", str(where), *args], capture_output=True, text=True, env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def origin_commit(self, files, message):
        for rel, text in files.items():
            (self.origin / rel).write_text(text)
        self.git(self.origin, "add", "-A")
        self.git(self.origin, "commit", "-qm", message)

    def script(self, *args, repo=None):
        return subprocess.run(["sh", ".github/tools/figures/tikz-tensors.sh", *args], cwd=repo or self.repo,
                              capture_output=True, text=True, env=self.env)

    def ok(self, *args, repo=None):
        r = self.script(*args, repo=repo)
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        return r

    def version(self, repo=None):
        return ((repo or self.repo) / ".github/tools/figures/tikz-tensors/tex/tikz-tensors.sty").read_text()

    def staged_gitlink(self):
        return self.git(self.repo, "ls-files", "-s", "--", ".github/tools/figures/tikz-tensors").split()[:2]

    # -- ensure -------------------------------------------------------------

    def test_ensure_adds_it_at_main_which_is_the_newest_release(self):
        r = self.ok("ensure")
        self.assertIn("at v0.2.0", r.stderr)
        self.assertEqual(self.version(), sty("0.2.0"))
        self.assertEqual(self.staged_gitlink()[0], "160000", "the pin is staged as a submodule")
        main = self.git(self.origin, "rev-parse", "main").strip()
        self.assertEqual(self.staged_gitlink()[1], main, "main itself, docs commit included")
        self.assertEqual(self.git(self.repo, "config", "push.recurseSubmodules").strip(), "check")

    def test_ensure_writes_the_config_once(self):
        # build.sh calls ensure before every build of a document; worktrees share one
        # .git/config, so a write on every call makes two builds at once fight over its lock.
        self.ok("ensure")
        lock = self.repo / ".git/config.lock"
        lock.write_text("")
        self.addCleanup(lock.unlink)
        self.ok("ensure")

    def test_ensure_restores_what_use_this_template_drops(self):
        """A template copy has .gitmodules and an empty directory, but no pinned commit."""
        (self.repo / ".gitmodules").write_text(
            '[submodule ".github/tools/figures/tikz-tensors"]\n'
            "\tpath = .github/tools/figures/tikz-tensors\n"
            "\turl = https://github.com/pen-sotashimozono/tikz-tensors\n")
        self.sub.mkdir()
        self.ok("ensure")
        self.assertEqual(self.version(), sty("0.2.0"))
        self.assertEqual(self.staged_gitlink()[0], "160000")

    def test_ensure_refuses_a_main_that_is_not_a_release(self):
        self.origin_commit({"tex/tikz-tensors.sty": sty("0.2.0") + "% unreleased\n"}, "ungated")
        r = self.script("ensure")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("is not a release", r.stderr)

    def test_a_fresh_clone_is_initialised_at_the_recorded_pin(self):
        self.ok("pin", "v0.1.0")
        self.git(self.repo, "commit", "-qm", "pin v0.1.0")
        clone = self.repo.parent / "clone"
        self.git(self.repo.parent, "clone", "-q", str(self.repo), str(clone))
        self.assertFalse((clone / ".github/tools/figures/tikz-tensors/tex").exists())
        self.ok("ensure", repo=clone)
        self.assertEqual(self.version(clone), sty("0.1.0"), "the recorded pin, not the newest")

    # -- pin ----------------------------------------------------------------

    def test_pin_moves_to_a_release_and_stages_it(self):
        self.ok("pin", "v0.2.0")
        before = self.staged_gitlink()[1]
        self.ok("pin", "v0.1.0")
        self.assertEqual(self.version(), sty("0.1.0"))
        self.assertNotEqual(self.staged_gitlink()[1], before)

    def test_pin_refuses_a_missing_tag(self):
        self.ok("pin", "v0.2.0")
        r = self.script("pin", "v9.9.9")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("no tag v9.9.9", r.stderr)
        self.assertEqual(self.version(), sty("0.2.0"))

    def test_pin_refuses_a_tag_whose_version_line_disagrees(self):
        self.ok("pin", "v0.2.0")
        r = self.script("pin", "v0.3.0")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("not a release", r.stderr)
        self.assertEqual(self.version(), sty("0.2.0"))

    # -- developing in place --------------------------------------------------

    def develop(self):
        """dev branch in the submodule, one commit on it."""
        self.ok("pin", "latest")
        self.git(self.repo, "commit", "-qm", "pin")
        r = self.ok("dev", "fn-size")
        self.assertIn("my-paper/fn-size", r.stdout)
        (self.sub / "tex/tikz-tensors.sty").write_text(sty("0.2.0") + "% an edit in place\n")
        self.git(self.sub, "commit", "-qam", "edit")
        self.git(self.repo, "add", ".github/tools/figures/tikz-tensors")
        self.git(self.repo, "commit", "-qm", "build with the proposal")

    def test_status_of_a_release(self):
        self.ok("pin", "v0.2.0")
        out = self.ok("status").stdout
        self.assertIn("release v0.2.0", out)
        self.assertNotIn("not pushed", out)

    def test_status_of_an_unpushed_proposal(self):
        self.develop()
        out = self.ok("status").stdout
        self.assertIn("(my-paper/fn-size)", out)
        self.assertIn("proposal, not a release", out)
        self.assertIn("main: 1 ahead, 0 behind", out)
        self.assertIn("not pushed", out)

    def test_check_passes_a_release(self):
        self.ok("pin", "v0.2.0")
        self.git(self.repo, "commit", "-qm", "pin")
        out = self.ok("check").stdout
        self.assertIn("release v0.2.0", out)
        self.assertTrue(out.rstrip().endswith("OK"), out)

    def test_check_fails_an_unpushed_pin_and_warns_on_a_pushed_proposal(self):
        self.develop()
        clone = self.repo.parent / "ci"
        self.git(self.repo.parent, "clone", "-q", str(self.repo), str(clone))
        r = self.script("check", repo=clone)
        self.assertNotEqual(r.returncode, 0, "the pinned commit exists only in the project's submodule")
        self.assertIn("is not on", r.stdout)
        self.git(self.sub, "push", "-q", "origin", "my-paper/fn-size")
        r = self.script("check", repo=clone)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("::warning::", r.stdout)
        self.assertIn("on my-paper/fn-size", r.stdout)


if __name__ == "__main__":
    unittest.main()
