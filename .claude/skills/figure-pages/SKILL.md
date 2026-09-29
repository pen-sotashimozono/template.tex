---
name: figure-pages
description: Make or change a figure page - a standalone equation, a TikZ tensor diagram (tikz-tensors) or picture, or a computed plot - under figures/src/, built to figures/assets/ as SVG (and PDF for the documents). Use whenever a slide or a document needs a new formula or schematic picture, or a figure's notation, numbering or folder changes.
---

# Figure pages: one output per source

`figures/src/<topic>/<page>.tex|.py` → `.github/tools/figures/build.sh` →
`figures/assets/<topic>/<page>.svg` (and `.pdf` with `--pdf`).

`figures/` holds only what a writer looks at: pages (`src/`), what they build
into (`assets/`), and other papers' figures (`papers/`, the `paper-figures`
skill). The shared files a page uses — `preamble.tex` and the vendored
`tikz-tensors/` ([pen-sotashimozono/tikz-tensors](https://github.com/pen-sotashimozono/tikz-tensors), pinned by `update-tikz-tensors.sh`) — and the
build's `latexmkrc` live in `.github/tools/figures/`; build.sh puts that
directory on TEXINPUTS, so a page just writes `\input{preamble}` and
`\usepackage{tikz-tensors}` and never names it.

Topics are folders in reading order (`01-model`, `02-method`, …); pages are
numbered inside them (`00-…`, `01-…`, `01b-…`). `figures/src/example/` shows
one page of each kind; delete it once a real topic exists.

## What goes in a page

- **The formula only.** No text labels ("one-body:", "ground state:") and no
  `\underbrace{…}_{\text{…}}` explanations — the slide or the caption carries
  the words. Units are part of a formula.
- **One line per page.** A two-line array is two pages (`01a-…`, `01b-…`).
- **A header comment** saying what the page shows, where its numbers come
  from, and which pages it pairs with (by path).
- **Numbers from a source** — a calculation in the repository, or a paper
  checked in `papers/` — never from memory. Recompute a rounded value before
  writing it.
- **One notation for the whole project.** Decide the symbols once (write them
  into CLAUDE.md) and keep every page to them.

## Kinds of page

- **Equation** (`.tex`): `\documentclass[border=4pt]{standalone}`,
  `\input{preamble}`, one `$\displaystyle … $`.
- **Tensor diagram** (`.tex`): add `\usepackage{tikz-tensors}` and use its styles —
  `cont` wavy legs for continuous arguments (**r**), `disc` plain lines for
  finite indices, `fn`/`fnwide`/`fntall` circles and boxes for functions,
  `coef`/`coefwide`/`coeftall` squares for arrays, `frame` for a group that
  contracts to one array, `\tnswap` to exchange two fermion legs. Conventions
  are in the header of `tikz-tensors.sty` and its README. Put the coefficients on top of the basis
  functions, so the basis visibly sits between the numbers and space.
- **Picture** (`.tex`): plain TikZ with the theme's colours (from tikz-tensors);
  parts a project reuses go in a `.sty` next to build.sh (found on TEXINPUTS).
  Labels are LaTeX math, so they match the equations.
- **Computed plot** (`.py`): a script that writes the SVG path it is given
  (matplotlib with `svg.fonttype = path`, say); run it with `PYTHON=` an
  interpreter that has what it imports.

A figure showing *another paper's* result is never drawn here: extract the
original with the **`paper-figures`** skill.

## Build and look

```sh
.github/tools/figures/build.sh                  # every page that is out of date
.github/tools/figures/build.sh 02-method        # one topic (or a page's path)
.github/tools/figures/build.sh --pdf            # also keep each LaTeX page's PDF
.github/tools/figures/build.sh --force          # rebuild everything
qlmanage -t -s 900 -o /tmp figures/assets/02-method/01-energy.svg   # macOS preview; then look at it
```

- **Slides** paste the SVG (glyphs are paths, so no TeX fonts are needed).
- **Documents** include the PDF: with `\graphicspath{{figures/}}`,
  `\includegraphics{assets/<topic>/<page>}`. Build with `--pdf` and commit the
  PDF; the arXiv bundle keeps the path below `figures/`.
- A page is rebuilt when it, or a shared file of its kind in
  `.github/tools/figures/`, is newer than its SVG; slow Python pages run
  under `PYTHON=` an interpreter that has what they need.
- `build.sh` deletes any SVG or PDF whose source is gone, so `assets/`
  mirrors `src/`.

Always look at the rendered page before reporting it done — a label can
collide, a line can run off, a symbol can come out wrong.

## Renaming or moving pages

Pages refer to each other by path in their comments, and documents include
them by path. After moving or renumbering, rewrite every reference
(`grep -rn '<old path>' figures/src *.tex notes CLAUDE.md`) and rebuild.
