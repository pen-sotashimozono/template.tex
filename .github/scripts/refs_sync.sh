#!/bin/sh
# Give every bibliography entry its PDF at refs/<bibkey>.pdf, from the doiget
# store.
#
#   ./.github/scripts/refs_sync.sh          # fill in what is missing
#   ./.github/scripts/refs_sync.sh --force  # re-copy everything
#
# references.bib is the source of truth for *which* works; the store is the
# machine-wide cache they come from; refs/ is this project's copy. This script
# is the link between them, which otherwise runs by hand per entry and drifts.
#
# The store defaults to ./papers under the current directory, so running doiget
# from a paper repository silently builds a second store inside it. Set
# DOIGET_STORE_ROOT to one fixed path and every project shares one cache.
set -eu

FORCE=0
[ "${1:-}" = "--force" ] && FORCE=1

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
command -v doiget >/dev/null || { echo "doiget not found" >&2; exit 1; }
PY="${PYTHON:-python3}"
command -v "$PY" >/dev/null 2>&1 || PY=python

# Ask doiget where the store is rather than re-deriving its resolution order.
# Backslash via octal 134: a literal one does not survive every layer that
# edits this file. Quoting differs between the config and env-var forms.
STORE="$(doiget config show 2>/dev/null \
  | sed -n 's/^store_root = //p' | tr -d "\"'" | tr '\134' '/')"
[ -n "$STORE" ] || { echo "could not resolve the doiget store root" >&2; exit 1; }
echo "store: $STORE"
case "$STORE" in
  "$ROOT"/*|"$ROOT")
    echo "  warning: the store is inside this repository. Set DOIGET_STORE_ROOT" >&2
    echo "  to a path outside it, or every project keeps its own copy." >&2
    ;;
esac

mkdir -p refs
awk -f .github/scripts/bibentries.awk references.bib | tr -d '\r' > "$ROOT/.refs_sync.tmp"

have=0; got=0; missing=0
# Read through fd 3: doiget would otherwise consume the loop's stdin.
while IFS="$(printf '\t')" read -r key ep doi <&3; do
  [ -z "$key" ] && continue
  if [ "$FORCE" -eq 0 ] && [ -f "refs/$key.pdf" ]; then
    have=$((have + 1)); continue
  fi

  ref="$ep"
  [ "$ref" = "-" ] && ref="$doi"
  if [ "$ref" = "-" ]; then
    echo "  none  $key  (entry carries neither eprint nor doi)"
    missing=$((missing + 1)); continue
  fi

  # fetch is idempotent: a no-op once the ref is in the store.
  doiget fetch "$ref" </dev/null >/dev/null 2>&1 || true

  rel="$(doiget info "$ref" --mode json </dev/null 2>/dev/null \
    | "$PY" -c 'import json,sys
try:
    print(json.load(sys.stdin)["metadata"].get("pdf_path", ""))
except Exception:
    print("")' 2>/dev/null)"

  if [ -n "$rel" ] && [ -f "$STORE/$rel" ]; then
    cp "$STORE/$rel" "refs/$key.pdf"
    echo "  pdf   $key  ($ref)"; got=$((got + 1))
  else
    echo "  none  $key  ($ref -- no open-access PDF in the store)"
    missing=$((missing + 1))
  fi
done 3< "$ROOT/.refs_sync.tmp"
rm -f "$ROOT/.refs_sync.tmp"

echo
echo "already present: $have   copied: $got   unavailable: $missing"
if [ "$missing" -gt 0 ]; then
  echo "Entries without a PDF are fine: cite them and note the absence."
fi
