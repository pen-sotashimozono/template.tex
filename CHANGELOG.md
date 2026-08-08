# Changelog

One entry per released version, newest first. The PR that bumps `VERSION`
adds its entry here, so the history is readable in-repo without downloading
release artifacts. `./scripts/bump.sh <kind> "summary"` prepends the stub.

To see what actually changed in the paper between two versions:

```sh
git diff v0.1.2 v0.1.3 -- '*.tex'     # text, greppable — prefer this
./scripts/diff.sh v0.1.2 v0.1.3       # rendered latexdiff PDF, for reading
```

<!-- new entries go directly below this line -->

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
