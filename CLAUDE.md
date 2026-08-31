# Working rules for this repository

A LaTeX paper repository carrying two root documents: `main.tex` is the paper in
revtex4-2, `notes.tex` is the working notebook in article. `references.bib` is
the bibliography they share, and `refs/` holds the PDF of every cited work.

CI enforces three disciplines: **bump every document a PR changes and only
those**, **resolvable references**, and **a submission bundle that compiles on
its own**.

`.github/docs.toml` lists the root documents and is the only version authority.
The table name is the document id and everything mechanical follows from it --
the root file, the build output, the release tag:

    [main]  ->  main.tex  ->  out/main.pdf  ->  tag main-v0.0.11

so a third root document would be one table, and the CI matrix, the release and
the tag all pick it up unchanged.

Each root carries its own complete preamble. The two documents repeat what they
share rather than reading a common file, so either can be read and shipped on
its own -- at the cost that a change to shared markup has to be made twice, and
nothing catches a missed one.

## Layout

The repository root holds the documents. Everything that runs them -- workflows,
scripts, the manifest, the changelog -- lives under `.github/`, and the skills
under `.claude/`. Both are hidden, so opening the repository to write shows the
writing.

Three files cannot move, and the reasons are worth keeping so it is not tried
again: latexmk only auto-reads an rc file from the working directory, Claude
Code only reads `CLAUDE.md` from the repository root, and GitHub detects a
licence at the root only. `README.md` is the one that does resolve from
`.github/`, which is why it lives there.

| Path | Contents |
|---|---|
| `main.tex` | paper, revtex4-2 two-column PRB; children pulled in with `\input` |
| `notes.tex` | working notebook, article; one column, wide measure |
| `references.bib` | bibliography — entries come from `doiget cite`, never hand-written |
| `refs/` | one PDF per bibliography key: `refs/<bibkey>.pdf` |
| `refs/src/` | full text of each reference for grepping — arXiv LaTeX source (`.tex`) where available, PDF extraction (`.txt`) otherwise |
| `figures/` | figures, PDF only |
| `notes/` | child `.tex` files of `notes.tex` |
| `.latexmkrc`, `LICENSE` | root-only, for the reasons above |
| `.github/docs.toml` | root documents and their versions -- the version authority |
| `.github/CHANGELOG.md` | one entry per version, headed by its tag; the PR that bumps writes it |
| `.github/scripts/` | `bump.sh`, `docs.py`, `closure.py`, `diff.sh`, `arxiv_bundle.sh`, `fetch_sources.sh` |
| `.claude/skills/changelog/` | the procedure for recording a change and bumping |
| `out/` | build output (gitignored) |

Build with `latexmk main.tex` -> `out/main.pdf`, `latexmk notes.tex` ->
`out/notes.pdf`. One `.latexmkrc` serves both: LuaLaTeX + BibTeX into `out/`,
and the stems differ so nothing collides.

Two things differ between the classes and are worth knowing before editing
either preamble. **revtex4-2 bundles its own `natbib`**, so only `notes.tex`
loads it -- adding `natbib` to `main.tex` clashes with the class. And
`\affiliation`, `\email` and the `acknowledgments` environment are revtex-only,
so `notes.tex` reimplements them; that is what lets the same title and body
markup compile under either class.

## Version discipline — bump every document the PR touches, and only those

The `version-check` job in `latex-ci.yml` asks `closure.py` which documents this
branch actually changed — through their `\input` children and `references.bib`,
not the root file alone — and requires a single semver step for exactly those.
A document the PR did not touch must stay put; moving it is an error. A PR that
touches no document at all, such as a CI or README change, needs no bump and
ships no release.

Before opening a PR:

```sh
./.github/scripts/bump.sh --affected patch "One line on what changed and why."
./.github/scripts/bump.sh notes patch "..."   # or name the document explicitly
git add .github/docs.toml .github/CHANGELOG.md
```

The **`changelog` skill** carries this procedure. Reach for it rather than
reconstructing the command.

`--affected` computes the same set CI will demand. Two preconditions: build
first, since it reads the records under `out/`, and commit your content changes
first, since the comparison is `git diff main...HEAD` and an uncommitted file is
invisible to it. A document that does not yet exist on `main` is new, so the
check accepts whatever version it arrives with and `--affected` skips it.

The summary becomes the `.github/CHANGELOG.md` entry and the release body, so
the history is readable in-repo. Omitting it leaves a `TODO` to fill in.

A PR that bumps a document ships its release on merge: `AutoRelease.yml` walks
the manifest, finds each document whose version has no matching tag, and
dispatches `Release.yml`, which tags `{document}-v{version}` and attaches
`{tag}.pdf`, `diff-{tag}.pdf` (latexdiff against that document's previous tag)
and the arXiv bundle. Every such merge leaves a comparable snapshot.

**The comparison is against the current tip of `main`, not the state at PR
creation.** When several PRs touch the *same* document at once:

- Only the next PR in that document's queue is green. Assign its ladder up front
  and merge in that order. PRs touching different documents do not collide.
- After a PR merges, the next one must take `main` in (`git merge main`) to make
  its checks re-run — a base-branch update alone does not re-trigger them.
- That merge conflicts on `.github/docs.toml`. Resolve by keeping **your
  branch's higher value**, not `main`'s.

Two checks guard this, and the split is deliberate:

| Check | Rule | Needs a build |
|---|---|---|
| **Validate semver step** (`VersionCheck.yml`) | every version is unchanged or exactly one step | no |
| **Validate semver bump** (`latex-ci.yml`) | the *right* documents moved, and only those | yes |

The first is a strict subset of the second, kept separate because it answers in
seconds and because it still runs when a build fails -- which is exactly when
the closure-driven one cannot run at all.

No branch protection is configured, so the merge button is the gate. Require
both to make it blocking.

## The submission bundle must compile on its own

`arxiv_bundle.sh` flattens a document with `latexpand`, adds its `.bbl` and the
figures, then compiles the result in isolation. CI runs it for every document on
every PR.

This is not only about arXiv. It is the check that a document is self-contained
once flattened, and it is the only thing that would notice: an unflattened
bundle fails on arXiv while every build here stays green.

Two things break it, both quietly:

- `latexpand` reads inside `\verb`, so writing `\input{...}` as an *example* in
  prose is treated as a real inclusion. Write around it.
- A file the document reads but git does not track never reaches the tarball.

## References — always go through doiget

`VerifyReferences.yml` resolves every DOI / arXiv id in `references.bib`
against Crossref and arXiv whenever that file changes. Hand-written entries
with a mistyped or invented identifier are what break it. For every new
citation:

```sh
doiget fetch <doi|arxiv-id>   # PDF into the local store; copy it to refs/<bibkey>.pdf
doiget cite  <doi|arxiv-id>   # BibTeX; paste into references.bib, rename the key
./.github/scripts/fetch_sources.sh   # fills refs/src/ with the full text of new entries
```

`refs/src/` is what makes checking a citation cheap. Prefer it to opening the
PDF:

```sh
grep -n 'F_Q' refs/src/hauke2016measuring.tex     # read the inequality in source form
grep -l 'structure factor' refs/src/*.tex          # which references discuss it
grep -o '\\cite{[^}]*}' refs/src/<key>.tex         # what that paper cites (catches second-hand claims)
```

Where the arXiv LaTeX source exists it beats PDF extraction: equations keep
their structure, `\label{...}` gives a reference that is stable across the
arXiv and published versions (whose equation *numbers* differ), and nothing is
silently dropped — PDF extraction routinely loses Greek letters.

Rules that follow:

- **Never invent or guess a DOI.** A plausible-looking DOI usually resolves to
  a *different, real* paper, which is worse than a broken link.
- **A resolving DOI is not proof the citation is right.** Check that the title
  and authors returned by `doiget cite` are the work you meant, then read the
  PDF in `refs/` to confirm it supports the claim you attach to it.
- Keep `refs/<bibkey>.pdf` in sync with the key you chose in `references.bib`.
- Some works have no open-access PDF; `doiget fetch` then stores metadata only.
  Cite them normally and note the absence.

`strict` is currently `"false"` in `VerifyReferences.yml`: an unresolvable
entry warns rather than fails. Set it to `"true"` if you want the check to
block.

## Before opening a PR

1. `latexmk main.tex` and `latexmk notes.tex` both build clean.
2. `./.github/scripts/bump.sh --affected patch` is committed (see the
   `changelog` skill), or nothing was bumped because no document changed.
3. New citations came from `doiget`, with their PDFs in `refs/`.
4. `git diff --cached HEAD --stat` — read the **whole** list, not the head of
   it, and confirm nothing unintended (caches, scratch files, other people's
   directories) was swept in by `git add -A`.
