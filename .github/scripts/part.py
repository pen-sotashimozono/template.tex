#!/usr/bin/env python3
"""Compile only some sections of a document, for speed while writing.

    python3 .github/scripts/part.py notes 03-dmrg            # -> out/notes-part.pdf
    python3 .github/scripts/part.py notes 03-dmrg 04b-tdvp   # several
    python3 .github/scripts/part.py notes --list             # the sections there are

A section is a file the root pulls in with \\input on a line of its own. Those
named (any part of the path is enough) are compiled; the others are replaced
by an empty file. Neither the root nor a section is edited: the replacement is
LaTeX's own file substitution, passed in on the command line, and the result
goes to out/<stem>-part.pdf beside the full document, whose build files are
left alone.

What a part cannot know, it takes from the last full build (out/<stem>.aux):
references into the sections left out resolve to the numbers they have there,
and each compiled section starts at the section number it has there. Build
the full document once first; without it the part still compiles, numbered
from 1 and with ?? for what it cannot see.

It is a view for writing, not the document: page numbers, the table of
contents and the order of the bibliography are those of the part. Nothing
released is built this way.
"""
import argparse
import pathlib
import re
import subprocess
import sys

from docs import ROOT, load, root_of

INPUT = re.compile(r"^\s*\\input\{([^}]+)\}\s*(?:%.*)?$", re.M)
LABEL = re.compile(r"\\label\{([^}]+)\}")


def sections(root_tex: pathlib.Path) -> list[str]:
    """The files the root \\inputs on lines of their own, as TeX will name them (with .tex)."""
    found = []
    for name in INPUT.findall(root_tex.read_text(errors="replace")):
        path = name if name.endswith(".tex") else name + ".tex"
        if (ROOT / path).is_file() and path not in found:
            found.append(path)
    return found


def select(all_sections: list[str], patterns: list[str]) -> list[str]:
    chosen = []
    for pattern in patterns:
        hits = [s for s in all_sections if pattern in s]
        if not hits:
            sys.exit(f"no section matches '{pattern}'; there are:\n  " + "\n  ".join(all_sections))
        chosen += [h for h in hits if h not in chosen]
    return chosen


def section_numbers(aux: pathlib.Path) -> dict[str, int]:
    """label -> number, for the labels of top-level sections in the full build."""
    numbers = {}
    if aux.is_file():
        for label, number in re.findall(r"\\newlabel\{([^}]+)\}\{\{(\d+)\}", aux.read_text(errors="replace")):
            numbers[label] = int(number)
    return numbers


def pretex(all_sections: list[str], chosen: list[str], stem: str) -> str:
    out = pathlib.Path("out")
    numbers = section_numbers(ROOT / out / f"{stem}.aux")
    lines = ["\\makeatletter"]
    for path in all_sections:
        if path not in chosen:
            lines.append(f"\\declare@file@substitution{{{path}}}{{{out.as_posix()}/{stem}-part.skip.tex}}")
            continue
        # The first label of a section file is its \section's; where the full
        # build numbered it, start there.
        first = LABEL.search((ROOT / path).read_text(errors="replace"))
        if first and first[1] in numbers:
            # LaTeX names a file's hook by its name alone, without the directory.
            name = pathlib.PurePosixPath(path).name
            lines.append(f"\\AddToHook{{file/{name}/before}}{{\\setcounter{{section}}{{{numbers[first[1]] - 1}}}}}")
    if (ROOT / out / f"{stem}.aux").is_file():
        lines.append(f"\\AddToHook{{begindocument/before}}{{\\RequirePackage{{xr}}\\externaldocument{{{out.as_posix()}/{stem}}}}}")
    lines.append("\\makeatother")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("doc", help="document id in docs.toml")
    parser.add_argument("sections", nargs="*", help="part of the path of each section to compile")
    parser.add_argument("--list", action="store_true", help="print the sections and stop")
    args = parser.parse_args()

    docs = load()
    if args.doc not in docs:
        sys.exit(f"unknown document '{args.doc}'; docs.toml has: {', '.join(docs)}")
    root = root_of(args.doc, docs)
    stem = pathlib.Path(root).stem
    all_sections = sections(ROOT / root)
    if args.list or not args.sections:
        print("\n".join(all_sections) if all_sections else f"{root} pulls in no section with \\input")
        return 0 if args.list else 2
    chosen = select(all_sections, args.sections)

    out = ROOT / "out"
    out.mkdir(exist_ok=True)
    (out / f"{stem}-part.skip.tex").write_text("")
    pre = out / f"{stem}-part.pre.tex"
    pre.write_text(pretex(all_sections, chosen, stem))
    command = ["latexmk", f"-jobname={stem}-part", "-synctex=1",
               f"-usepretex=\\input{{out/{pre.name}}}", root]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        sys.stderr.write(result.stdout[-3000:] + result.stderr[-1000:])
        return result.returncode
    print(f"out/{stem}-part.pdf  ({', '.join(chosen)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
