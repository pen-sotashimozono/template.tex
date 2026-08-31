# Working rules for this repository

A LaTeX paper repository. `main.tex` is the paper, `references.bib` is its
bibliography, and `refs/` holds the PDF of every cited work. CI enforces two
disciplines: **one version bump per PR** and **resolvable references**.

`docs.toml` lists the root documents and is the only version authority. The
table name is the document id and everything mechanical follows from it -- the
root file, the build output, the release tag:

    [main]  ->  main.tex  ->  out/main.pdf  ->  tag main-v0.1.0

so a second root document is one table, and the CI matrix, the release and the
tag all pick it up unchanged.

## Layout

| Path | Contents |
|---|---|
| `main.tex` | paper source; child `.tex` files are pulled in with `\input` |
| `references.bib` | bibliography — entries come from `doiget cite`, never hand-written |
| `refs/` | one PDF per bibliography key: `refs/<bibkey>.pdf` |
| `refs/src/` | full text of each reference for grepping — arXiv LaTeX source (`.tex`) where available, PDF extraction (`.txt`) otherwise |
| `docs.toml` | root documents and their versions -- the version authority |
| `CHANGELOG.md` | one entry per version, headed by its tag; the PR that bumps writes it |
| `figures/` | figures, PDF only |
| `notes/` | working notes |
| `scripts/bump.sh` | version bump helper |
| `scripts/docs.py` | reads and writes `docs.toml` -- ids, roots, tags, versions |
| `scripts/closure.py` | a document's dependency closure, read off its build record |
| `out/` | build output (gitignored) |

Build with `latexmk main.tex` → `out/main.pdf`.

## Version discipline — every PR bumps by exactly one step

`VersionCheck.yml` fails a PR whose `docs.toml` version is unchanged, and fails
a bump that is not a single semver step. Before opening a PR:

```sh
./scripts/bump.sh main patch "One line on what changed and why."
./scripts/bump.sh --affected patch "..."   # or: every document this branch touched
git add docs.toml CHANGELOG.md
```

`--affected` asks `closure.py` which documents this branch actually changed and
bumps exactly those. It reads the build records under `out/`, so build first.

The summary becomes the `CHANGELOG.md` entry and the release body, so the
history is readable in-repo. Omitting it leaves a `TODO` to fill in.

Each merged PR ships a release: `AutoRelease.yml` walks `docs.toml`, finds
each document whose version has no matching tag, and dispatches `Release.yml`,
which tags `{document}-v{version}` and attaches `{tag}.pdf`, `diff-{tag}.pdf`
(latexdiff against that document's previous tag) and the arXiv bundle. The
point is that every merge leaves a comparable snapshot — that is why the bump
is mandatory and not optional.

**The comparison is against the current tip of `main`, not the state at PR
creation.** Consequences when several PRs are open at once:

- Only the next PR in the queue is green. Assign the ladder up front
  (0.1.1, 0.1.2, 0.1.3, …) and merge in that order.
- After a PR merges, the next one must take `main` in (`git merge main`) to
  make its checks re-run — a base-branch update alone does not re-trigger them.
- That merge conflicts on `docs.toml` every time. Resolve by keeping **your
  branch's higher value**, not `main`'s.
- If the merge order changes, rebase onto `main` and re-run `./scripts/bump.sh`.

## References — always go through doiget

`VerifyReferences.yml` resolves every DOI / arXiv id in `references.bib`
against Crossref and arXiv whenever that file changes. Hand-written entries
with a mistyped or invented identifier are what break it. For every new
citation:

```sh
doiget fetch <doi|arxiv-id>   # PDF into the local store; copy it to refs/<bibkey>.pdf
doiget cite  <doi|arxiv-id>   # BibTeX; paste into references.bib, rename the key
./scripts/fetch_sources.sh    # fills refs/src/ with the full text of new entries
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

1. `latexmk main.tex` builds clean — every root in `docs.toml`, if there are
   several.
2. `./scripts/bump.sh <document> patch` (or minor/major) is committed.
3. New citations came from `doiget`, with their PDFs in `refs/`.
4. `git diff --cached HEAD --stat` — read the **whole** list, not the head of
   it, and confirm nothing unintended (caches, scratch files, other people's
   directories) was swept in by `git add -A`.
