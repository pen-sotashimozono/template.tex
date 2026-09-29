# Working rules for this repository

Two root documents: `main.tex` (paper, revtex4-2 two-column PRB) and
`notes.tex` (working notebook, article). They share `references.bib`; `papers/`
holds the PDF of every cited work.

`docs.toml` is the only version authority. The table name is the
document id, and the rest follows from it:

    [main]  ->  main.tex  ->  out/main.pdf  ->  tag v0.0.11-main

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
| `docs.toml` | root documents and versions — the version authority |
| `papers/`, `papers/src/` | one PDF per bibkey; full text for grepping |
| `figures/` | the documents' own figures (PDF) at the top; figure pages in `src/<topic>/`, built into `assets/<topic>/` (SVG, and PDF with `--pdf`); cited papers' own figures as `papers/<bibkey>-fig<N>.svg` — see below |
| `notes/` | children of `notes.tex` |
| `slides/` (or anywhere) | pptx / docx exports, built to PDF in CI |
| `.github/CHANGELOG.md` | one entry per version, headed by its tag |
| `.github/scripts/` | `bump.sh`, `docs.py`, `closure.py`, `diff.sh`, `arxiv_bundle.sh`, `refs_sync.sh`, `fetch_sources.sh`, `bib_files.py`, `exports.py`, `soffice_pdf.py` |
| `.github/tools/figures/` | what runs the figure pages, never read while writing: `build.sh`, `latexmkrc`, `preamble.tex`, `paper_figures.py`, and `tikz-tensors/` (the TikZ format and theme, a git submodule pinned by `tikz-tensors.sh`) |
| `.claude/skills/` | `changelog` (record a change and bump), `references` (doiget), `figure-pages` (an equation, tensor diagram or drawing), `paper-figures` (a cited paper's own figure) |
| `out/` | build output (gitignored) |

`latexmk main.tex` → `out/main.pdf`, `latexmk notes.tex` → `out/notes.pdf`. One
`.latexmkrc` serves both; the stems differ so nothing collides.

Before editing either preamble: **revtex4-2 bundles its own `natbib`**, so only
`notes.tex` loads it. `\affiliation`, `\email` and `acknowledgments` are
revtex-only, so `notes.tex` reimplements them — that is what lets the same
markup compile under either class.

## Figures: pages in `figures/src/`, tools in `.github/tools/figures/`

A figure you make is a **page**, one output per source:
`figures/src/<topic>/<page>.tex` (standalone LaTeX: an equation, or a TikZ
tensor diagram) or `<page>.py` (a script that writes the SVG path it is given)
→ `figures/assets/<topic>/<page>.svg`, and `.pdf` for LaTeX pages with `--pdf`.

```sh
.github/tools/figures/build.sh               # every page that is out of date
.github/tools/figures/build.sh --pdf 02-x    # one topic, keeping PDFs for \includegraphics
```

`figures/` holds only pages and what they build into; everything that runs
them sits in `.github/tools/figures/`. A `.tex` page starts `\input{preamble}`
and a tensor diagram adds `\usepackage{tikz-tensors}`
([pen-sotashimozono/tikz-tensors](https://github.com/pen-sotashimozono/tikz-tensors): wavy legs for continuous arguments, plain lines for finite indices,
circles for functions, squares for coefficient arrays; `\tnswap`; the shared
theme's colours). It is a git submodule at `.github/tools/figures/tikz-tensors/`.
**Its `main` is the one canonical tikz-tensors, always a release** (gated in
that repository: PRs only, version checked, released on merge). Here it is
either pinned at a release, or developed in place on a branch named after this
project — a proposal, which you decide separately to send to tikz-tensors as a
PR; merged, it becomes the next release.

```sh
.github/tools/figures/tikz-tensors.sh status        # release or proposal; ahead/behind main; pushed?
.github/tools/figures/tikz-tensors.sh pin latest    # tikz-tensors' main = its newest release (staged)
.github/tools/figures/tikz-tensors.sh pin v0.3.0    # a particular release
.github/tools/figures/tikz-tensors.sh dev <topic>   # branch <project>/<topic> inside the submodule
```

Developing: `dev <topic>`, edit inside the submodule, build here (the figures
use the working copy at once), commit and push **inside it first**, then
`git add` the submodule here. `ensure` sets `push.recurseSubmodules=check`,
so git refuses to push a pin whose commit is not on GitHub. The **tikz-tensors
pin** workflow says the same on every PR: a release passes, a pushed proposal
passes with a warning naming its branch and its distance from main, a commit
not on GitHub fails. The version is the `.sty`'s `\ProvidesPackage` line;
`pin` accepts only a commit whose package is exactly the release that line
names. build.sh fetches the submodule when a checkout lacks it (a clone
without `--recurse-submodules`), and `Initialize.yml` pins it at tikz-tensors'
main in a repository made from this template, because "Use this template"
copies `.gitmodules` but not the pinned commit. Once fetched, figures build
offline.
Pictures are TikZ (a project's own parts go in a `.sty` next to build.sh);
`.py` pages are for computed plots. build.sh finds the shared files
through TEXINPUTS and passes
its own `latexmkrc` with `-r`, so a page never names that directory, and the
root `.latexmkrc` never applies to pages. A document includes a page as
`\includegraphics{assets/<topic>/<page>}` (graphicspath `figures/`); the arXiv
bundle keeps paths below `figures/`, so that still resolves there.
`assets/` mirrors `src/`: an output whose source is gone is deleted.
The **`figure-pages`** skill carries the rules (formula only, one line per
page, numbers from a source, look before reporting).

A figure showing **another paper's result** is never redrawn: the
**`paper-figures`** skill extracts the original from its arXiv source, or crops
it from `papers/<bibkey>.pdf`, into `figures/papers/<bibkey>-fig<N>.svg`, with
the caption in the SVG's `<desc>`. Cite the paper wherever it is shown.

## Versions — bump what the PR touched, and only that

```sh
./.github/scripts/bump.sh --affected patch "One line on what changed and why."
git add docs.toml .github/CHANGELOG.md
```

`--affected` asks `closure.py` which documents actually changed, through their
`\input` children and `references.bib` — and `exports.py` which exports' source
files changed. **Build first** (it reads `out/`) and
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
`docs.toml` conflict by keeping your higher value, and re-bump. PRs on
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
./.github/scripts/refs_sync.sh       # every entry gets papers/<bibkey>.pdf
./.github/scripts/fetch_sources.sh   # and papers/src/<bibkey>.tex or .txt
```

The **`references` skill** carries this, including pinning `DOIGET_STORE_ROOT`
— the store defaults to `./papers` under the cwd, so doiget run from a paper
repository builds a second store inside it.

`papers/src/` makes checking a citation cheap — prefer it to opening the PDF:

```sh
grep -n 'F_Q' papers/src/hauke2016measuring.tex     # the inequality in source form
grep -l 'structure factor' papers/src/*.tex          # which references discuss it
grep -o '\\cite{[^}]*}' papers/src/<key>.tex         # what that paper cites
```

arXiv LaTeX source beats PDF extraction: equations keep their structure,
`\label{...}` is stable across arXiv and published versions (whose equation
*numbers* differ), and nothing is silently dropped — extraction routinely loses
Greek letters.

- **Never invent or guess a DOI.** A plausible one usually resolves to a
  *different, real* paper, which is worse than a broken link.
- **A resolving DOI is not proof the citation is right.** Check the title and
  authors, then read the PDF to confirm it supports your claim.
- Keep `papers/<bibkey>.pdf` in sync with the key in `references.bib`. Each entry
  with a local PDF carries `file = {papers/<bibkey>.pdf}`, written by
  `.github/scripts/bib_files.py` (run by `refs_sync.sh`, checked in CI) — never
  by hand. A PDF fetched by hand (a licensed download) goes to
  `papers/<bibkey>.pdf`; then run `refs_sync.sh` and `fetch_sources.sh`.
- Some works have no OA PDF; `doiget fetch` stores metadata only. Cite normally
  and note the absence.

`strict` is `"false"`: unresolvable entries warn. Set `"true"` to block.

## Exports — pptx / docx on the same version ladder

Slides and reports written in Office are documents like any other: a
`docs.toml` table with a `version`, bumped with `bump.sh`, tagged
`v<version>-<id>` and released on merge. The difference is a `source` in place
of a root:

    [talk]
    source = "slides/talk.pptx"   ->  out/talk.pdf
    version = "0.1.0"             ->  release v0.1.0-talk

`Export CI` builds the PDF with LibreOffice on every PR (artifact
`<id>-pdf`), as `LaTeX CI` does for the `.tex` roots, and checks that the
version moved exactly when the source did — an export's closure is its source
file. `Release.yml` routes each tag by kind: an export's release carries
`<tag>.pptx` (or `.docx`) and `<tag>.pdf`, no diff. Only the source is
committed.

```sh
python3 .github/scripts/exports.py build talk   # locally, if soffice is installed
./.github/scripts/bump.sh talk patch "One line on what changed."
python3 -m unittest discover -s .github/scripts/tests   # after touching the scripts
```

An id may hold only letters, digits and `_` (tags split at the last `-`); a
`source` must be a relative path inside the repository.

The runner has no Office fonts. `.github/actions/libreoffice/fonts.conf` maps
游ゴシック / Hiragino / Meiryo to Noto Sans CJK JP, the Mincho faces to Noto
Serif CJK JP and Calibri to Carlito, and hides the Chinese / Korean CJK faces
LibreOffice would otherwise pick for text with no East Asian font.
`soffice_pdf.py` turns off LibreOffice's Asian/Latin gap for pptx, which
PowerPoint does not add. Glyph widths still differ, so a line may break at a
different word; the release's pptx is the exact layout. Using Noto fonts in
the deck makes the two match.

git stores every committed source whole, so commit at milestones (first draft,
before rehearsal, as given or submitted) rather than on every save.

## Before opening a PR

1. `latexmk main.tex` and `latexmk notes.tex` both build clean.
2. `bump.sh --affected patch` committed — or nothing, if no document changed.
3. New citations came from `doiget`, with their PDFs in `papers/`.
4. `git diff --cached HEAD --stat` — read the **whole** list and confirm nothing
   unintended was swept in by `git add -A`.
