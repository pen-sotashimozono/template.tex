---
name: paper-figures
description: Use a cited paper's own figure - extract it from the paper's arXiv source, or crop it from refs/<bibkey>.pdf, into figures/papers/<bibkey>-fig<N>.svg. Use whenever a slide or a note should show a figure from a paper; never redraw a look-alike.
---

# A paper's figure: the original, as SVG

A figure that shows another paper's result is shown as **that paper's own
figure**. Drawing an imitation of it in `figures/src/` is not
allowed: our own pages are only for our derivations and our own computed
numbers.

```sh
python3 .github/tools/figures/paper_figures.py <bibkey>                               # every figure, from the arXiv source
python3 .github/tools/figures/paper_figures.py <bibkey> 1 4                           # only Figs. 1 and 4
python3 .github/tools/figures/paper_figures.py <bibkey> crop <N> <page> <x> <y> <w> <h>  # from refs/<bibkey>.pdf
```

Output is **only SVG**, flat in `figures/papers/`:

| File | Is |
|---|---|
| `<bibkey>-fig<N>.svg` | the paper's Fig. N |
| `<bibkey>-fig<N>a.svg`, `…b.svg` | a figure built from several files, in include order |

Each SVG carries the figure's label and caption in its `<desc>`, so a figure
is found by what it shows:

```sh
grep -o '<desc>[^<]*' figures/papers/<bibkey>-fig*.svg | cut -c1-200
```

## Which route

1. **arXiv source** (default). The key's `eprint`, or `doiget link <doi>`,
   gives the id. Figures are numbered by the order of the figure environments
   in the main `.tex` (inputs inlined) — the paper's own numbering. Check one
   against the PDF (`FIG. N.` in `pdftotext refs/<bibkey>.pdf`) the first time.
   Vector figures (pdf, eps) stay vector; png/jpg are embedded unchanged.
2. **Crop** (no arXiv source: old or publisher-only papers). Render the page at
   72 dpi, where one pixel is one PDF point, and read off the box:
   ```sh
   pdftocairo -png -r 72 -f <page> -l <page> refs/<bibkey>.pdf /tmp/p
   ```
   Then `crop <N> <page> <x> <y> <w> <h>` (top-left origin). The result is a
   vector crop of the printed page — look at it before using it.

## Using it

- On a storyboard page, link it like any figure
  (`../../figures/papers/<bibkey>-fig<N>.svg`), with a `<cite>` to the same
  key right under it — the figure is the authors' work.
- On the deck, the citation goes beside the figure, in the deck style.
- Take only the figures a slide uses (give their numbers). Re-running with
  numbers replaces just those; without numbers, every `-fig*.svg` of the key is
  rewritten. Never edit these files by hand.
- To find the number first, read the captions in the PDF
  (`pdftotext refs/<bibkey>.pdf - | grep -A2 'FIG. '`) or extract everything once
  and grep the `<desc>`.
