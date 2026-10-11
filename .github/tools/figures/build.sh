#!/usr/bin/env bash
# Build the figure pages under figures/src/ into figures/assets/, one per page:
#
#   figures/src/<topic>/<name>.tex   standalone LaTeX  -> figures/assets/<topic>/<name>.svg
#   figures/src/<topic>/<name>.py    script that writes the SVG path it is given
#
#   .github/tools/figures/build.sh                       # every page that is out of date
#   .github/tools/figures/build.sh 04-h2-hubbard         # one topic
#   .github/tools/figures/build.sh figures/src/02-h2-problem/02-hamiltonian.tex   # one page
#   .github/tools/figures/build.sh --force               # rebuild even if up to date
#   .github/tools/figures/build.sh --pdf                 # keep the PDF of each .tex page too
#   .github/tools/figures/build.sh --pdf-only            # only the PDFs that are missing or out of date
#
# figures/ holds only what a writer looks at: the pages (src/) and what they
# build into (assets/). Everything that runs them sits here, next to this
# script: preamble.tex (every .tex page does \input{preamble}), tikz-tensors/
# (a git submodule, the TikZ format and theme: \usepackage{tikz-tensors} for
# tensor diagrams; tikz-tensors.sh pins its version, and is called here to
# fetch it when a checkout lacks it), and latexmkrc. They are found through
# TEXINPUTS (and PYTHONPATH, for any
# helper module a Python page wants to share), so a page never names this
# directory. Python pages are for computed plots; pictures are TikZ.
#
# A page is rebuilt when its SVG is missing or older than the page or a shared
# file it reads (see stale() below), which keeps
# slow pages (a PySCF curve) from running every time. Python pages run under
# $PYTHON (default python3).
#
# --pdf keeps <name>.pdf next to <name>.svg for .tex pages, for a document
# that \includegraphics the page (graphicspath {figures/}: assets/<topic>/<name>).
# The SVG is what slides paste; the PDF is what LaTeX includes.
#
# The SVGs are committed and the PDFs are not (.gitignore): a PDF is stored
# whole again at every rebuild, and it can always be made from its page. So a
# checkout has no PDF until the pages are built. --pdf-only does that and no
# more: for each .tex page whose PDF is missing or older than the page, it
# writes the PDF and leaves the SVG alone, so a fresh clone or a CI runner
# never rewrites a committed file. Python pages are skipped (they have no
# PDF), and neither pdftocairo nor pdfinfo is needed. The root .latexmkrc
# runs it before every build of a document. After editing a page, run the
# script without --pdf-only (with --pdf) so that the SVG follows.
#
# One page per source; a .tex that produces more is an error. LaTeX runs in
# figures/.build/, which is deleted on exit, so nothing but src/ and assets/
# remains. An SVG (or PDF) whose source is gone is deleted too, so assets/
# always mirrors src/. LaTeX SVGs come from the PDF with pdftocairo, which
# turns glyphs into paths: they render without the TeX fonts installed.
set -euo pipefail

TOOLS="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$TOOLS/../../.." && pwd)"
cd "$ROOT/figures"
BUILD=.build
PYTHON="${PYTHON:-python3}"
trap 'rm -rf "$BUILD"' EXIT

force=0
pdf=0
pdfonly=0
args=()
for arg in "$@"; do
  case "$arg" in
    -f|--force) force=1 ;;
    --pdf) pdf=1 ;;
    --pdf-only) pdf=1; pdfonly=1 ;;
    *) args+=("$arg") ;;
  esac
done
[ ${#args[@]} -gt 0 ] || args=(src)

pages() { find "$1" -mindepth 1 -type f \( -name '*.tex' -o -name '*.py' \) -path 'src/*/*' | sort; }
sources=()
for arg in "${args[@]}"; do
  arg="${arg#"$ROOT"/}"; arg="${arg#figures/}"
  if [ -f "$arg" ]; then
    sources+=("$arg")
  elif [ -d "$arg" ] || [ -d "src/$arg" ]; then
    [ -d "$arg" ] || arg="src/$arg"
    while IFS= read -r f; do sources+=("$f"); done < <(pages "$arg")
  else
    echo "error: no such page or topic: $arg" >&2
    exit 1
  fi
done

# A page depends on itself and on the shared files it can read: a .tex page on
# $TOOLS/*.tex and *.sty (preamble.tex, any local style) and tikz-tensors/tex (a new pin
# restyles every LaTeX page); a .py page on the modules pages import, named
# here -- not on every *.py in $TOOLS, which also holds paper_figures.py, a
# separate tool whose edits must not rerun slow pages. Add a shared module's
# path to SHARED_PY when Python pages start importing one.
SHARED_PY=("$TOOLS"/schematic.py)
stale() {
  local svg="$1" src="$2" ext="${2##*.}" dep deps
  [ "$force" -eq 1 ] || [ ! -f "$svg" ] || [ "$src" -nt "$svg" ] && return 0
  [ "$pdf" -eq 1 ] && [ "$ext" = tex ] && [ ! -f "${svg%.*}.pdf" ] && return 0
  if [ "$ext" = tex ]; then deps=("$TOOLS"/*.tex "$TOOLS"/*.sty "$TOOLS"/tikz-tensors/tex/*); else deps=("${SHARED_PY[@]}"); fi
  for dep in "${deps[@]}"; do
    [ -f "$dep" ] && [ "$dep" -nt "$svg" ] && return 0
  done
  return 1
}

# tikz-tensors is a submodule: present it before the first LaTeX page, so a
# fresh clone (or a repository made from the template) builds with no setup.
for src in "${sources[@]}"; do
  case "$src" in *.tex) "$TOOLS/tikz-tensors.sh" ensure; break ;; esac
done

for src in "${sources[@]}"; do
  rel="${src#src/}"
  topic="$(dirname "$rel")"
  name="${rel##*/}"; name="${name%.*}"
  svg="assets/$topic/$name.svg"
  out="$svg"
  if [ "$pdfonly" -eq 1 ]; then
    case "$src" in *.py) continue ;; esac
    # Measured against the PDF, not the SVG: the SVG of a checkout is not ours to judge.
    out="assets/$topic/$name.pdf"
  fi
  stale "$out" "$src" || continue
  mkdir -p "assets/$topic"
  case "$src" in
    *.tex)
      mkdir -p "$BUILD/$topic"
      # The trailing ':' keeps TeX's default search path after the shared files.
      # Only tikz-tensors/tex, not the whole submodule: its tests and examples
      # hold .tex files a page must never pick up by name.
      # A fixed date makes the PDF (and its /ID) the same bytes on every build,
      # so a rebuilt page that did not change shows no diff.
      if ! TEXINPUTS="$TOOLS:$TOOLS/tikz-tensors/tex:${TEXINPUTS:-}" SOURCE_DATE_EPOCH=0 FORCE_SOURCE_DATE=1 \
          latexmk -r "$TOOLS/latexmkrc" -outdir="$BUILD/$topic" "$src" >/dev/null 2>&1; then
        echo "error: $src failed:" >&2
        grep -A4 '^!\|:[0-9]*:' "$BUILD/$topic/$name.log" >&2 || true
        exit 1
      fi
      # poppler is needed for the SVG. Without it (--pdf-only on a bare TeX
      # runner) the page count goes unchecked; the writer's own build checked it.
      if command -v pdfinfo >/dev/null 2>&1; then
        pages="$(pdfinfo "$BUILD/$topic/$name.pdf" | awk '/^Pages:/ {print $2}')"
        if [ "$pages" -ne 1 ]; then
          echo "error: $src has $pages pages; split it, one page per source" >&2
          exit 1
        fi
      fi
      [ "$pdfonly" -eq 1 ] || pdftocairo -svg "$BUILD/$topic/$name.pdf" "$svg"
      [ "$pdf" -eq 0 ] || cp "$BUILD/$topic/$name.pdf" "assets/$topic/$name.pdf"
      ;;
    *.py)
      # Write into .build/ and move on success, so a failed run (a missing
      # pyscf, say) leaves the existing SVG in place.
      mkdir -p "$BUILD/$topic"
      # No __pycache__ next to a shared module: nothing is written outside assets/.
      if ! PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$TOOLS${PYTHONPATH:+:$PYTHONPATH}" \
          "$PYTHON" "$src" "$BUILD/$topic/$name.svg" >/dev/null; then
        echo "error: $src failed (PYTHON=$PYTHON); $svg left as it was" >&2
        exit 1
      fi
      mv "$BUILD/$topic/$name.svg" "$svg"
      ;;
  esac
  echo "figures/$out"
done

# assets/ mirrors src/: drop an SVG or PDF whose source is gone, then empty topics.
find assets \( -name '*.svg' -o -name '*.pdf' \) | while IFS= read -r out; do
  rel="${out#assets/}"; base="src/${rel%.*}"
  [ -f "$base.tex" ] || [ -f "$base.py" ] || { rm "$out"; echo "removed figures/$out (no source)"; }
done
find assets -mindepth 1 -type d -empty -delete
