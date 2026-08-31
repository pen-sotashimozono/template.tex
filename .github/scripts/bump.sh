#!/bin/sh
# Raise a document's version in docs.toml by one semver step, and prepend its
# CHANGELOG stub.
#
#   ./.github/scripts/bump.sh main patch "One line on what changed and why."
#   ./.github/scripts/bump.sh --affected patch "..."   # every document this branch touched
#
# One step per document the PR changes, none for the ones it does not, measured
# from the CURRENT tip of main. If main moved, merge it in and re-run.
#
# --affected asks closure.py which documents this branch actually touched -- the
# same set CI will demand. It reads the build records under out/, so build
# first, and it compares commits, so commit the content first.
set -eu

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DOCS="$ROOT/.github/scripts/docs.py"
CLOSURE="$ROOT/.github/scripts/closure.py"
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
  AFFECTED="$("$PY" "$CLOSURE" affected --base "$BASE" 2>/dev/null || true)"

  # A document absent from the base branch is new, and the version check
  # accepts whatever version it arrives with -- there is nothing to step from.
  # Bumping it here would push it off its intended initial version.
  BASE_DOCS="$(git -C "$ROOT" show "$BASE:.github/docs.toml" 2>/dev/null > "$ROOT/.base-docs.tmp"     && "$PY" "$DOCS" ids --file "$ROOT/.base-docs.tmp" 2>/dev/null || true)"
  rm -f "$ROOT/.base-docs.tmp"

  DOC_LIST=''
  for DOC in $AFFECTED; do
    for KNOWN in $BASE_DOCS; do
      if [ "$DOC" = "$KNOWN" ]; then
        DOC_LIST="${DOC_LIST} ${DOC}"
      fi
    done
  done

  if [ -z "$DOC_LIST" ]; then
    echo "No existing document's dependency closure changed since $BASE — no bump needed."
    for DOC in $AFFECTED; do
      echo "  ($DOC is new; it keeps the version it was added with)"
    done
    exit 0
  fi
  echo "Affected since $BASE:${DOC_LIST}"
else
  DOC_LIST="$TARGET"
fi

LOG="$ROOT/.github/CHANGELOG.md"
MARK='<!-- new entries go directly below this line -->'
TOUCHED=''

for DOC in $DOC_LIST; do
  "$PY" "$DOCS" bump "$DOC" "$KIND"
  NEW="$("$PY" "$DOCS" version "$DOC")"
  TAG="v${NEW}-${DOC}"
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
  echo "Next: git add .github/docs.toml .github/CHANGELOG.md && git commit"
else
  echo "Next: git add .github/docs.toml && git commit"
fi
