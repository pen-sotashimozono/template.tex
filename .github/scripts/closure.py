#!/usr/bin/env python3
"""Dependency closure of each root document listed in docs.toml.

A document is not one file: a root pulls in child .tex files through \\input
and its bibliography through bibtex. Version checks and releases have to fire
when anything in that closure changes, so the closure is read off the build
itself rather than from a list kept by hand -- a list drifts, latexmk's own
records cannot.

Two records are needed and both are load-bearing:

    out/<stem>.fls           INPUT lines: what lualatex read, i.e. the \\input
                             children and any \\includegraphics
    out/<stem>.fdb_latexmk   per-rule sources: what latexmk tracked, including
                             references.bib, which never appears in .fls
                             because lualatex reads main.bbl, not the .bib

Only files git tracks survive the filter, so TeX Live paths and build products
under out/ drop out on their own.

Usage:
    python .github/scripts/closure.py docs                  # document ids
    python .github/scripts/closure.py list [DOC]            # closure, one path per line
    python .github/scripts/closure.py affected --base REF   # ids whose closure
                                                    # intersects REF...HEAD

Requires a build: run `latexmk <root>` first, or the record is missing and the
command fails rather than reporting an empty closure.

Run from the repository root.
"""
from __future__ import annotations

import argparse
import os
import pathlib
import subprocess
import sys

from docs import ROOT, load, root_of


def git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(ROOT), *args],
        capture_output=True, text=True, check=True,
    ).stdout


def tracked_files() -> set[str]:
    return {line for line in git("ls-files").splitlines() if line}


def fls_inputs(path: pathlib.Path) -> list[tuple[pathlib.Path, str]]:
    """(base, raw path) for every INPUT line. Paths are relative to PWD."""
    base = ROOT
    found = []
    for line in path.read_text(errors="replace").splitlines():
        if line.startswith("PWD "):
            base = pathlib.Path(line[4:].strip())
        elif line.startswith("INPUT "):
            found.append((base, line[6:].strip()))
    return found


def fdb_sources(path: pathlib.Path) -> list[tuple[pathlib.Path, str]]:
    """(base, raw path) for every source line of every rule.

    A rule opens with ["<rule>"] and is followed by indented quoted source
    lines until a (generated) or (rewritten before read) marker. Those trailing
    sections list the rule's *outputs* and must not be read as dependencies.
    """
    found = []
    in_sources = False
    for line in path.read_text(errors="replace").splitlines():
        if line.startswith('["'):
            in_sources = True          # the header line itself names the rule's
            continue                   # own source/dest, not its dependencies
        if not line.startswith("  "):
            in_sources = False
            continue
        body = line.strip()
        if body.startswith("("):
            in_sources = False
            continue
        if in_sources and body.startswith('"'):
            end = body.find('"', 1)
            if end > 1:
                found.append((ROOT, body[1:end]))
    return found


def to_repo_path(base: pathlib.Path, raw: str) -> str | None:
    """Repo-relative POSIX path, or None if the file lives outside the repo.

    Normalised lexically, never through the filesystem: Path.resolve() rewrites
    a name to its on-disk spelling, so a recorded name that differs from a
    tracked one only in case comes back as the tracked file and lands in the
    closure. That is how the bare "version" entry latexmk records under the
    lualatex rule used to pull in the repo's old VERSION file on Windows -- a
    different file, whose md5 did not even match. git is case-sensitive and CI
    is Linux, so matching must be too, or the closure depends on who built.
    """
    path = raw if os.path.isabs(raw) else os.path.join(str(base), raw)
    path = os.path.normpath(path)
    root = os.path.normpath(str(ROOT))
    prefix = os.path.normcase(root) + os.sep
    if not os.path.normcase(path).startswith(prefix):
        return None
    # normcase for containment only; the tail keeps the recorded spelling
    return pathlib.PurePath(path[len(root) + 1:]).as_posix()


def closure(doc_id: str, doc: dict, tracked: set[str]) -> set[str]:
    root = root_of(doc_id, {doc_id: doc})
    stem = pathlib.Path(root).stem
    fls = ROOT / "out" / f"{stem}.fls"
    fdb = ROOT / "out" / f"{stem}.fdb_latexmk"
    if not fls.exists() and not fdb.exists():
        sys.exit(
            f"{doc_id}: no build record under out/ (looked for {fls.name} and "
            f"{fdb.name}). Run `latexmk {root}` first."
        )

    raw: list[tuple[pathlib.Path, str]] = []
    if fls.exists():
        raw += fls_inputs(fls)
    if fdb.exists():
        raw += fdb_sources(fdb)

    found = {p for p in (to_repo_path(b, r) for b, r in raw) if p and p in tracked}
    if root in tracked:
        found.add(root)
    return found


def changed_files(base: str) -> set[str]:
    """Files changed on this branch since it diverged from base."""
    out = git("diff", "--name-only", f"{base}...HEAD")
    return {line for line in out.splitlines() if line}


def main() -> int:
    # newline="" means no translation on write, so lines end LF even on
    # Windows. print() would otherwise emit CRLF, and shell callers that
    # word-split this output would carry the carriage return into an
    # argument -- a document id then matches nothing in the manifest.
    sys.stdout.reconfigure(newline="")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("docs", help="print document ids")
    p_list = sub.add_parser("list", help="print the closure of a document")
    p_list.add_argument("doc", nargs="?", help="document id (default: all)")
    p_affected = sub.add_parser("affected", help="print ids touched since base")
    p_affected.add_argument("--base", required=True, help="base ref to compare against")
    args = parser.parse_args()

    docs = load()

    if args.command == "docs":
        for doc_id in docs:
            print(doc_id)
        return 0

    tracked = tracked_files()

    if args.command == "list":
        if args.doc is None:
            selected = docs
        elif args.doc in docs:
            selected = {args.doc: docs[args.doc]}
        else:
            sys.exit(f"unknown document '{args.doc}'; docs.toml has: {', '.join(docs)}")
        for doc_id, doc in selected.items():
            if len(selected) > 1:
                print(f"# {doc_id}")
            for path in sorted(closure(doc_id, doc, tracked)):
                print(path)
        return 0

    changed = changed_files(args.base)
    for doc_id, doc in docs.items():
        hits = closure(doc_id, doc, tracked) & changed
        if hits:
            print(doc_id)
            for path in sorted(hits):
                print(f"  {path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
