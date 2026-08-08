# template.tex

LaTeX template for physics papers in APS/PRB style, with a full CI/CD pipeline on GitHub Actions.

## Features

- **revtex4-2** with PRB two-column layout
- **LuaLaTeX** engine via latexmk
- **Automated release pipeline**: compile paper, latexdiff against previous version, and supplementary material on every semver tag
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

```
main.tex            # paper source (single file)
supplemental.tex    # supplementary material (optional, create when needed)
references.bib      # bibliography (BibTeX format)
figures/            # figures in PDF format only
notes/              # scratch notes, not compiled
.latexmkrc          # build recipe (LuaLaTeX + BibTeX, out/ dir)
```

## Revision markup

Four commands are defined in `main.tex` for tracking changes during review:

| Command | Color | Purpose |
|---|---|---|
| `\sh{text}` | green | author edit |
| `\ch{text}` | blue | collaborator edit |
| `\rev{text}` | red | response to reviewer |
| `\remove{text}` | strikethrough | deletion |

Comment out the `xcolor`/`ulem` block before final submission.

## Versioning

The current version is stored in `VERSION` (e.g. `1.2.0`). The git tag `v{VERSION}` is the release identifier. `Release.yml` verifies they match before building.

### Every PR must bump the version

`VersionCheck.yml` fails a PR whose `VERSION` is unchanged, and fails a bump that is not a single semver step. Bump with:

```sh
./scripts/bump.sh patch     # or minor / major
```

| Command | Example: 1.2.3 → |
|---|---|
| `./scripts/bump.sh patch` | 1.2.4 |
| `./scripts/bump.sh minor` | 1.3.0 |
| `./scripts/bump.sh major` | 2.0.0 |

Every merged PR therefore ships a release, so each merge leaves a comparable snapshot: `paper-v{VERSION}.pdf` plus `diff-v{VERSION}.pdf`, a latexdiff against the previous tag. The version history is a one-to-one record of merged changes.

The comparison is against the **current tip of `main`**, not the state at PR creation: if another PR merges first, the check goes red until you merge/rebase `main` into your branch and re-bump (expect a conflict on `VERSION` — keep your branch's higher value). With several PRs in flight, assign the ladder up front (0.1.1, 0.1.2, 0.1.3, …) and merge in that order.

On a private repository under the Free plan, branch protection is unavailable, so the check is advisory in the mechanical sense — the merge button is the gate. On a public repository, add Version Check as a required status check to make it truly blocking.

### Manual release

From the Actions tab, run **Release** with the target version (without `v`):

```sh
gh workflow run Release.yml --field version=1.0.0
```

The pipeline builds in parallel and attaches to the GitHub Release:

| File | Contents |
|---|---|
| `paper-v1.0.0.pdf` | compiled paper |
| `diff-v1.0.0.pdf` | latexdiff against previous tag (skipped on first tag) |
| `supplemental-v1.0.0.pdf` | supplementary (only if `supplemental.tex` exists) |
| `arxiv-bundle-v1.0.0.zip` | `main.tex` + `main.bbl` + `figures/*.pdf` for arXiv submission |

## Supplementary material

Create `supplemental.tex` in the repository root. It is compiled independently and included in the release automatically.

## DOI verification

Runs automatically when `references.bib` changes. Can also be triggered manually from the Actions tab. Currently non-strict (unresolvable DOIs warn but do not fail the build).

## License

MIT
