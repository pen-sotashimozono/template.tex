#!/usr/bin/env python3
"""The document manifest: docs.toml, and the version ladder it carries.

One table per compiled PDF. The table name is the document id, and everything
mechanical is derived from it -- root file, build output, release tag:

    [main]  ->  main.tex  ->  out/main.pdf  ->  main-v0.1.0

so adding a document means adding a table with a version, and no workflow has
to be told about it separately. `root` overrides the default when the file is
not <id>.tex. A table is a document iff it carries `version`.

This file is the only version authority in the repository. There is no VERSION
file: it held the same number as this manifest and nothing reconciled the two.

Writes rewrite a single `version = "..."` line in place rather than going
through a TOML dumper. A dumper reformats the whole file and drops every
comment, and docs.toml is meant to stay readable by hand.

Usage:
    python scripts/docs.py ids [--json] [--file F]      # document ids
    python scripts/docs.py root <id>                    # root .tex path
    python scripts/docs.py version <id>                 # current version
    python scripts/docs.py tag <id>                     # <id>-v<version>
    python scripts/docs.py next <id> <patch|minor|major>
    python scripts/docs.py bump <id> <patch|minor|major>
    python scripts/docs.py init <version>               # every version -> X
    python scripts/docs.py check-bump --base <file> [--only ID ...]

Run from anywhere; paths resolve against the repository root.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import tomllib

ROOT = pathlib.Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "docs.toml"

SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
TABLE_LINE = re.compile(r"^\s*\[([^\[\]]+)\]")
VERSION_LINE = re.compile(r"""^(\s*version\s*=\s*)(["'])([^"']*)\2(.*)$""")


def load(path: pathlib.Path = MANIFEST) -> dict[str, dict]:
    """Document tables only -- anything without `version` is configuration."""
    with path.open("rb") as fh:
        data = tomllib.load(fh)
    return {
        name: table
        for name, table in data.items()
        if isinstance(table, dict) and "version" in table
    }


def root_of(doc_id: str, docs: dict[str, dict]) -> str:
    return docs[doc_id].get("root", f"{doc_id}.tex")


def parse(version: str, where: str) -> tuple[int, int, int]:
    m = SEMVER.match(version.strip())
    if not m:
        sys.exit(f"{where}: version '{version}' is not in X.Y.Z form")
    return int(m[1]), int(m[2]), int(m[3])


def next_version(version: str, kind: str, where: str) -> str:
    major, minor, patch = parse(version, where)
    if kind == "patch":
        return f"{major}.{minor}.{patch + 1}"
    if kind == "minor":
        return f"{major}.{minor + 1}.0"
    if kind == "major":
        return f"{major + 1}.0.0"
    sys.exit(f"unknown bump kind '{kind}'; expected patch, minor or major")


def write_version(doc_ids: list[str], new: str, path: pathlib.Path = MANIFEST) -> None:
    """Rewrite the `version` line of each named table, comments untouched."""
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    current: str | None = None
    written: set[str] = set()
    for i, line in enumerate(lines):
        table = TABLE_LINE.match(line)
        if table:
            current = table[1].strip()
            continue
        if current not in doc_ids:
            continue
        m = VERSION_LINE.match(line)
        if m:
            eol = "\n" if line.endswith("\n") else ""
            lines[i] = f"{m[1]}{m[2]}{new}{m[2]}{m[4].rstrip()}{eol}"
            written.add(current)
    missing = [d for d in doc_ids if d not in written]
    if missing:
        sys.exit(f"no version line found for: {', '.join(missing)}")
    path.write_text("".join(lines), encoding="utf-8")


def check_bump(base_path: pathlib.Path, only: list[str] | None) -> int:
    """Compare head versions against the base branch's.

    `only` names the documents that MUST bump; every other document must stay
    put. Omitting it requires all of them to bump. Passing it empty requires
    none -- a PR that touches no document's closure, such as a CI or README
    change, is then free of the ladder entirely.
    """
    head = load()
    base = load(base_path)
    required = set(head) if only is None else set(only)

    unknown = required - set(head)
    if unknown:
        sys.exit(f"unknown document(s): {', '.join(sorted(unknown))}")

    errors: list[str] = []
    for doc_id, table in head.items():
        new = table["version"]
        parse(new, doc_id)

        if doc_id not in base:
            print(f"{doc_id}: new document at {new} -- no base version to step from. OK")
            continue

        old = base[doc_id]["version"]
        parse(old, f"{doc_id} (base)")
        steps = {kind: next_version(old, kind, doc_id) for kind in ("patch", "minor", "major")}
        allowed = ", ".join(f"{v} ({k})" for k, v in steps.items())

        if doc_id not in required:
            if new != old:
                errors.append(
                    f"{doc_id}: version moved {old} -> {new}, but this PR does not "
                    f"touch its dependency closure. Put it back to {old}."
                )
            else:
                print(f"{doc_id}: untouched at {old}. OK")
            continue

        if new == old:
            errors.append(
                f"{doc_id}: version is unchanged at {old}. Run "
                f"'./scripts/bump.sh {doc_id} patch' and commit. Allowed: {allowed}."
            )
        elif new not in steps.values():
            errors.append(
                f"{doc_id}: {old} -> {new} is not a single semver step from the "
                f"current tip of the base branch. Allowed: {allowed}. If another "
                f"PR merged first, merge it in and re-bump."
            )
        else:
            kind = next(k for k, v in steps.items() if v == new)
            print(f"{doc_id}: valid {kind} bump {old} -> {new}. Release {doc_id}-v{new} on merge.")

    for gone in sorted(set(base) - set(head)):
        print(f"{gone}: removed from docs.toml. OK")

    for message in errors:
        print(f"::error::{message}")
    return 1 if errors else 0


def main() -> int:
    # newline="" means no translation on write, so lines end LF even on
    # Windows. print() would otherwise emit CRLF, and shell callers that
    # word-split this output would carry the carriage return into an
    # argument -- a document id then matches nothing in the manifest.
    sys.stdout.reconfigure(newline="")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p_ids = sub.add_parser("ids", help="print document ids")
    p_ids.add_argument("--json", action="store_true", help="as a JSON array, for an Actions matrix")
    p_ids.add_argument("--file", type=pathlib.Path, default=MANIFEST, help="read another manifest")
    for name, help_text in (
        ("root", "print a document's root .tex"),
        ("version", "print a document's version"),
        ("tag", "print a document's release tag"),
    ):
        sub.add_parser(name, help=help_text).add_argument("doc")
    for name, help_text in (
        ("next", "print the version one step up, without writing"),
        ("bump", "raise a document's version by one step"),
    ):
        p = sub.add_parser(name, help=help_text)
        p.add_argument("doc")
        p.add_argument("kind", choices=["patch", "minor", "major"], nargs="?", default="patch")
    sub.add_parser("init", help="set every document to one version").add_argument("version")
    p_check = sub.add_parser("check-bump", help="validate the ladder against a base manifest")
    p_check.add_argument("--base", required=True, type=pathlib.Path)
    p_check.add_argument("--only", nargs="*", default=None, metavar="ID")
    args = parser.parse_args()

    if args.command == "check-bump":
        return check_bump(args.base, args.only)

    docs = load(args.file) if args.command == "ids" else load()
    if args.command == "ids":
        print(json.dumps(list(docs)) if args.json else "\n".join(docs))
        return 0
    if args.command == "init":
        parse(args.version, "init")
        write_version(list(docs), args.version)
        print(f"docs.toml: {', '.join(docs)} -> {args.version}")
        return 0

    if args.doc not in docs:
        sys.exit(f"unknown document '{args.doc}'; docs.toml has: {', '.join(docs) or '(none)'}")

    if args.command == "root":
        print(root_of(args.doc, docs))
    elif args.command == "version":
        print(docs[args.doc]["version"])
    elif args.command == "tag":
        print(f"{args.doc}-v{docs[args.doc]['version']}")
    elif args.command == "next":
        print(next_version(docs[args.doc]["version"], args.kind, args.doc))
    elif args.command == "bump":
        old = docs[args.doc]["version"]
        new = next_version(old, args.kind, args.doc)
        write_version([args.doc], new)
        print(f"{args.doc}: {old} -> {new} ({args.kind})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
