"""Tests for docs.py / exports.py, run against throwaway git repositories.

    python3 -m unittest discover -s .github/scripts/tests -v

The build tests need LibreOffice and are skipped without `soffice`.
"""
import pathlib
import shutil
import subprocess
import tempfile
import unittest

SCRIPTS = pathlib.Path(__file__).resolve().parent.parent
FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures"
BASE_TOML = '[main]\nversion = "0.1.0"\n'
TALK = '\n[talk]\nsource = "slides/talk.pptx"\nversion = "0.1.0"\n'


class Repo:
    def __init__(self, test, toml=""):
        self.root = pathlib.Path(tempfile.mkdtemp())
        test.addCleanup(shutil.rmtree, self.root)
        scripts = self.root / ".github" / "scripts"
        scripts.mkdir(parents=True)
        for name in ("docs.py", "exports.py", "soffice_pdf.py"):
            shutil.copy(SCRIPTS / name, scripts)
        self.git("init", "-q", "-b", "main")
        self.write("docs.toml", BASE_TOML + toml)
        self.commit("base")

    def write(self, path, text):
        (self.root / path).parent.mkdir(parents=True, exist_ok=True)
        (self.root / path).write_text(text)

    def git(self, *args):
        return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
                              cwd=self.root, capture_output=True, text=True, check=True).stdout

    def commit(self, message):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)

    def run(self, script, *args):
        return subprocess.run(["python3", f".github/scripts/{script}", *args],
                              cwd=self.root, capture_output=True, text=True)

    def check_bump(self, base="main"):
        (self.root / "base.toml").write_text(self.git("show", f"{base}:docs.toml"))
        return self.run("exports.py", "check-bump", "--base", "base.toml", "--base-ref", base)

    def set_talk_version(self, version):
        text = (self.root / "docs.toml").read_text()
        self.write("docs.toml", text.replace('version = "0.1.0"\n', f'version = "{version}"\n')
                   .replace(f'[main]\nversion = "{version}"', '[main]\nversion = "0.1.0"'))


class Manifest(unittest.TestCase):
    def test_latex_only_views(self):
        repo = Repo(self, TALK)
        self.assertEqual(repo.run("docs.py", "ids").stdout.split(), ["main"])
        self.assertEqual(repo.run("docs.py", "ids", "--all").stdout.split(), ["main", "talk"])
        self.assertEqual(repo.run("docs.py", "kind", "talk").stdout.strip(), "export")
        self.assertEqual(repo.run("docs.py", "kind", "main").stdout.strip(), "tex")
        self.assertNotEqual(repo.run("docs.py", "root", "talk").returncode, 0)
        self.assertEqual(repo.run("docs.py", "tag", "talk").stdout.strip(), "v0.1.0-talk")
        self.assertEqual(repo.run("exports.py", "ids").stdout.split(), ["talk"])

    def test_rejects_bad_tables(self):
        cases = {
            "hyphen in id": '\n[my-talk]\nsource = "a.pptx"\nversion = "0.1.0"\n',
            "shell in id": '\n["$(id)"]\nsource = "a.pptx"\nversion = "0.1.0"\n',
            "version not a string": '\n[talk]\nsource = "a.pptx"\nversion = 1\n',
            "absolute source": '\n[talk]\nsource = "/etc/passwd.pptx"\nversion = "0.1.0"\n',
            "source outside repo": '\n[talk]\nsource = "../x.pptx"\nversion = "0.1.0"\n',
            "unknown extension": '\n[talk]\nsource = "a.key"\nversion = "0.1.0"\n',
            "root and source": '\n[talk]\nroot = "a.tex"\nsource = "a.pptx"\nversion = "0.1.0"\n',
        }
        for label, toml in cases.items():
            with self.subTest(label):
                result = Repo(self, toml).run("docs.py", "ids", "--all")
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("docs.toml [", result.stderr)


class CheckBump(unittest.TestCase):
    def repo_with_source(self):
        """main carries [talk] with its source committed; HEAD is a work branch."""
        repo = Repo(self, TALK)
        repo.write("slides/talk.pptx", "v1")
        repo.commit("first source")
        repo.git("switch", "-q", "-c", "work")
        return repo

    def test_new_export_ships_at_its_version(self):
        repo = Repo(self)
        repo.git("switch", "-q", "-c", "work")
        repo.write("docs.toml", BASE_TOML + TALK)
        repo.write("slides/talk.pptx", "v1")
        repo.commit("new export")
        result = repo.check_bump()
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("new export", result.stdout)

    def test_first_source_ships_at_table_version(self):
        repo = Repo(self, TALK)
        repo.git("switch", "-q", "-c", "work")
        repo.write("slides/talk.pptx", "v1")
        repo.commit("first source")
        result = repo.check_bump()
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("first source", result.stdout)

    def test_changed_source_needs_bump(self):
        repo = self.repo_with_source()
        repo.write("slides/talk.pptx", "v2")
        repo.commit("edit")
        self.assertNotEqual(repo.check_bump().returncode, 0)
        repo.set_talk_version("0.1.1")
        repo.commit("bump")
        result = repo.check_bump()
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_bump_without_change_fails(self):
        repo = self.repo_with_source()
        repo.set_talk_version("0.1.1")
        repo.commit("bump")
        self.assertNotEqual(repo.check_bump().returncode, 0)

    def test_renamed_source_needs_bump(self):
        repo = self.repo_with_source()
        repo.git("mv", "slides/talk.pptx", "slides/talk2.pptx")
        repo.write("slides/talk2.pptx", "v2")
        text = (repo.root / "docs.toml").read_text()
        repo.write("docs.toml", text.replace("slides/talk.pptx", "slides/talk2.pptx"))
        repo.commit("rename and edit")
        result = repo.check_bump()
        self.assertNotEqual(result.returncode, 0, result.stdout)

    def test_check_step_covers_exports(self):
        repo = self.repo_with_source()
        repo.set_talk_version("0.3.0")
        repo.commit("jump")
        (repo.root / "base.toml").write_text(repo.git("show", "main:docs.toml"))
        result = repo.run("docs.py", "check-step", "--base", "base.toml")
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("talk", result.stdout)


@unittest.skipUnless(shutil.which("soffice"), "LibreOffice not installed")
class Build(unittest.TestCase):
    def test_builds_pptx_and_docx(self):
        toml = ('\n[deck]\nsource = "slides/sample.pptx"\nversion = "0.1.0"\n'
                '\n[report]\nsource = "reports/sample.docx"\nversion = "0.1.0"\n')
        repo = Repo(self, toml)
        for doc, src in (("deck", "slides/sample.pptx"), ("report", "reports/sample.docx")):
            with self.subTest(doc):
                (repo.root / src).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(FIXTURES / pathlib.Path(src).name, repo.root / src)
                result = repo.run("exports.py", "build", doc)
                self.assertEqual(result.returncode, 0, result.stderr)
                pdf = repo.root / "out" / f"{doc}.pdf"
                self.assertTrue(pdf.read_bytes().startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()
