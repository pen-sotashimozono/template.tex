#!/usr/bin/env python3
"""Bring a document's released PDFs to this machine, with a page that says how they changed.

    python3 .github/scripts/release_log.py notes              # the last three versions
    python3 .github/scripts/release_log.py notes --last 10
    python3 .github/scripts/release_log.py notes --all
    python3 .github/scripts/release_log.py notes 0.1.2 0.1.5  # these versions
    python3 .github/scripts/release_log.py notes --list       # the page only, nothing downloaded

Every release keeps the PDF of its version and the latexdiff against the one
before, but on GitHub, one page per version. This puts them side by side in
log/<document>/:

    log/notes/v0.1.5-notes.pdf         the document as released
    log/notes/diff-v0.1.5-notes.pdf    what changed from 0.1.4, marked in the text
    log/notes/index.md                 every version: date, pages, the changelog's line, the files here

log/ is not committed: it is a copy of what the releases hold, and can be
fetched again. A file already there is not downloaded twice. out/ is the build
of the working tree and is emptied by a clean; log/ is not touched by either.

Needs gh, signed in. Page counts need pdfinfo (poppler) and are left out without it.
"""
import argparse
import json
import pathlib
import re
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
CHANGELOG = ROOT / ".github" / "CHANGELOG.md"
LOG = ROOT / "log"
VERSION = r"\d+\.\d+\.\d+"


def version_of(tag: str, doc: str) -> str | None:
    """The version in a tag of this document: v<version>-<id>, or the older <id>-v<version>."""
    match = re.fullmatch(rf"v({VERSION})-{re.escape(doc)}", tag) or re.fullmatch(rf"{re.escape(doc)}-v({VERSION})", tag)
    return match[1] if match else None


def key(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def versions(releases: list[dict], doc: str) -> list[dict]:
    """This document's releases, newest first: version, tag, date and the names of its files."""
    found = []
    for release in releases:
        version = version_of(release["tag_name"], doc)
        if version and not release.get("draft"):
            found.append({"version": version, "tag": release["tag_name"],
                          "date": (release.get("published_at") or "")[:10],
                          "assets": [a["name"] for a in release.get("assets", [])]})
    return sorted(found, key=lambda r: key(r["version"]), reverse=True)


def select(found: list[dict], wanted: list[str], last: int | None, everything: bool) -> list[dict]:
    if wanted:
        by_version = {r["version"]: r for r in found}
        missing = [v for v in wanted if v.lstrip("v") not in by_version]
        if missing:
            sys.exit(f"no release of version {', '.join(missing)}; there are: {', '.join(r['version'] for r in found)}")
        return [by_version[v.lstrip("v")] for v in wanted]
    return found if everything else found[: last or 3]


def wanted_files(release: dict) -> list[str]:
    """The PDF of the version and its diff. Not the arXiv bundle or the copy without draft marking."""
    tag = release["tag_name"] if "tag_name" in release else release["tag"]
    return [name for name in (f"{tag}.pdf", f"diff-{tag}.pdf") if name in release["assets"]]


def changelog_lines(text: str) -> dict[str, str]:
    """tag -> the first paragraph of its entry, on one line."""
    entries = {}
    for match in re.finditer(r"^## (\S+)[^\n]*\n(.*?)(?=^## |\Z)", text, flags=re.M | re.S):
        paragraph = match[2].strip().split("\n\n")[0]
        entries[match[1]] = " ".join(paragraph.split())
    return entries


def pages(pdf: pathlib.Path) -> int | None:
    if not (pdf.is_file() and shutil.which("pdfinfo")):
        return None
    out = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout
    match = re.search(r"^Pages:\s+(\d+)", out, flags=re.M)
    return int(match[1]) if match else None


def index(doc: str, found: list[dict], lines: dict[str, str], counts: dict[str, int | None], here: set[str]) -> str:
    """The page: one row per released version, newest first."""
    rows = [f"# {doc}: released versions", "",
            "Made by `.github/scripts/release_log.py`; run it again to bring more versions here.", "",
            "| version | released | pages | what changed | here |", "|---|---|---|---|---|"]
    for i, release in enumerate(found):
        count = counts.get(release["tag"])
        before = counts.get(found[i + 1]["tag"]) if i + 1 < len(found) else None
        shown = "" if count is None else str(count) if before is None or before == count else f"{count} ({count - before:+d})"
        files = " · ".join(f"[{'diff' if name.startswith('diff-') else 'pdf'}]({name})"
                           for name in wanted_files(release) if name in here)
        line = lines.get(release["tag"], "").replace("|", "\\|")
        rows.append(f"| {release['version']} | {release['date']} | {shown} | {line} | {files} |")
    return "\n".join(rows) + "\n"


def run(*command: str) -> str:
    return subprocess.run(command, cwd=ROOT, check=True, text=True, capture_output=True).stdout


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("doc", help="document id in docs.toml")
    parser.add_argument("version", nargs="*", help="versions to fetch (default: the last three)")
    parser.add_argument("--last", type=int, metavar="N", help="the N newest versions")
    parser.add_argument("--all", action="store_true", help="every version")
    parser.add_argument("--list", action="store_true", help="write the page and print it; download nothing")
    args = parser.parse_args()

    repo = run("gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner").strip()
    pages_of_releases = json.loads(run("gh", "api", "--paginate", "--slurp", f"repos/{repo}/releases"))
    found = versions([r for page in pages_of_releases for r in page], args.doc)
    if not found:
        sys.exit(f"{repo} has no release of a document '{args.doc}'")

    folder = LOG / args.doc
    folder.mkdir(parents=True, exist_ok=True)
    if not args.list:
        for release in select(found, args.version, args.last, args.all):
            for name in wanted_files(release):
                if (folder / name).is_file():
                    continue
                run("gh", "release", "download", release["tag"], "--repo", repo, "--pattern", name, "--dir", str(folder))
                print(f"log/{args.doc}/{name}")

    here = {p.name for p in folder.glob("*.pdf")}
    counts = {r["tag"]: pages(folder / f"{r['tag']}.pdf") for r in found}
    lines = changelog_lines(CHANGELOG.read_text()) if CHANGELOG.is_file() else {}
    text = index(args.doc, found, lines, counts, here)
    (folder / "index.md").write_text(text)
    if args.list:
        print(text, end="")
    else:
        print(f"log/{args.doc}/index.md  ({sum(1 for r in found if r['tag'] + '.pdf' in here)} of {len(found)} versions here)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
