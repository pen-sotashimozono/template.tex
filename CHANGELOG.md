# Changelog

One entry per released version, newest first, headed by the tag it ships
under. Each document in `docs.toml` has its own ladder, so entries interleave:
`main-v0.1.4` may sit above `notes-v0.3.0`. The PR that bumps a version adds
its entry here, so the history is readable in-repo without downloading release
artifacts. `./scripts/bump.sh <document> <kind> "summary"` prepends the stub.

To see what actually changed in a document between two of its versions:

```sh
git diff main-v0.1.2 main-v0.1.3 -- '*.tex'     # text, greppable — prefer this
./scripts/diff.sh main-v0.1.2 main-v0.1.3       # rendered latexdiff PDF, for reading
```

Entries below `0.0.10` predate per-document tags and are headed by a bare
version; they belong to `main`.

<!-- new entries go directly below this line -->

## main-v0.0.11 — 2026-08-31

docs.toml is now the only version authority; VERSION is gone and tags are per document.

## 0.0.10 — 2026-08-14

Add `docs.toml` and `scripts/closure.py`: each root document's dependency
closure is now derived from its own build records (`out/<stem>.fls` and
`out/<stem>.fdb_latexmk`), so version checks and releases can key off the
`\input` children and `references.bib` rather than the root file alone.
Nothing gates on it yet; `latex-ci.yml` only prints the closure.

## 0.0.9 — 2026-08-09

Local diff rendering (`scripts/diff.sh`), a reference full-text corpus
(`scripts/fetch_sources.sh` → `refs/src/`), this changelog, and release notes
generated from the commit log. Fixes the release latexdiff, which compared
`main.tex` only and therefore showed nothing when the change lived in an
`\input` child.

## 0.0.8 — 2026-08-09

`CLAUDE.md` with the working rules, `refs/.keep`, and a fix to the placeholder
bibliography entry, which paired fabricated author/title metadata with a real
DOI belonging to an unrelated paper.

## 0.0.7 — 2026-08-09

Version Check made strict: every PR must bump `VERSION` by exactly one semver
step. Adds `scripts/bump.sh`.
