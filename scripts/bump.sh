#!/bin/sh
# Bump VERSION by one semver step. Usage: ./scripts/bump.sh [patch|minor|major]
#
# Every PR to main must carry exactly one such bump (VersionCheck.yml), and the
# bump must be single-step from the CURRENT tip of main. If main moved while
# your branch was open, rebase first and re-run this script.
set -eu

KIND="${1:-patch}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FILE="$ROOT/VERSION"

CUR="$(tr -d ' \t\r\n' < "$FILE")"
case "$CUR" in
  [0-9]*.[0-9]*.[0-9]*) ;;
  *) echo "VERSION '$CUR' is not in X.Y.Z form" >&2; exit 1 ;;
esac

M="${CUR%%.*}"
REST="${CUR#*.}"
m="${REST%%.*}"
p="${REST#*.}"

case "$KIND" in
  patch) NEW="$M.$m.$((p + 1))" ;;
  minor) NEW="$M.$((m + 1)).0" ;;
  major) NEW="$((M + 1)).0.0" ;;
  *) echo "usage: $0 [patch|minor|major]" >&2; exit 1 ;;
esac

printf '%s\n' "$NEW" > "$FILE"
echo "VERSION: $CUR -> $NEW ($KIND)"

# Prepend a changelog stub so the release notes exist as text in the repo.
SUMMARY="${2:-}"
LOG="$ROOT/CHANGELOG.md"
MARK='<!-- new entries go directly below this line -->'
if [ -f "$LOG" ] && grep -qF "$MARK" "$LOG"; then
  if grep -q "^## $NEW " "$LOG"; then
    echo "CHANGELOG.md: entry for $NEW already present, left alone"
  else
    entry="## $NEW — $(date +%Y-%m-%d)

${SUMMARY:-TODO: one paragraph on what changed and why.}"
    awk -v mark="$MARK" -v entry="$entry" '
      { print }
      $0 == mark && !done { print ""; print entry; done = 1 }
    ' "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
    echo "CHANGELOG.md: added an entry for $NEW${SUMMARY:+ }"
    [ -z "$SUMMARY" ] && echo "  (fill in the TODO before opening the PR)"
  fi
  echo "Next: git add VERSION CHANGELOG.md && git commit"
else
  echo "Next: git add VERSION && git commit"
fi
