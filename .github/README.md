# template.tex

LaTeX template for physics papers in APS/PRB style, with a full CI/CD pipeline on GitHub Actions.

Two root documents out of the box, versioned and released independently: the
paper in **revtex4-2**, and a working notebook in **article** — one column and a
wide measure, because long derivations are unreadable in a PRB two-column. Each
carries its own preamble, so either can be read and shipped on its own.

## Features

- **revtex4-2** with PRB two-column layout, plus a self-contained **article** notebook
- **LuaLaTeX** engine via latexmk, one `.latexmkrc` for every document
- **Multiple root documents**: `.github/docs.toml` lists them; the CI build matrix, the tags and the releases are all generated from it
- **Two version checks**: a fast one that allows only a single semver step, and a closure-driven one that requires a bump for exactly the documents whose `\input` children or bibliography the PR touched
- **Per-document releases**: `main-v1.2.3`, `notes-v0.4.0`, each with its own PDF and its own latexdiff against its own previous tag
- **arXiv bundle**: flattened `.tex` + `.bbl` + figures, and CI compiles it in isolation on every PR to prove it still builds
- **DOI verification**: every reference in `references.bib` is validated against Crossref/arXiv via [doiget](https://github.com/sotashimozono/doiget)
- **Dependabot**: GitHub Actions versions updated monthly

## Quick start

Click **Use this template** on GitHub, then clone your new repository.

On the first push, `Initialize.yml` runs once in the generated repository and
then deletes itself. It sets every document in `.github/docs.toml` to `0.1.0`,
clears this template's changelog, and removes `LICENSE` — the MIT licence covers
the template, not the work you write with it.

## Local build

Requirements: TeX Live (with LuaLaTeX, latexmk, bibtex, latexpand), and any
editor with the texlab LSP.

```sh
latexmk main.tex        # compile → out/main.pdf
latexmk notes.tex       # compile → out/notes.pdf
latexmk -c              # clean auxiliaries
latexmk -C              # clean including out/
```

The local build reads `.latexmkrc` and outputs to `out/`.

## File structure

The root holds the documents. Everything that runs them lives under `.github/`,
and the skills under `.claude/`. Both are hidden, so opening the repository to
write shows the writing.

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
LICENSE                     # GitHub detects a licence at the root only

.github/docs.toml           # root documents and their versions — the version authority
.github/CHANGELOG.md        # one entry per version, written by the PR that bumps it
.github/scripts/            # bump.sh, docs.py, closure.py, diff.sh, arxiv_bundle.sh, fetch_sources.sh
.github/workflows/          # build, version check, release, reference verification
.claude/skills/changelog/   # how to record a change and bump

out/                        # build output (gitignored)
```

`.latexmkrc`, `CLAUDE.md` and `LICENSE` cannot move: latexmk only auto-reads an
rc file from the working directory, Claude Code only reads `CLAUDE.md` from the
repository root, and GitHub detects a licence at the root only. `README.md` is
the exception — GitHub does resolve it from `.github/`, which is why it lives
there.

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

`.github/docs.toml` lists the root documents. One table per compiled PDF, and
the table name is the document id — everything mechanical follows from it, so
adding a document is one table and nothing else:

```toml
[main]              # -> main.tex, out/main.pdf, tag main-v0.1.0
version = "0.1.0"

[notes]             # -> notes.tex, out/notes.pdf, tag notes-v0.1.0
version = "0.1.0"
```

Set `root` in a table if the file is not `<id>.tex`. A table is a document iff
it carries `version`. There is no `VERSION` file: the manifest is the only
authority, and `Release.yml` verifies the tag matches it before building.

Each root carries its own complete preamble rather than reading a shared file,
so either document can be read and shipped on its own. Two differences are worth
knowing: **revtex4-2 bundles its own `natbib`**, so only `notes.tex` loads it,
and `\affiliation` / `\email` / `acknowledgments` are revtex-only, so
`notes.tex` reimplements them.

A single `.latexmkrc` serves every document — all of them are LuaLaTeX + BibTeX
into `out/`, and the stems differ, so `out/main.*` and `out/notes.*` never
collide.

### Every PR bumps the documents it touches — and only those

The `version-check` job asks `.github/scripts/closure.py` which documents this
branch actually changed, through their `\input` children and `references.bib`
rather than the root file alone, and requires a single semver step for exactly
those. A document the PR did not touch must stay put. A PR that touches no
document at all — CI, README, tooling — needs no bump and ships no release.

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

The optional summary is prepended to `.github/CHANGELOG.md` under the tag the
bump will release, and becomes the release body. The `changelog` skill under
`.claude/skills/` carries the whole procedure.

### Reading what changed

```sh
git diff main-v1.2.3 main-v1.2.4 -- '*.tex'          # text, greppable
./.github/scripts/diff.sh main-v1.2.3 main-v1.2.4    # rendered latexdiff PDF -> out/
```

Both flatten `\input` children, so changes in child files are visible — the
release `diff-*.pdf` does the same.

A merged PR ships a release for each document it bumped: `{document}-v{version}.pdf`
plus `diff-{document}-v{version}.pdf`, a latexdiff against that document's own
previous tag. Each document's version history is a one-to-one record of the
merges that changed it.

The comparison is against the **current tip of `main`**, not the state at PR
creation. If another PR merges first and touched the same document, the check
goes red until you merge `main` into your branch and re-bump — expect a conflict
on `.github/docs.toml`, and keep your branch's higher value. PRs touching
different documents do not collide.

Two checks enforce this, split on purpose:

| Check | Rule | Needs a build |
|---|---|---|
| **Validate semver step** (`VersionCheck.yml`) | every version is unchanged or exactly one semver step from `main` — no two-step jumps, no going backwards, no `X.Y` | no |
| **Validate semver bump** (`latex-ci.yml`) | the documents the PR touched moved, and the ones it did not touch did not | yes, it reads each document's closure from the build records |

The first is a strict subset of the second. It is worth its own workflow because
it answers in seconds rather than after a LaTeX build, and because it still runs
when a build fails — which is precisely when the closure-driven check cannot run
at all.

No branch protection is configured on this repository, so the merge button is
the gate. Require both to make it blocking.

### Manual release

From the Actions tab, run **Release** with the document and the target version
(without `v`):

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
`.github/scripts/arxiv_bundle.sh` builds it and then compiles it in isolation,
and CI runs that for every document on every PR — an unflattened bundle fails on
arXiv while every build here stays green, so nothing else would notice it break.
The check is really "is this document self-contained once flattened", which is
worth knowing whether or not it is headed for arXiv.

## Supplementary material

Create `supplemental.tex` in the repository root. It is compiled independently
and attached to every release automatically.

## DOI verification

Runs automatically when `references.bib` changes. Can also be triggered manually
from the Actions tab. Currently non-strict: unresolvable DOIs warn but do not
fail the build. Set `strict: "true"` in `VerifyReferences.yml` to make it block.

## License

MIT — for the template. `Initialize.yml` removes it from a generated repository,
since it does not cover the work you write there.
