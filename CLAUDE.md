# Working rules for this repository

Two root documents: `main.tex` (paper, revtex4-2 two-column PRB) and
`notes.tex` (working notebook, article). They share `references.bib`; `refs/`
holds the PDF of every cited work.

`.github/docs.toml` is the only version authority. The table name is the
document id, and the rest follows from it:

    [main]  ->  main.tex  ->  out/main.pdf  ->  tag main-v0.0.11

A third document is one table; the CI matrix, tags and releases pick it up
unchanged.

Each root carries its own complete preamble rather than sharing one, so either
ships alone — at the cost that shared markup must be edited twice, and nothing
catches a miss.

## Layout

The root holds the documents; everything that runs them is under `.github/`,
skills under `.claude/`. Three files cannot move: `.latexmkrc` (latexmk reads an
rc only from the working directory), `CLAUDE.md` (Claude Code reads it only from
the root), `LICENSE` (GitHub detects a licence only at the root). `README.md`
*does* resolve from `.github/`.

| Path | Contents |
|---|---|
| `main.tex`, `notes.tex` | the documents; children pulled in with `\input` |
| `references.bib` | bibliography — from `doiget cite`, never hand-written |
| `refs/`, `refs/src/` | one PDF per bibkey; full text for grepping |
| `figures/`, `notes/` | figures (PDF only); children of `notes.tex` |
| `.github/docs.toml` | root documents and versions |
| `.github/CHANGELOG.md` | one entry per version, headed by its tag |
| `.github/scripts/` | `bump.sh`, `docs.py`, `closure.py`, `diff.sh`, `arxiv_bundle.sh`, `refs_sync.sh`, `fetch_sources.sh` |
| `.claude/skills/` | `changelog` (record a change and bump), `references` (doiget) |
| `out/` | build output (gitignored) |

`latexmk main.tex` → `out/main.pdf`, `latexmk notes.tex` → `out/notes.pdf`. One
`.latexmkrc` serves both; the stems differ so nothing collides.

Before editing either preamble: **revtex4-2 bundles its own `natbib`**, so only
`notes.tex` loads it. `\affiliation`, `\email` and `acknowledgments` are
revtex-only, so `notes.tex` reimplements them — that is what lets the same
markup compile under either class.

## Versions — bump what the PR touched, and only that

```sh
./.github/scripts/bump.sh --affected patch "One line on what changed and why."
git add .github/docs.toml .github/CHANGELOG.md
```

`--affected` asks `closure.py` which documents actually changed, through their
`\input` children and `references.bib`. **Build first** (it reads `out/`) and
**commit the content first** (it compares commits, not the working tree). A
document not yet on `main` is new: any version is accepted and `--affected`
skips it. The **`changelog` skill** carries this.

Two checks, split on purpose:

| Check | Rule | Build |
|---|---|---|
| **Validate semver step** (`VersionCheck.yml`) | unchanged or exactly one step | no |
| **Validate semver bump** (`latex-ci.yml`) | the right documents moved, and only those | yes |

The first is a subset, kept separate because it answers in seconds and still
runs when a build fails — when the second cannot run at all. Neither is a
required check; the merge button is the gate.

A PR touching no document needs no bump and ships no release. One that bumps a
document releases it on merge: `{tag}.pdf`, `diff-{tag}.pdf` (against that
document's own previous tag) and the arXiv bundle.

Comparison is against the **current tip of `main`**. When two PRs touch the
*same* document, only the next in its queue is green; take `main` in (a
base-branch update alone does not re-trigger checks), resolve the
`.github/docs.toml` conflict by keeping your higher value, and re-bump. PRs on
different documents do not collide.

## The submission bundle must compile alone

`arxiv_bundle.sh` flattens a document with `latexpand`, adds its `.bbl` and
figures, and compiles the result in isolation. CI runs it per document per PR.
It is the only check that a document is self-contained: an unflattened bundle
fails on arXiv while every build here stays green.

Two things break it quietly: `latexpand` reads inside `\verb`, so an `\input`
written as an *example* is treated as real — write around it; and a file git
does not track never reaches the tarball.

## References — always through doiget

`VerifyReferences.yml` resolves every DOI / arXiv id in `references.bib` against
Crossref and arXiv when that file changes.

```sh
doiget cite <doi|arxiv-id>           # BibTeX; paste in verbatim, rename the key
./.github/scripts/refs_sync.sh       # every entry gets refs/<bibkey>.pdf
./.github/scripts/fetch_sources.sh   # and refs/src/<bibkey>.tex or .txt
```

The **`references` skill** carries this, including pinning `DOIGET_STORE_ROOT`
— the store defaults to `./papers` under the cwd, so doiget run from a paper
repository builds a second store inside it.

`refs/src/` makes checking a citation cheap — prefer it to opening the PDF:

```sh
grep -n 'F_Q' refs/src/hauke2016measuring.tex     # the inequality in source form
grep -l 'structure factor' refs/src/*.tex          # which references discuss it
grep -o '\\cite{[^}]*}' refs/src/<key>.tex         # what that paper cites
```

arXiv LaTeX source beats PDF extraction: equations keep their structure,
`\label{...}` is stable across arXiv and published versions (whose equation
*numbers* differ), and nothing is silently dropped — extraction routinely loses
Greek letters.

- **Never invent or guess a DOI.** A plausible one usually resolves to a
  *different, real* paper, which is worse than a broken link.
- **A resolving DOI is not proof the citation is right.** Check the title and
  authors, then read the PDF to confirm it supports your claim.
- Keep `refs/<bibkey>.pdf` in sync with the key in `references.bib`.
- Some works have no OA PDF; `doiget fetch` stores metadata only. Cite normally
  and note the absence.

`strict` is `"false"`: unresolvable entries warn. Set `"true"` to block.

## Before opening a PR

1. `latexmk main.tex` and `latexmk notes.tex` both build clean.
2. `bump.sh --affected patch` committed — or nothing, if no document changed.
3. New citations came from `doiget`, with their PDFs in `refs/`.
4. `git diff --cached HEAD --stat` — read the **whole** list and confirm nothing
   unintended was swept in by `git add -A`.
