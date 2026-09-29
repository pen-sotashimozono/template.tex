#!/bin/sh
# Populate papers/src/ with a greppable full text for every bibliography entry.
#
#   ./.github/scripts/fetch_sources.sh          # fill in what is missing
#   ./.github/scripts/fetch_sources.sh --force  # refetch everything
#
# Preference order per entry:
#   1. arXiv LaTeX source  -> papers/src/<bibkey>.tex   (doiget tex-source)
#      The arXiv id comes from the entry's `eprint` field, or from
#      `doiget link <doi>` (OpenAlex) when there is none.
#   2. PDF text extraction -> papers/src/<bibkey>.txt   (pdftotext papers/<bibkey>.pdf)
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
mkdir -p papers/src

# LaTeX source for an arXiv id, on stdout.
#
# `doiget tex-source` is the preferred route, but doiget 0.6.0 does not carry
# that subcommand; fall back to the arXiv e-print endpoint so papers/src/ still
# gets LaTeX rather than a lossy PDF extraction. Most e-prints are a gzipped
# tar of the submission; a single-file submission is served bare-gzipped, so
# the download lands in a file rather than a pipe -- a pipe cannot be re-read
# to try the second form.
texsource() {
  doiget tex-source "$1" </dev/null 2>/dev/null && return 0
  _tf=$(mktemp) || return 1
  _ua="doiget-refs/1 (${DOIGET_CONTACT_EMAIL:-unknown})"
  if curl -sfL --max-time 180 -A "$_ua" "https://arxiv.org/e-print/$1" -o "$_tf"; then
    if tar tzf "$_tf" >/dev/null 2>&1; then
      tar xzOf "$_tf" '*.tex' 2>/dev/null
      rm -f "$_tf"; return 0
    fi
    if gzip -dc "$_tf" 2>/dev/null | grep -q .; then
      gzip -dc "$_tf" 2>/dev/null
      rm -f "$_tf"; return 0
    fi
  fi
  rm -f "$_tf"; return 1
}

# key<TAB>eprint<TAB>doi per entry; the parse is shared with refs_sync.sh.
awk -f .github/scripts/bibentries.awk references.bib | tr -d '\015' > "$ROOT/.fetch_sources.tmp"

got=0; fell_back=0; missing=0
# Read through fd 3: doiget would otherwise consume the loop's stdin.
while IFS="$(printf '\t')" read -r key ep doi <&3; do
  [ -z "$key" ] && continue
  if [ "$FORCE" -eq 0 ] && { [ -f "papers/src/$key.tex" ] || [ -f "papers/src/$key.txt" ]; }; then
    got=$((got + 1)); continue
  fi

  aid="$ep"
  if [ "$aid" = "-" ] && [ "$doi" != "-" ]; then
    aid=$(doiget link "$doi" --mode json </dev/null 2>/dev/null \
          | sed -n 's/.*"arxiv": *"\([^"]*\)".*/\1/p' | head -1)
    [ -z "$aid" ] && aid="-"
  fi

  if [ "$aid" != "-" ] && texsource "$aid" > "papers/src/$key.tex" 2>/dev/null \
     && [ -s "papers/src/$key.tex" ]; then
    echo "  tex   $key  ($aid)"; got=$((got + 1)); continue
  fi
  rm -f "papers/src/$key.tex"

  if [ -f "papers/$key.pdf" ] && command -v pdftotext >/dev/null \
     && pdftotext "papers/$key.pdf" "papers/src/$key.txt" 2>/dev/null && [ -s "papers/src/$key.txt" ]; then
    echo "  text  $key  (from PDF)"; fell_back=$((fell_back + 1)); continue
  fi
  rm -f "papers/src/$key.txt"
  echo "  none  $key  (no arXiv source, no local PDF)"; missing=$((missing + 1))
done 3< "$ROOT/.fetch_sources.tmp"
rm -f "$ROOT/.fetch_sources.tmp"

echo
echo "LaTeX source: $got   PDF text: $fell_back   unavailable: $missing"
