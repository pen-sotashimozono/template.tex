#!/bin/sh
# Raise a document's version in docs.toml by one semver step, and prepend its
# CHANGELOG stub.
#
#   ./scripts/bump.sh main patch "One line on what changed and why."
#   ./scripts/bump.sh --affected patch "..."   # every document this branch touched
#
# Every PR to main must carry exactly one such bump per document it changes
# (VersionCheck.yml), single-step from the CURRENT tip of main. If main moved
# while your branch was open, merge it in and re-run this script.
#
# --affected asks scripts/closure.py which documents this branch actually
# touched and bumps exactly those -- the same set CI will demand. It reads the
# build records under out/, so build first.
set -eu

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DOCS="$ROOT/scripts/docs.py"
CLOSURE="$ROOT/scripts/closure.py"
PY="${PYTHON:-python3}"
command -v "$PY" >/dev/null 2>&1 || PY=python

usage() {
  echo "usage: $0 <document|--affected> [patch|minor|major] [\"summary\"]" >&2
  echo "documents in docs.toml: $("$PY" "$DOCS" ids | tr '\n' ' ')" >&2
  exit 1
}

TARGET="${1:-}"
KIND="${2:-patch}"
SUMMARY="${3:-}"
[ -n "$TARGET" ] || usage
case "$KIND" in patch|minor|major) ;; *) usage ;; esac

if [ "$TARGET" = "--affected" ]; then
  BASE=main
  git -C "$ROOT" rev-parse --verify --quiet "$BASE" >/dev/null || BASE=origin/main
  DOC_LIST="$("$PY" "$CLOSURE" affected --base "$BASE" 2>/dev/null || true)"
  if [ -z "$DOC_LIST" ]; then
    echo "No document's dependency closure changed since $BASE — no bump needed."
    exit 0
  fi
  echo "Affected since $BASE: $(echo "$DOC_LIST" | tr '\n' ' ')"
else
  DOC_LIST="$TARGET"
fi

LOG="$ROOT/CHANGELOG.md"
MARK='<!-- new entries go directly below this line -->'
TOUCHED=''

for DOC in $DOC_LIST; do
  "$PY" "$DOCS" bump "$DOC" "$KIND"
  NEW="$("$PY" "$DOCS" version "$DOC")"
  TAG="${DOC}-v${NEW}"
  TOUCHED="${TOUCHED} ${TAG}"

  # A changelog stub per document, headed by the tag it will release under, so
  # Release.yml can lift the entry out by exact match.
  [ -f "$LOG" ] && grep -qF "$MARK" "$LOG" || continue
  if grep -q "^## $TAG " "$LOG"; then
    echo "CHANGELOG.md: entry for $TAG already present, left alone"
    continue
  fi
  entry="## $TAG — $(date +%Y-%m-%d)

${SUMMARY:-TODO: one paragraph on what changed and why.}"
  awk -v mark="$MARK" -v entry="$entry" '
    { print }
    $0 == mark && !done { print ""; print entry; done = 1 }
  ' "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
  echo "CHANGELOG.md: added an entry for $TAG"
  if [ -z "$SUMMARY" ]; then
    echo "  (fill in the TODO before opening the PR)"
  fi
done

echo "Will release on merge:${TOUCHED}"
if [ -f "$LOG" ]; then
  echo "Next: git add docs.toml CHANGELOG.md && git commit"
else
  echo "Next: git add docs.toml && git commit"
fi
