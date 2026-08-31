# template.tex

LaTeX template for physics papers in APS/PRB style, with a CI/CD pipeline on GitHub Actions.

Two root documents, versioned and released independently: the paper in
**revtex4-2**, and a working notebook in **article** — one column and a wide
measure, because long derivations are unreadable in a PRB two-column. Each
carries its own preamble, so either ships alone.

## Features

- **revtex4-2** PRB two-column, plus a self-contained **article** notebook
- **LuaLaTeX** via latexmk, one `.latexmkrc` for every document
- **Multiple root documents**: `.github/docs.toml` lists them; the build matrix, tags and releases are generated from it
- **Two version checks**: a fast one allowing only a single semver step, and a closure-driven one requiring a bump for exactly the documents the PR touched
- **Per-document releases**: `main-v1.2.3`, `notes-v0.4.0`, each with its own PDF and its own latexdiff
- **arXiv bundle**: flattened `.tex` + `.bbl` + figures, compiled in isolation on every PR to prove it still builds
- **DOI verification** against Crossref/arXiv via [doiget](https://github.com/sotashimozono/doiget)
- **Dependabot** for GitHub Actions

## Quick start

Click **Use this template**, then clone. On the first push `Initialize.yml`
runs once and deletes itself: every document goes to `0.1.0`, the template's
changelog is cleared, and `LICENSE` is removed — the MIT licence covers the
template, not the work you write with it.

## Local build

Requires TeX Live (LuaLaTeX, latexmk, bibtex, latexpand).

```sh
latexmk main.tex        # → out/main.pdf
latexmk notes.tex       # → out/notes.pdf
latexmk -c              # clean auxiliaries
latexmk -C              # clean including out/
```

## File structure

The root holds the documents; everything that runs them is under `.github/`,
skills under `.claude/`.

```
main.tex                    # paper, revtex4-2 two-column PRB
notes.tex                   # working notebook, article
supplemental.tex            # supplementary material (optional)
references.bib              # bibliography, from `doiget cite`
figures/  notes/            # figures (PDF only); children of notes.tex
refs/  refs/src/            # one PDF per bibkey; full text for grepping
.latexmkrc                  # LuaLaTeX + BibTeX into out/
CLAUDE.md  LICENSE          # root-only, see below

.github/docs.toml           # root documents and versions — the version authority
.github/CHANGELOG.md        # one entry per version
.github/scripts/            # bump.sh, docs.py, closure.py, diff.sh, arxiv_bundle.sh, refs_sync.sh, fetch_sources.sh
.github/workflows/          # build, version checks, release, reference verification
.claude/skills/             # changelog (record a change), references (doiget)

out/                        # build output (gitignored)
```

`.latexmkrc`, `CLAUDE.md` and `LICENSE` cannot move: latexmk reads an rc only
from the working directory, Claude Code reads `CLAUDE.md` only from the root,
and GitHub detects a licence only at the root. `README.md` is the exception —
it does resolve from `.github/`.

## Revision markup

Defined in each document's preamble; comment out the `xcolor`/`ulem` block
before final submission.

| Command | Color | Purpose |
|---|---|---|
| `\sh{text}` | green | author edit |
| `\ch{text}` | blue | collaborator edit |
| `\rev{text}` | red | response to reviewer |
| `\remove{text}` | strikethrough | deletion |

## Documents and versioning

One table per compiled PDF; the table name is the document id, and everything
mechanical follows from it:

```toml
[main]              # -> main.tex, out/main.pdf, tag main-v0.1.0
version = "0.1.0"

[notes]             # -> notes.tex, out/notes.pdf, tag notes-v0.1.0
version = "0.1.0"
```

Set `root` if the file is not `<id>.tex`. A table is a document iff it carries
`version`. There is no `VERSION` file; `Release.yml` verifies the tag matches
the manifest before building.

Each root carries its own preamble rather than sharing one. Two differences
matter: **revtex4-2 bundles its own `natbib`**, so only `notes.tex` loads it,
and `\affiliation` / `\email` / `acknowledgments` are revtex-only, so
`notes.tex` reimplements them.

### Bump what the PR touched, and only that

```sh
./.github/scripts/bump.sh --affected patch "One line on what changed."
./.github/scripts/bump.sh notes minor "..."     # or name it explicitly
```

`--affected` asks `closure.py` which documents actually changed, through their
`\input` children and `references.bib`. Build first (it reads `out/`) and
commit the content first (it compares commits, not the working tree). The
summary is prepended to `.github/CHANGELOG.md` under the tag it will release,
and becomes the release body.

Two checks enforce this, split on purpose:

| Check | Rule | Build |
|---|---|---|
| **Validate semver step** (`VersionCheck.yml`) | every version unchanged or exactly one step — no two-step jumps, no going backwards, no `X.Y` | no |
| **Validate semver bump** (`latex-ci.yml`) | the documents the PR touched moved, and the ones it did not touch did not | yes, it reads each closure from the build records |

The first is a subset of the second, worth its own workflow because it answers
in seconds rather than after a LaTeX build, and still runs when a build fails —
precisely when the second cannot run at all. No branch protection is
configured, so the merge button is the gate; require both to make it blocking.

Comparison is against the **current tip of `main`**. If another PR merges first
having touched the same document, take `main` in, keep your higher value in the
`.github/docs.toml` conflict, and re-bump. PRs on different documents do not
collide.

### Reading what changed

```sh
git diff main-v1.2.3 main-v1.2.4 -- '*.tex'          # text, greppable
./.github/scripts/diff.sh main-v1.2.3 main-v1.2.4    # rendered latexdiff -> out/
```

Both flatten `\input` children, as the release `diff-*.pdf` does. A PR touching
no document ships no release; one that bumps a document releases it on merge.

### Manual release

```sh
gh workflow run Release.yml --field document=main --field version=1.0.0
```

| File | Contents |
|---|---|
| `main-v1.0.0.pdf` | compiled document |
| `diff-main-v1.0.0.pdf` | latexdiff against this document's previous tag (skipped on its first) |
| `supplemental-main-v1.0.0.pdf` | only if `supplemental.tex` exists |
| `arxiv-bundle-main-v1.0.0.zip` | flattened `.tex` + `.bbl` + `figures/*.pdf` |

The bundle is **flattened**, not copied: arXiv sees only what is inside the
tarball, so a root that pulls content in through `\input` is not self-contained.
`arxiv_bundle.sh` builds it and compiles it in isolation, per document per PR —
an unflattened bundle fails on arXiv while every build here stays green, so
nothing else would notice.

## Supplementary material

Create `supplemental.tex` in the root. It is compiled independently and
attached to every release.

## DOI verification

Runs when `references.bib` changes, or manually from the Actions tab.
Non-strict: unresolvable DOIs warn. Set `strict: "true"` in
`VerifyReferences.yml` to block.

## License

MIT, for the template. `Initialize.yml` removes it from a generated repository,
since it does not cover the work written there.
