#!/bin/sh
# Populate refs/src/ with a greppable full text for every bibliography entry.
#
#   ./.github/scripts/fetch_sources.sh          # fill in what is missing
#   ./.github/scripts/fetch_sources.sh --force  # refetch everything
#
# Preference order per entry:
#   1. arXiv LaTeX source  -> refs/src/<bibkey>.tex   (doiget tex-source)
#      The arXiv id comes from the entry's `eprint` field, or from
#      `doiget link <doi>` (OpenAlex) when there is none.
#   2. PDF text extraction -> refs/src/<bibkey>.txt   (pdftotext refs/<bibkey>.pdf)
#
# LaTeX source is preferred because equations survive intact: you can grep for
# \label{...} and read an inequality's direction from the source instead of from
# a PDF extraction that silently drops Greek letters. Labels are also stable
# across the arXiv and published versions, whose equation NUMBERS differ.
set -eu

FORCE=0
[ "${1:-}" = "--force" ] && FORCE=1

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
command -v doiget >/dev/null || { echo "doiget not found" >&2; exit 1; }
mkdir -p refs/src

# key<TAB>eprint<TAB>doi per entry; the parse is shared with refs_sync.sh.
awk -f .github/scripts/bibentries.awk references.bib | tr -d '\015' > "$ROOT/.fetch_sources.tmp"

got=0; fell_back=0; missing=0
# Read through fd 3: doiget would otherwise consume the loop's stdin.
while IFS="$(printf '\t')" read -r key ep doi <&3; do
  [ -z "$key" ] && continue
  if [ "$FORCE" -eq 0 ] && { [ -f "refs/src/$key.tex" ] || [ -f "refs/src/$key.txt" ]; }; then
    got=$((got + 1)); continue
  fi

  aid="$ep"
  if [ "$aid" = "-" ] && [ "$doi" != "-" ]; then
    aid=$(doiget link "$doi" --mode json </dev/null 2>/dev/null \
          | sed -n 's/.*"arxiv": *"\([^"]*\)".*/\1/p' | head -1)
    [ -z "$aid" ] && aid="-"
  fi

  if [ "$aid" != "-" ] && doiget tex-source "$aid" </dev/null > "refs/src/$key.tex" 2>/dev/null \
     && [ -s "refs/src/$key.tex" ]; then
    echo "  tex   $key  ($aid)"; got=$((got + 1)); continue
  fi
  rm -f "refs/src/$key.tex"

  if [ -f "refs/$key.pdf" ] && command -v pdftotext >/dev/null \
     && pdftotext "refs/$key.pdf" "refs/src/$key.txt" 2>/dev/null && [ -s "refs/src/$key.txt" ]; then
    echo "  text  $key  (from PDF)"; fell_back=$((fell_back + 1)); continue
  fi
  rm -f "refs/src/$key.txt"
  echo "  none  $key  (no arXiv source, no local PDF)"; missing=$((missing + 1))
done 3< "$ROOT/.fetch_sources.tmp"
rm -f "$ROOT/.fetch_sources.tmp"

echo
echo "LaTeX source: $got   PDF text: $fell_back   unavailable: $missing"
