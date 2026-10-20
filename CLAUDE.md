# Working rules for this repository

Two root documents: `main.tex` (paper, revtex4-2 two-column PRB) and
`notes.tex` (working notebook, article). They share `references.bib`; `papers/`
holds the PDF of every cited work.

`docs.toml` is the only version authority. The table name is the
document id, and the rest follows from it:

    [main]  ->  main.tex  ->  out/main.pdf  ->  tag v0.0.11-main

A third document is one table; the CI matrix, tags and releases pick it up
unchanged.

The file a table stands for must exist: `<id>.tex`, or what `root` names.
**Validate semver step** fails otherwise, naming the table and the file. An
export is the exception: its table may be written before its `source` is
committed.

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
| `figures/` | four kinds, told apart by directory: `src/<topic>/` figure pages you write; `generated/<topic>/` what `build.sh` makes of them (SVG and PDF, built and not committed) — never edited by hand, and remade if deleted; `assets/` figures made one by one outside the page build (a plot exported from elsewhere, a photograph), committed as the originals they are; `papers/<bibkey>-fig<N>.svg` cited papers' own figures — see below |
| `src/notes/`, `src/main/` | children of `notes.tex` and of `main.tex`: `src/<document id>/`, one directory per document |
| `slides/` (or anywhere) | pptx / docx exports, built to PDF in CI |
| `.github/CHANGELOG.md` | one entry per version, headed by its tag |
| `.github/scripts/` | `bump.sh`, `docs.py`, `closure.py`, `diff.sh`, `arxiv_bundle.sh`, `refs_sync.sh`, `fetch_sources.sh`, `bib_files.py`, `exports.py`, `soffice_pdf.py`, `rename_releases.py`, `release_log.py` |
| `.github/tools/figures/` | what runs the figure pages, never read while writing: `build.sh`, `latexmkrc`, `preamble.tex`, `notation.tex` (what the shapes of a tensor diagram stand for here), `paper_figures.py`, and `tikz-tensors/` (the TikZ format and theme, a git submodule pinned by `tikz-tensors.sh`) |
| `.claude/rules/` | one file per subject, listed in `.claude/README.md`; all in force unless listed under "Rules not in force" below |
| `.claude/skills/` | `changelog` (record a change and bump), `references` (doiget), `figure-pages` (an equation, tensor diagram or drawing), `paper-figures` (a cited paper's own figure), `cold-read` (a reader who did not write the passage, before the author sees it), `release-log` (bring released versions to this machine and say how they changed) |
| `out/` | build output (gitignored) |
| `log/` | released PDFs and their diffs, fetched by `release_log.py` with a page of what changed (gitignored; a copy of what the releases hold) |

A change of layout or convention (where files in `out/` go, a new `docs.toml`
key, the name of a PDF) is written into this section in the same PR, and, in a
repository made from this template, into the template's `CLAUDE.md` as well.

The scripts need Python 3.11 or later (`tomllib`, `X | None`, the `filter` of
`tarfile`). Where `python3` is older (macOS ships 3.9), set `PYTHON=` for
`bump.sh` and `diff.sh`, and put a newer `python3` first on `PATH` for the
tests, `release_log.py` and `paper_figures.py`. A comment in `.latexmkrc` or in
a script says what the code does that is not obvious from it, in a line or two,
and leaves out the history of why.

`.claude` is a git submodule,
[pen-sotashimozono/.claude](https://github.com/pen-sotashimozono/.claude),
shared by every repository made from the template. A clone without
`--recurse-submodules` has it empty until `git submodule update --init .claude`.
To change a rule or a skill, edit inside `.claude`, commit and push **there
first**, then `git add .claude` here; `git submodule update --remote .claude`
moves to its newest main. Everything in it is shared, so what belongs to this
repository only is written in this file. `Initialize.yml` adds it afresh at
its main in a repository made from this template, for the same reason
as tikz-tensors below. The template itself follows `.claude`'s main every four hours
(`SyncClaude.yml`: move the pin, refuse the move if it emptied `rules/` or
`skills/`, commit); initialization deletes that workflow, because the rules are
in force while a project's text is being written and should not move under its
author. A project therefore pins when it chooses.

`latexmk main.tex` → `out/main.pdf`, `latexmk notes.tex` → `out/notes.pdf`. One
`.latexmkrc` serves both; the stems differ so nothing collides. `out/` keeps
only the latest diff PDFs. A stale `out/<id>-diff-HEAD..working.pdf` is deleted
after a commit, and an older tag's diff is made again with `diff.sh` when it is
wanted.

Before editing either preamble: **revtex4-2 bundles its own `natbib`**, so only
`notes.tex` loads it. `\affiliation`, `\email` and `acknowledgments` are
revtex-only, so `notes.tex` reimplements them — that is what lets the same
markup compile under either class.

## Rules

Every file in `.claude/rules/` is in force by default. To switch one off, name
it below with one line on why. Rules that hold for this repository only (its
notation, its running example, which sections to imitate) are also written
here, not in `.claude`.

### Rules not in force

None.

### Rules of this repository only

None yet.

## Figures: pages in `figures/src/`, tools in `.github/tools/figures/`

A figure you make is a **page**, one output per source:
`figures/src/<topic>/<page>.tex` (standalone LaTeX: an equation, or a TikZ
tensor diagram) or `<page>.py` (a script that writes the SVG path it is given)
→ `figures/generated/<topic>/<page>.svg`, and `.pdf` for LaTeX pages with `--pdf`.

```sh
.github/tools/figures/build.sh               # every page that is out of date
.github/tools/figures/build.sh --pdf 02-x    # one topic, keeping PDFs for \includegraphics
.github/tools/figures/build.sh --pdf-only    # only the PDFs that are missing or out of date
```

Nothing under `figures/generated/` is committed (`.gitignore`): a built file
is stored whole again at every rebuild, and it can always be made from its
page. The root `.latexmkrc` therefore runs `build.sh --pdf-only` before every
build of a document. It writes the PDF of each `.tex` page that has none, or
whose page is newer, so a fresh clone, CI and a release build a document with
`latexmk` alone. The SVGs are made only when you ask for them, with
`build.sh <topic>`: for slides, or to look at a page. `closure.py` reads a built PDF
in a build record as the page it came from, the shared `.tex` and `.sty` files
beside `build.sh` and the tikz-tensors pin, so a PR that changes only a figure
still counts as touching the documents that include it.

A page that does not build fails CI, so it is neither merged nor released. On
your own machine it is a warning: the other pages are built, the documents
compile, and a document that includes the broken page shows the PDF of its
last good build, or stops at the file it cannot find.

Pages are built several at a time, as many as there are processors
(`FIGURE_JOBS` overrides). In CI each job that compiles a document restores
the PDFs from a cache keyed on everything a page reads (the pages, the files
beside `build.sh`, the tikz-tensors pin), so a PR that changes no figure
builds none; with nothing to restore, the job builds them through
`.latexmkrc` as a fresh clone does.

`figures/` holds only pages and what they build into; everything that runs
them sits in `.github/tools/figures/`. A `.tex` page starts `\input{preamble}`
and a tensor diagram adds `\usepackage{tikz-tensors}` and `\input{notation}`
([pen-sotashimozono/tikz-tensors](https://github.com/pen-sotashimozono/tikz-tensors) draws shapes, lines and layouts —
`\tnstack`, `\tnlayer`, `\tnconnect`, `\tnopen` — in the shared theme's colours, and says nothing
about what a shape means; `notation.tex`, next to `build.sh`, is this project's
own file of what they stand for: `fn` a function on `cont` wavy legs, `coef` an
array, `op` an operator, and so on). It is a git submodule at `.github/tools/figures/tikz-tensors/`.
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
offline. The template repository itself follows tikz-tensors'
main every four hours (`SyncTikzTensors.yml`: pin, rebuild the example figures, commit);
initialization deletes that workflow, so a project moves only when it pins.
Pictures are TikZ (a project's own parts go in a `.sty` next to build.sh);
`.py` pages are for computed plots. build.sh finds the shared files
through TEXINPUTS and passes
its own `latexmkrc` with `-r`, so a page never names that directory, and the
root `.latexmkrc` never applies to pages. A document includes a page as
`\includegraphics{generated/<topic>/<page>}` (graphicspath `figures/`); the arXiv
bundle keeps paths below `figures/`, so that still resolves there.
`generated/` mirrors `src/`: an output whose source is gone is deleted. In this
template it holds the built example pages; `Initialize.yml` empties it in a
repository made from the template, which then commits only what it builds. A figure
made by hand goes in `figures/assets/` and is included as
`\includegraphics{assets/<name>}`; `build.sh` never reads or writes there.
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

Released versions are read from `log/`, not from GitHub one page at a time:

```sh
python3 .github/scripts/release_log.py notes            # the last three versions: PDF and diff into log/notes/
python3 .github/scripts/release_log.py notes --all      # every version
python3 .github/scripts/release_log.py notes --list     # log/notes/index.md only: version, date, pages, the changelog's line
```

A PR touching no document needs no bump and ships no release. One that bumps a
document releases it on merge: `{tag}.pdf`, `diff-{tag}.pdf` (against that
document's own previous tag) and the arXiv bundle.

Comparison is against the **current tip of `main`**. When two PRs touch the
*same* document, only the next in its queue is green; take `main` in (a
base-branch update alone does not re-trigger checks), resolve the
`docs.toml` conflict by keeping your higher value, and re-bump. PRs on
different documents do not collide.

A document's id is in its tags (`v<version>-<id>`), in the titles of its
releases and in the names of the files attached to them. After renaming a
table in `docs.toml`, the document looks new and its next release has no
previous tag to diff against. `rename_releases.py` moves the history to the
new id: every tag, release, attached file and CHANGELOG heading.

```sh
python3 .github/scripts/rename_releases.py notes lecture            # what would change
python3 .github/scripts/rename_releases.py notes lecture --apply    # change it
```

The old tags are deleted and GitHub does not redirect them, so a link to an
old release stops working.

The move is made by hand, on a machine signed in to GitHub. A workflow cannot
make it: its token may not put a tag on an old commit whose workflow files
differ from today's. What the workflow does is notice. When a PR that renames
a table in `docs.toml` is merged, `AutoRelease.yml` releases nothing until no
tag is left under the old id, and prints the commands to run. Run them before
merging (and commit the changelog in the same PR) and the job passes at once;
run them after, and re-run the job.

A document is followed by its file: it has a new id when its root (or
`source`) now belongs to another table, because git sees the file renamed to
that table's or because that table names the same file. Rename the file with
`git mv`, in the same PR as the table. Two documents that trade ids are found
the same way and moved through a temporary id, in three commands; trade their
`version`s in `docs.toml` too, since a version belongs to the document and not
to the name. Both have tags before and after, so the job cannot see that a
swap is done: label the PR `releases-renamed` and re-run it.

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
