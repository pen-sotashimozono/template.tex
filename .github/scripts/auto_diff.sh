#!/bin/sh
# auto_diff.sh <root stem> -- after a build of a document whose table in
# docs.toml has `auto_diff = true`, render what changed since the last commit
# as out/<id>-diff-HEAD..working.pdf (diff.sh), in the background.
#
# Called by .latexmkrc. It does nothing in CI, for the build of a diff itself
# (no document has its stem), or while another one is still running.
set -eu
cd "$(dirname "$0")/../.."
[ -z "${CI:-}${GITHUB_ACTIONS:-}" ] || exit 0
PY="${PYTHON:-python3}"
"$PY" -c 'import tomllib' 2>/dev/null || PY="$(command -v python3.13 python3.12 python3.11 2>/dev/null | head -1)"
[ -n "$PY" ] || exit 0
export PYTHON="$PY"
stem="${1:?usage: auto_diff.sh <root stem>}"
AUX="$(sh .github/scripts/aux_dir.sh)"
for id in $("$PY" .github/scripts/docs.py ids); do
  root="$("$PY" .github/scripts/docs.py root "$id")"
  [ "$(basename "$root" .tex)" = "$stem" ] || continue
  [ "$("$PY" .github/scripts/docs.py get "$id" auto_diff false)" = true ] || exit 0
  mkdir -p "$AUX"
  find "$AUX"/auto-diff.lock -maxdepth 0 -mmin +30 -exec rmdir {} \; 2>/dev/null || true
  mkdir "$AUX"/auto-diff.lock 2>/dev/null || exit 0
  (
    sh .github/scripts/diff.sh -d "$id" HEAD > "$AUX"/auto-diff.log 2>&1 || true
    rmdir "$AUX"/auto-diff.lock
  ) > /dev/null 2>&1 &
  exit 0
done
