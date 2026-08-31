# Changelog

One entry per released version, newest first, headed by the tag it ships
under. Each document in `docs.toml` has its own ladder, so entries interleave:
`v0.1.4-main` may sit above `v0.3.0-notes`. The PR that bumps a version adds
its entry here, so the history is readable in-repo without downloading release
artifacts. `./.github/scripts/bump.sh <document> <kind> "summary"` prepends the
stub; the `changelog` skill carries the whole procedure.

To see what actually changed in a document between two of its versions:

```sh
git diff v0.1.2-main v0.1.3-main -- '*.tex'     # text, greppable — prefer this
./.github/scripts/diff.sh v0.1.2-main v0.1.3-main   # rendered latexdiff PDF
```

Entries above are headed `v<version>-<document>`. Those between `main-v0.0.11`
and `notes-v0.0.12` shipped under `<document>-v<version>`, and entries below
`0.0.10` predate per-document tags entirely and belong to `main`. Each is left
under the name it actually released with. Paths quoted inside older entries are the paths
of their time -- `scripts/` and `docs.toml` moved under `.github/` later, and
those entries are left as written rather than rewritten to match.

<!-- new entries go directly below this line -->

## notes-v0.0.12 — 2026-08-31

Add a references skill and refs_sync.sh, so references.bib drives refs/ from the doiget store.

## main-v0.0.12 — 2026-08-31

Add a references skill and refs_sync.sh, so references.bib drives refs/ from the doiget store.

## notes-v0.0.11 — 2026-08-31

First release of the working notebook: article class, one column, self-contained
preamble, sharing only `references.bib` with the paper.

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
