---
name: references
description: Add, fetch and read citations with doiget. Use whenever a reference is added to references.bib, a cited PDF is needed in refs/, or a claim has to be checked against the source. Entries are never hand-written - a guessed identifier usually resolves to a different real paper.
---

# Citations run through doiget

Three places, one direction:

| | Holds | Filled by |
|---|---|---|
| `references.bib` | which works are cited — the source of truth | `doiget cite` |
| doiget store | the machine-wide PDF cache | `doiget fetch` |
| `refs/`, `refs/src/` | this project's copy: PDF, and full text for grepping | `refs_sync.sh`, `fetch_sources.sh` |

## Adding a citation

```sh
doiget cite 1509.01739                        # or a DOI
```

Paste the output **verbatim** and rename only the key. Never edit the
identifier, and never hand-write an entry: `VerifyReferences.yml` resolves every
DOI and arXiv id against Crossref and arXiv, and a plausible-looking guessed DOI
usually resolves to a *different, real* paper — worse than a broken link.

`cite` resolves live and falls back to the store, so an already-fetched ref
always cites. Then:

```sh
./.github/scripts/refs_sync.sh       # every entry gets refs/<bibkey>.pdf
./.github/scripts/fetch_sources.sh   # and refs/src/<bibkey>.tex or .txt
```

Both are idempotent and read `references.bib`, so neither needs a ref passed by
hand. `refs_sync.sh` fetches into the store when needed and copies out; it
reports entries with no open-access PDF, which is fine — cite them and note the
absence.

## Pin the store, once

The store defaults to `./papers` **under the current directory**, so running
doiget from a paper repository silently builds a second store inside it and
every project re-downloads everything.

```sh
export DOIGET_STORE_ROOT=/path/to/one/shared/papers
doiget config show          # confirm store_root_source is DOIGET_STORE_ROOT
```

`refs_sync.sh` warns when the resolved store sits inside the repository.

## Reading a paper

Prefer `refs/src/` to opening the PDF:

```sh
grep -n 'F_Q' refs/src/hauke2016measuring.tex   # the inequality in source form
grep -l 'structure factor' refs/src/*.tex        # which references discuss it
grep -o '\\cite{[^}]*}' refs/src/<key>.tex       # what that paper cites
```

arXiv LaTeX source beats PDF extraction: equations keep their structure,
`\label{...}` is stable across the arXiv and published versions (whose equation
*numbers* differ), and nothing is silently dropped — extraction routinely loses
Greek letters. `fetch_sources.sh` prefers `.tex` and falls back to `.txt` from
the PDF.

Other reads, when `refs/src/` is not enough:

```sh
doiget text 1509.01739         # sectioned plain text via ar5iv (arXiv id)
doiget tex-source 1509.01739   # raw LaTeX from the arXiv source API
doiget info 1509.01739         # stored metadata; --mode json gives pdf_path
doiget search --local 'entanglement'   # the store, by title / author / venue
doiget list-recent
```

## Checking a citation is right

A resolving DOI proves the identifier exists, not that it supports your claim.
Two failures matter more than a broken link:

- **Misattribution.** Confirm the title and authors `doiget cite` returned are
  the work you meant, then read the source to confirm it supports the specific
  claim — direction of an inequality, which limit, upper versus lower bound.
- **Second-hand claims.** `grep -o '\\cite{[^}]*}'` on the source shows what
  that paper itself cites. A result it attributes to someone else belongs to
  that someone else.

## Keys

`refs/<bibkey>.pdf` and `refs/src/<bibkey>.*` are keyed by the bibkey, so
renaming a key means renaming its files. `refs_sync.sh` re-fetches under the new
name; delete the old ones.
