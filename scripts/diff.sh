#!/bin/sh
# Render a latexdiff between two revisions, locally, with \input children
# flattened. Usage:
#
#   ./scripts/diff.sh v0.1.2 v0.1.3   # between two tags/commits
#   ./scripts/diff.sh v0.1.2          # tag -> working tree
#
# Output: out/diff-<from>..<to>.pdf
#
# Flattening matters: this document can keep its content in child .tex files, so
# a latexdiff of main.tex alone shows nothing when only a child changed. Each
# revision is checked out into its own worktree and flattened with latexpand
# first.
#
# To read changes as an agent, prefer plain text:
#   git diff v0.1.2 v0.1.3 -- '*.tex'
# This script is for a rendered, human-readable diff.
set -eu

FROM="${1:?usage: $0 <from-rev> [to-rev]}"
TO="${2:-}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

command -v latexpand >/dev/null || { echo "latexpand not found (TeX Live)" >&2; exit 1; }
command -v latexdiff >/dev/null || { echo "latexdiff not found (TeX Live)" >&2; exit 1; }

WORK="$(mktemp -d)"
cleanup() {
  git worktree remove --force "$WORK/from" 2>/dev/null || true
  git worktree remove --force "$WORK/to" 2>/dev/null || true
  rm -rf "$WORK"
}
trap cleanup EXIT

git worktree add -q --detach "$WORK/from" "$FROM"
(cd "$WORK/from" && latexpand main.tex > "$WORK/from.tex" 2>/dev/null)

if [ -n "$TO" ]; then
  git worktree add -q --detach "$WORK/to" "$TO"
  (cd "$WORK/to" && latexpand main.tex > "$WORK/to.tex" 2>/dev/null)
  LABEL="$TO"
else
  latexpand main.tex > "$WORK/to.tex" 2>/dev/null
  LABEL="working"
fi

mkdir -p out
NAME="diff-${FROM}..${LABEL}"
latexdiff "$WORK/from.tex" "$WORK/to.tex" > "out/${NAME}.tex"
latexmk -lualatex -interaction=nonstopmode -outdir=out "out/${NAME}.tex" >/dev/null 2>&1 || true

if [ -f "out/${NAME}.pdf" ]; then
  echo "out/${NAME}.pdf"
else
  echo "PDF not produced; the annotated source is at out/${NAME}.tex" >&2
  exit 1
fi
