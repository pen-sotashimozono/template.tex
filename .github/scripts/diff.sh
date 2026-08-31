#!/bin/sh
# Render a latexdiff between two revisions of one document, locally, with
# \input children flattened. Usage:
#
#   ./.github/scripts/diff.sh v0.1.2-main v0.1.3-main   # between two tags/commits
#   ./.github/scripts/diff.sh v0.1.2-main               # tag -> working tree
#   ./.github/scripts/diff.sh -d notes HEAD~5           # pick the document explicitly
#
# Output: out/diff-<from>..<to>.pdf
#
# The document is taken from the from-revision when it is a v<version>-<id>
# tag, since that is the usual way in; otherwise -d, or the single document in
# docs.toml when there is only one.
#
# Flattening matters: a document can keep its content in child .tex files, so
# a latexdiff of the root alone shows nothing when only a child changed. Each
# revision is checked out into its own worktree and flattened with latexpand
# first.
#
# To read changes as an agent, prefer plain text:
#   git diff v0.1.2-main v0.1.3-main -- '*.tex'
# This script is for a rendered, human-readable diff.
set -eu

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
PY="${PYTHON:-python3}"
command -v "$PY" >/dev/null 2>&1 || PY=python

DOC=''
if [ "${1:-}" = "-d" ]; then
  DOC="${2:?usage: $0 [-d DOCUMENT] <from-rev> [to-rev]}"
  shift 2
fi

FROM="${1:?usage: $0 [-d DOCUMENT] <from-rev> [to-rev]}"
TO="${2:-}"

IDS="$("$PY" .github/scripts/docs.py ids)"
if [ -z "$DOC" ]; then
  # v0.1.2-main -> main, but only if that is really a document
  CANDIDATE="${FROM##*-}"
  for ID in $IDS; do
    if [ "$ID" = "$CANDIDATE" ]; then
      DOC="$ID"
    fi
  done
fi
if [ -z "$DOC" ]; then
  if [ "$(echo "$IDS" | wc -l)" -eq 1 ]; then
    DOC="$IDS"
  else
    echo "cannot tell which document '$FROM' refers to; pass -d <id>" >&2
    echo "documents in docs.toml: $(echo "$IDS" | tr '\n' ' ')" >&2
    exit 1
  fi
fi
ROOT_TEX="$("$PY" .github/scripts/docs.py root "$DOC")"

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
(cd "$WORK/from" && latexpand "$ROOT_TEX" > "$WORK/from.tex" 2>/dev/null)

if [ -n "$TO" ]; then
  git worktree add -q --detach "$WORK/to" "$TO"
  (cd "$WORK/to" && latexpand "$ROOT_TEX" > "$WORK/to.tex" 2>/dev/null)
  LABEL="$TO"
else
  latexpand "$ROOT_TEX" > "$WORK/to.tex" 2>/dev/null
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
