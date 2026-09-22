#!/usr/bin/env python3
"""Exports: documents whose source is a pptx / docx, with a PDF exported by hand.

    [review]
    source = "slides/review.pptx"   ->  slides/review.pdf + .pdf.sha256
    version = "0.1.0"               ->  release v0.1.0-review

Same version ladder as the LaTeX documents, but never built (headless
converters break the Japanese layout). CI checks that the PDF's stamp matches
the source, and that the version moved exactly when the source did.

Usage:
    python .github/scripts/exports.py ids [--json]
    python .github/scripts/exports.py paths <id>          # source, pdf, stamp
    python .github/scripts/exports.py stamp <id>          # record the source hash
    python .github/scripts/exports.py check [--strict] [ID ...]
    python .github/scripts/exports.py affected --base REF
    python .github/scripts/exports.py check-bump --base FILE --base-ref REF

Run from anywhere; paths resolve against the repository root.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import subprocess
import sys

from docs import MANIFEST, ROOT, kind_of, load_all, next_version, parse


def load(path: pathlib.Path = MANIFEST) -> dict[str, dict]:
    return {name: t for name, t in load_all(path).items() if kind_of(name, t) == "export"}


def paths(table: dict) -> tuple[pathlib.Path, pathlib.Path, pathlib.Path]:
    source = ROOT / table["source"]
    pdf = source.with_suffix(".pdf")
    return source, pdf, pdf.with_name(pdf.name + ".sha256")


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: pathlib.Path) -> str:
    return str(path.relative_to(ROOT))


def changed_files(base: str) -> set[str]:
    """Files changed since base, as closure.py measures it."""
    out = subprocess.run(["git", "-C", str(ROOT), "diff", "--name-only", f"{base}...HEAD"],
                         capture_output=True, text=True, check=True).stdout
    return {line for line in out.splitlines() if line}


def exists_at(ref: str, path: str) -> bool:
    return subprocess.run(["git", "-C", str(ROOT), "cat-file", "-e", f"{ref}:{path}"],
                          capture_output=True).returncode == 0


def affected(exports: dict[str, dict], base: str) -> list[str]:
    changed = changed_files(base)
    return [d for d, t in exports.items() if t["source"] in changed]


def check(exports: dict[str, dict], strict: bool) -> int:
    """The PDF was exported from the committed source. A missing source
    passes unless `strict`."""
    errors: list[str] = []
    fix = "run ./.github/scripts/office2pdf.sh {} and commit the PDF and its stamp"
    for doc_id, table in exports.items():
        source, pdf, stamp = paths(table)
        if not source.exists():
            if strict:
                errors.append(f"{doc_id}: {rel(source)} does not exist")
            elif pdf.exists():
                errors.append(f"{doc_id}: {rel(pdf)} is committed but {rel(source)} is not")
            else:
                print(f"{doc_id}: no {rel(source)} yet. OK")
            continue
        if not pdf.exists() or not stamp.exists():
            errors.append(f"{doc_id}: {rel(source)} has no exported PDF; {fix.format(doc_id)}")
            continue
        recorded = stamp.read_text(encoding="utf-8").split()[0] if stamp.stat().st_size else ""
        if recorded != sha256(source):
            errors.append(f"{doc_id}: {rel(pdf)} was exported from a different "
                          f"{rel(source)}; {fix.format(doc_id)}")
            continue
        print(f"{doc_id}: {rel(pdf)} matches {rel(source)}. OK")
    for message in errors:
        print(f"::error::{message}")
    return 1 if errors else 0


def check_bump(base_manifest: pathlib.Path, base_ref: str) -> int:
    """The version moved exactly when the source did. A first source ships
    at the version already in the table."""
    head = load()
    base = load(base_manifest)
    touched = set(affected(head, base_ref))
    errors: list[str] = []
    for doc_id, table in head.items():
        new = table["version"]
        if doc_id not in base:
            print(f"{doc_id}: new export at {new}. OK")
            continue
        if not exists_at(base_ref, table["source"]):
            print(f"{doc_id}: first source for this export, at {new}. OK")
            continue
        old = base[doc_id]["version"]
        parse(new, doc_id)
        if doc_id in touched and new == old:
            errors.append(f"{doc_id}: {table['source']} changed but the version is still "
                          f"{old}. Run './.github/scripts/bump.sh {doc_id} patch' "
                          f"(next: {next_version(old, 'patch', doc_id)}) and commit.")
        elif doc_id not in touched and new != old:
            errors.append(f"{doc_id}: version moved {old} -> {new}, but {table['source']} "
                          f"did not change. Put it back to {old}.")
        elif doc_id in touched:
            print(f"{doc_id}: source changed, {old} -> {new}. Release v{new}-{doc_id} on merge.")
        else:
            print(f"{doc_id}: untouched at {old}. OK")
    for message in errors:
        print(f"::error::{message}")
    return 1 if errors else 0


def main() -> int:
    sys.stdout.reconfigure(newline="")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("ids", help="print export ids").add_argument("--json", action="store_true")
    for name in ("paths", "stamp"):
        sub.add_parser(name).add_argument("doc")
    p_check = sub.add_parser("check", help="every PDF was exported from its source")
    p_check.add_argument("--strict", action="store_true", help="a missing source is an error")
    p_check.add_argument("docs", nargs="*", metavar="ID")
    sub.add_parser("affected", help="exports whose source changed since base").add_argument(
        "--base", required=True)
    p_bump = sub.add_parser("check-bump", help="versions moved exactly where sources did")
    p_bump.add_argument("--base", required=True, type=pathlib.Path, help="base docs.toml")
    p_bump.add_argument("--base-ref", required=True, help="base commit to diff against")
    args = parser.parse_args()

    if args.command == "check-bump":
        return check_bump(args.base, args.base_ref)
    exports = load()
    if args.command == "ids":
        print(json.dumps(list(exports)) if args.json else "\n".join(exports))
        return 0
    if args.command == "affected":
        print("\n".join(affected(exports, args.base)))
        return 0
    if args.command == "check":
        unknown = [d for d in args.docs if d not in exports]
        if unknown:
            sys.exit(f"unknown export(s): {', '.join(unknown)}")
        return check({d: exports[d] for d in args.docs} if args.docs else exports, args.strict)

    if args.doc not in exports:
        sys.exit(f"unknown export '{args.doc}'; docs.toml has: {', '.join(exports) or '(none)'}")
    table = exports[args.doc]
    if args.command == "paths":
        print("\n".join(str(p) for p in paths(table)))
    elif args.command == "stamp":
        source, _, stamp = paths(table)
        stamp.write_text(f"{sha256(source)}  {source.name}\n", encoding="utf-8")
        print(f"{args.doc}: stamped {rel(stamp)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
