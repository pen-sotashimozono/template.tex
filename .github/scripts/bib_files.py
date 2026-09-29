#!/usr/bin/env python3
"""Keep a `file` field on each references.bib entry pointing at its local PDF.

    python3 .github/scripts/bib_files.py [references.bib] [--check]

An entry whose refs/<bibkey>.pdf exists gets `file = {refs/<bibkey>.pdf}`;
one without loses the field. So the bibliography itself says where every
original is, and a reference manager (JabRef, BibDesk) opens it from there.
bibtex ignores the field, so the notes are unaffected.

The field is derived, never typed: refs_sync.sh runs this after copying
PDFs, and --check (for CI) exits 1 when a field is stale. Everything else
in an entry -- what doiget cite wrote -- is left byte for byte.
"""
import pathlib
import re
import sys

ENTRY = re.compile(r"^@\w+\{([^,\s]+),\n(.*?)^\}", re.M | re.S)
FILE_LINE = re.compile(r"^  file\s*=\s*\{[^}]*\},?\n", re.M)


def with_files(text: str, root: pathlib.Path) -> str:
    def fix(m: re.Match) -> str:
        key, body = m.group(1), FILE_LINE.sub("", m.group(2))
        if (root / "refs" / f"{key}.pdf").is_file():
            if body and not body.rstrip("\n").endswith(","):
                body = body.rstrip("\n") + ",\n"
            body += f"  file       = {{refs/{key}.pdf}},\n"
        return m.group(0)[: m.start(2) - m.start(0)] + body + "}"
    return ENTRY.sub(fix, text)


def main(argv: list) -> int:
    check = "--check" in argv
    args = [a for a in argv if a != "--check"]
    bib = pathlib.Path(args[0]) if args else pathlib.Path(__file__).resolve().parents[2] / "references.bib"
    root = bib.resolve().parent
    old = bib.read_text()
    new = with_files(old, root)
    if new == old:
        return 0
    if check:
        print(f"{bib}: file fields out of date; run .github/scripts/bib_files.py", file=sys.stderr)
        return 1
    bib.write_text(new)
    print(f"{bib}: file fields updated")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
