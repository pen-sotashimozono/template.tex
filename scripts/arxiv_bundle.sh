#!/bin/sh
# Build a document's arXiv submission bundle, and prove it compiles on its own.
#
#   ./scripts/arxiv_bundle.sh <document> [dest-dir]
#
# The bundle is flattened, not copied. A root that pulls content in through
# \input is not self-contained, and arXiv gets only what is inside the tarball,
# so an unflattened bundle fails there while every build here stays green. That
# is not hypothetical: the bundle did exactly this until it was caught by hand.
#
# The verification is the reason this is a script rather than three lines in a
# workflow. Producing the bundle is easy; noticing when it stops building is
# not, and nothing else in CI ever opens it. It is compiled in a throwaway copy
# so the build products do not end up inside the bundle that ships.
set -eu

DOC="${1:?usage: $0 <document> [dest-dir]}"
DEST="${2:-arxiv-src}"

REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"
PY="${PYTHON:-python3}"
command -v "$PY" >/dev/null 2>&1 || PY=python

ROOT_TEX="$("$PY" scripts/docs.py root "$DOC")"
STEM="$(basename "$ROOT_TEX" .tex)"

command -v latexpand >/dev/null || { echo "latexpand not found (TeX Live)" >&2; exit 1; }
command -v latexmk   >/dev/null || { echo "latexmk not found (TeX Live)" >&2; exit 1; }

mkdir -p "$DEST"
latexpand "$ROOT_TEX" > "$DEST/$STEM.tex"

# arXiv runs bibtex only if asked; shipping the .bbl is the usual way round it.
if [ -f "out/$STEM.bbl" ]; then
  cp "out/$STEM.bbl" "$DEST/"
else
  echo "::warning::$DOC: out/$STEM.bbl is missing, so the bundle has no bibliography. Build $ROOT_TEX first." >&2
fi

if [ -d figures ]; then
  find figures -name '*.pdf' | while IFS= read -r f; do cp "$f" "$DEST/"; done
fi

echo "$DOC: bundle contents"
ls -1 "$DEST" | sed 's/^/  /'

# Compile a copy, from nothing but what the tarball carries.
VERIFY="$(mktemp -d)"
cp "$DEST"/* "$VERIFY"/
if (cd "$VERIFY" && latexmk -lualatex -interaction=nonstopmode "$STEM.tex" > verify.log 2>&1); then
  echo "$DOC: bundle compiles standalone."
else
  echo "::error::$DOC: the arXiv submission bundle does not compile on its own." >&2
  echo "Anything the root reads through \input must be flattened into it." >&2
  grep -aE "LaTeX Error|Emergency stop|not found|Undefined control sequence" "$VERIFY/verify.log" \
    | head -10 | sed 's/^/  /' >&2
  exit 1
fi
