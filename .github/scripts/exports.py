#!/usr/bin/env python3
"""Exports: documents whose source is a pptx / docx, built to PDF by LibreOffice.

    [review]
    source = "slides/main.pptx"   ->  out/review.pdf
    version = "0.1.0"             ->  release v0.1.0-review (source + PDF)

Same version ladder as the LaTeX documents. CI builds the PDF on every PR and
on release; the version must move exactly when the source did.

Usage:
    python .github/scripts/exports.py ids [--json]
    python .github/scripts/exports.py source <id>
    python .github/scripts/exports.py build <id> [--outdir out]   # needs soffice
    python .github/scripts/exports.py affected --base REF
    python .github/scripts/exports.py check-bump --base FILE --base-ref REF

Run from anywhere; paths resolve against the repository root.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

from docs import HERE, MANIFEST, ROOT, kind_of, load_all, next_version, parse


def load(path: pathlib.Path = MANIFEST) -> dict[str, dict]:
    return {name: t for name, t in load_all(path).items() if kind_of(name, t) == "export"}


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True)


def changed_files(base: str) -> set[str]:
    """Files changed since base, as closure.py measures it."""
    out = git("diff", "--name-only", f"{base}...HEAD")
    if out.returncode:
        sys.exit(f"git diff {base}...HEAD failed: {out.stderr.strip()}")
    return {line for line in out.stdout.splitlines() if line}


def affected(exports: dict[str, dict], base: str) -> list[str]:
    changed = changed_files(base)
    return [d for d, t in exports.items() if t["source"] in changed]


def build(doc_id: str, table: dict, outdir: pathlib.Path) -> pathlib.Path:
    source = ROOT / table["source"]
    if not source.exists():
        sys.exit(f"{doc_id}: {table['source']} does not exist")
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        sys.exit("soffice not found; install LibreOffice (CI does)")
    outdir.mkdir(parents=True, exist_ok=True)
    target = outdir / f"{doc_id}.pdf"
    python = uno_python()
    if python:
        subprocess.run([python, str(HERE / "soffice_pdf.py"), str(source), str(target)],
                       check=True)
    else:
        print(f"{doc_id}: no python3-uno; plain conversion, mixed Japanese/Latin lines "
              "may space wider than in PowerPoint", file=sys.stderr)
        # soffice names the PDF after the source; convert in a scratch dir so
        # two exports with the same stem cannot collide.
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run([soffice, "--headless", "--convert-to", "pdf", "--outdir", tmp,
                            str(source)], check=True)
            shutil.move(pathlib.Path(tmp) / f"{source.stem}.pdf", target)
    if not target.exists():
        sys.exit(f"{doc_id}: LibreOffice produced no PDF")
    print(f"{doc_id}: {table['source']} -> {target}")
    return target


def uno_python() -> str | None:
    """An interpreter that can import LibreOffice's uno module, if any."""
    for python in dict.fromkeys([sys.executable, "/usr/bin/python3"]):
        if pathlib.Path(python).exists() and subprocess.run(
                [python, "-c", "import uno"], capture_output=True).returncode == 0:
            return python
    return None


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
        # The base table's own source: a renamed source is a change, not a first one.
        if git("cat-file", "-e", f"{base_ref}:{base[doc_id]['source']}").returncode != 0:
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
    sub.add_parser("source", help="print an export's source path").add_argument("doc")
    p_build = sub.add_parser("build", help="convert an export's source to PDF")
    p_build.add_argument("doc")
    p_build.add_argument("--outdir", type=pathlib.Path, default=ROOT / "out")
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

    if args.doc not in exports:
        sys.exit(f"unknown export '{args.doc}'; docs.toml has: {', '.join(exports) or '(none)'}")
    table = exports[args.doc]
    if args.command == "source":
        print(table["source"])
    elif args.command == "build":
        build(args.doc, table, args.outdir.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
