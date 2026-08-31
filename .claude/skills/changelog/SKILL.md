---
name: changelog
description: Record a change in .github/CHANGELOG.md and bump the versions of the documents it touched. Use before opening a PR, whenever any .tex file, references.bib, or a figure has changed - CI rejects a PR whose affected documents are not bumped, and rejects one that bumps a document it did not touch.
---

# Recording a change

Every merged PR releases the documents it changed. The changelog entry written
here becomes that release's body, so it is the only place the reason for a
change survives as prose - the commit log carries what changed, not why.

## The command

```sh
latexmk main.tex && latexmk notes.tex
./.github/scripts/bump.sh --affected patch "One line on what changed and why."
```

`--affected` asks `closure.py` which documents this branch actually changed,
through their `\input` children and `references.bib` rather than the root file
alone, and bumps exactly those. It writes one changelog stub per document,
headed by the tag that document will release under.

Use `minor` or `major` in place of `patch` when the change deserves it. Name a
document explicitly - `./.github/scripts/bump.sh notes patch "..."` - only when
`--affected` gets it wrong.

## Two preconditions, both easy to miss

**Build first.** `--affected` reads the build records under `out/`. Without
them it cannot compute a closure and will refuse rather than guess.

**Commit the content first.** The comparison is `git diff main...HEAD`, which
sees commits, not the working tree. Running this before committing the actual
changes reports nothing affected and bumps nothing.

So the order is: commit the writing, then bump, then commit the bump.

## Writing the entry

The summary argument becomes the entry body. Without one, a `TODO` is left in
place and has to be filled in before the PR - a released version whose entry
says TODO is worse than one with no entry, because it looks answered.

Say what changed and why it changed. "Rewrote section 3" is what the diff
already shows; "Section 3 conflated the two limits, which made the bound look
tighter than it is" is not.

## What CI checks

The `version-check` job in `latex-ci.yml` requires a single semver step for
every document whose closure the PR touched, and **forbids** a bump for the
documents it did not touch. A PR that changes only CI, the README, or tooling
needs no bump at all - do not invent one.

The comparison is against the current tip of `main`, not the state at PR
creation. If another PR merges first, merge `main` in and re-run the bump.

## Adding a new document

A document that does not yet exist on `main` is new: the check accepts whatever
version it arrives with, and `--affected` deliberately skips it. Set its
starting version by hand in `.github/docs.toml` and write its changelog entry
by hand, headed by the tag it will release under.
