---
name: changelog
description: Record a change in .github/CHANGELOG.md and bump the documents it touched. Use before opening a PR whenever a .tex file, references.bib or a figure changed - CI rejects a PR whose affected documents are not bumped, and one that bumps a document it did not touch.
---

# Recording a change

Every merged PR releases the documents it changed, and this entry becomes that
release's body. It is the only place the *reason* survives as prose; the commit
log carries what changed, not why.

```sh
latexmk main.tex && latexmk notes.tex
./.github/scripts/bump.sh --affected patch "One line on what changed and why."
```

`--affected` asks `closure.py` which documents actually changed, through their
`\input` children and `references.bib`, and bumps exactly those — one changelog
stub each, headed by the tag it will release under. Use `minor` or `major` where
deserved; name a document explicitly only when `--affected` gets it wrong.

## Two preconditions, both easy to miss

- **Build first.** `--affected` reads the build records under `out/`.
- **Commit the content first.** It compares `git diff main...HEAD` — commits,
  not the working tree. Run it before committing and it finds nothing.

So: commit the writing, bump, commit the bump.

## The summary

Without one, a `TODO` is left behind — worse than no entry, because it looks
answered.

Say why, not what. "Rewrote section 3" is what the diff already shows; "section
3 conflated the two limits, which made the bound look tighter than it is" is
not.

## What CI checks

`Validate semver bump` requires a single step for every document whose closure
the PR touched, and **forbids** a bump for the ones it did not — a PR changing
only CI, the README or tooling needs none. `Validate semver step` separately
rejects anything that is not unchanged-or-one-step.

Comparison is against the current tip of `main`; if another PR merged first,
merge `main` in and re-bump.

## A new document

One not yet on `main` is new: any starting version is accepted, and `--affected`
skips it deliberately. Set its version in `.github/docs.toml` and write its
changelog entry by hand, headed by the tag it will release under.
