# template.tex

LaTeX template for physics papers in APS/PRB style, with a full CI/CD pipeline on GitHub Actions.

Two root documents out of the box, versioned and released independently: the
paper in **revtex4-2**, and a working notebook in **article** — one column and a
wide measure, because long derivations are unreadable in a PRB two-column. Each
carries its own preamble, so either can be read and shipped on its own.

## Features

- **revtex4-2** with PRB two-column layout, plus a self-contained **article** notebook
- **LuaLaTeX** engine via latexmk
- **Automated release pipeline**: compile each document, latexdiff against its previous version, and supplementary material on every semver tag
- **Multiple root documents**: `docs.toml` lists them; the CI matrix, tags and releases are generated from it
- **Closure-driven version checks**: a PR bumps exactly the documents whose `\input` children or bibliography it touched
- **arXiv bundle**: auto-packaged `.tex` + `.bbl` + figures zip ready for submission
- **DOI verification**: every reference in `references.bib` is validated against Crossref/arXiv via [doiget](https://github.com/sotashimozono/doiget)
- **Dependabot**: GitHub Actions versions updated monthly

## Quick start

Click **Use this template** on GitHub, then clone your new repository.

## Local build

Requirements: TeX Live (with LuaLaTeX, latexmk, bibtex), Zed or any editor with texlab LSP.

```sh
latexmk main.tex        # compile → out/main.pdf
latexmk -c              # clean auxiliaries
latexmk -C              # clean including out/
```

The local build reads `.latexmkrc` and outputs to `out/`.

## File structure

The root holds the documents and nothing else. Everything that runs them
lives under `.github/`, and the skills under `.claude/`. Both are hidden, so
opening the repository to write shows the writing.

```
main.tex                    # paper, revtex4-2 two-column PRB
notes.tex                   # working notebook, article
supplemental.tex            # supplementary material (optional, create when needed)
references.bib              # bibliography (BibTeX; entries from `doiget cite`)
figures/                    # figures in PDF format only
notes/                      # child .tex files of notes.tex
refs/                       # PDF of every cited work, as refs/<bibkey>.pdf
refs/src/                   # full text of each reference for grepping
.latexmkrc                  # build recipe (LuaLaTeX + BibTeX, out/ dir)
CLAUDE.md                   # working rules

.github/docs.toml           # root documents and their versions -- the version authority
.github/CHANGELOG.md        # one entry per version, written by the PR that bumps it
.github/scripts/            # bump.sh, docs.py, closure.py, diff.sh, arxiv_bundle.sh
.github/workflows/         # build, version check, release
.claude/skills/changelog/   # how to record a change and bump

out/                        # build output (gitignored)
```

`.latexmkrc` and `CLAUDE.md` cannot move: latexmk only auto-reads an rc file
from the working directory, and Claude Code only reads `CLAUDE.md` from the
repository root.

## Revision markup

Four commands are defined in each document's preamble:

| Command | Color | Purpose |
|---|---|---|
| `\sh{text}` | green | author edit |
| `\ch{text}` | blue | collaborator edit |
| `\rev{text}` | red | response to reviewer |
| `\remove{text}` | strikethrough | deletion |

Comment out the `xcolor`/`ulem` block before final submission.

## Documents and versioning

`.github/docs.toml` lists the root documents. One table per compiled PDF, and the table
name is the document id — everything mechanical follows from it, so adding a
document is one table and nothing else:

```toml
[main]              # -> main.tex, out/main.pdf, tag main-v0.1.0
version = "0.1.0"

[notes]             # -> notes.tex, out/notes.pdf, tag notes-v0.1.0
version = "0.1.0"
```

Each root carries its own complete preamble rather than reading a shared file,
so either document can be read and shipped on its own. Two differences are
worth knowing: **revtex4-2 bundles its own `natbib`**, so only `notes.tex` loads
it, and `\affiliation` / `\email` / `acknowledgments` are revtex-only, so
`notes.tex` reimplements them.

Set `root` in a table if the file is not `<id>.tex`. A table is a document iff
it carries `version`. There is no `VERSION` file: `docs.toml` is the only
authority, and `Release.yml` verifies the tag matches it before building.

A single `.latexmkrc` serves every document — all of them are LuaLaTeX +
BibTeX into `out/`, and the stems differ, so `out/main.*` and `out/notes.*`
never collide.

### Every PR bumps the documents it touches — and only those

The `version-check` job asks `.github/scripts/closure.py` which documents this branch
actually changed, through their `\input` children and `references.bib` rather
than the root file alone, and requires a single semver step for exactly those.
A document the PR did not touch must stay put. A PR that touches no document at
all — CI, README, tooling — needs no bump.

```sh
./.github/scripts/bump.sh --affected patch "One line on what changed."   # or minor / major
./.github/scripts/bump.sh notes patch "..."                              # or name it explicitly
```

| Command | Example: 1.2.3 → |
|---|---|
| `./.github/scripts/bump.sh main patch` | 1.2.4 |
| `./.github/scripts/bump.sh main minor` | 1.3.0 |
| `./.github/scripts/bump.sh main major` | 2.0.0 |

`--affected` computes the same set CI will demand. Two preconditions: build
first, since it reads the records under `out/`, and commit your content changes
first, since the comparison is `git diff main...HEAD` and an uncommitted file is
invisible to it.

The optional summary is prepended to `CHANGELOG.md` under the tag the bump will
release, and becomes the release body.

### Reading what changed

```sh
git diff main-v1.2.3 main-v1.2.4 -- '*.tex'     # text, greppable
./.github/scripts/diff.sh main-v1.2.3 main-v1.2.4       # rendered latexdiff PDF -> out/
```

Both flatten `\input` children, so changes in child files are visible — the
release `diff-*.pdf` does the same.

Every merged PR therefore ships a release, so each merge leaves a comparable snapshot: `{document}-v{version}.pdf` plus `diff-{document}-v{version}.pdf`, a latexdiff against that document's previous tag. The version history is a one-to-one record of merged changes, per document.

The comparison is against the **current tip of `main`**, not the state at PR creation: if another PR merges first, the check goes red until you merge/rebase `main` into your branch and re-bump (expect a conflict on `docs.toml` — keep your branch's higher value). With several PRs in flight, assign the ladder up front (0.1.1, 0.1.2, 0.1.3, …) and merge in that order.

On a private repository under the Free plan, branch protection is unavailable, so the check is advisory in the mechanical sense — the merge button is the gate. On a public repository, add Version Check as a required status check to make it truly blocking.

### Manual release

From the Actions tab, run **Release** with the document and the target version (without `v`):

```sh
gh workflow run Release.yml --field document=main --field version=1.0.0
```

The pipeline builds in parallel and attaches to the GitHub Release:

| File | Contents |
|---|---|
| `main-v1.0.0.pdf` | compiled document |
| `diff-main-v1.0.0.pdf` | latexdiff against this document's previous tag (skipped on its first tag) |
| `supplemental-main-v1.0.0.pdf` | supplementary (only if `supplemental.tex` exists) |
| `arxiv-bundle-main-v1.0.0.zip` | flattened `main.tex` + `main.bbl` + `figures/*.pdf` for arXiv submission |

The bundle is **flattened**, not copied: a root that pulls content in through
`\input` is not self-contained, and arXiv sees only what is inside the tarball.
`.github/scripts/arxiv_bundle.sh` builds it and then compiles it in isolation, and CI
runs that for every document on every PR — an unflattened bundle fails on arXiv
while every build here stays green, so nothing else would notice it break. The
check is really "is this document self-contained once flattened", which is
worth knowing whether or not it is headed for arXiv.

## Supplementary material

Create `supplemental.tex` in the repository root. It is compiled independently and included in the release automatically.

## DOI verification

Runs automatically when `references.bib` changes. Can also be triggered manually from the Actions tab. Currently non-strict (unresolvable DOIs warn but do not fail the build).

## License

MIT
