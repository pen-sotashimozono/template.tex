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
echo "Next: git add VERSION && git commit"
