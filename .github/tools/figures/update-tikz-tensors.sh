#!/bin/sh
# Vendor a pinned release of tikz-tensors (the TikZ format and theme shared by
# every figure repository) into .github/tools/figures/tikz-tensors/.
#
#   .github/tools/figures/update-tikz-tensors.sh v0.1.0
#
# The copy is committed, so a figure builds offline and the same everywhere
# until this script is run for a newer tag. build.sh puts tikz-tensors/tex on
# TEXINPUTS; pages write \usepackage{tikz-tensors}. theme.css is kept too, for
# the HTML notes and storyboards. TIKZ_TENSORS_URL overrides the download URL
# (the tests point it at a local file:// tarball).
set -eu
TAG="${1:?usage: $0 <tag, e.g. v0.1.0>}"
URL="${TIKZ_TENSORS_URL:-https://github.com/pen-sotashimozono/tikz-tensors/archive/refs/tags/$TAG.tar.gz}"
DIR="$(cd "$(dirname "$0")" && pwd)/tikz-tensors"
TMP="$(mktemp -d)"
NEW="$DIR.new.$$"
trap 'rm -rf "$TMP" "$NEW"' EXIT HUP INT TERM

# Download to a file, not through a pipe: in `curl | tar` the pipeline's status
# is tar's, so a bad tag or a dropped connection would go unnoticed.
if ! curl -sfL "$URL" -o "$TMP/release.tar.gz"; then
  echo "error: could not download tikz-tensors $TAG ($URL); vendored copy left as it was" >&2
  exit 1
fi
mkdir "$TMP/src"
if ! tar xzf "$TMP/release.tar.gz" -C "$TMP/src" --strip-components=1; then
  echo "error: tikz-tensors $TAG: not a readable tarball; vendored copy left as it was" >&2
  exit 1
fi

# Assemble the whole new copy beside the old one, check every file is there,
# then swap it in: a failure never leaves tex/ from one tag and VERSION from another.
mkdir -p "$NEW/tex" "$NEW/theme"
for f in tex/tikz-tensors.sty tex/tikz-tensors-colors.tex theme/theme.css theme/tokens.toml LICENSE; do
  if [ ! -f "$TMP/src/$f" ]; then
    echo "error: tikz-tensors $TAG has no $f; vendored copy left as it was" >&2
    exit 1
  fi
  cp "$TMP/src/$f" "$NEW/$f"
done
echo "$TAG" > "$NEW/VERSION"
rm -rf "$DIR.old"
if [ -d "$DIR" ]; then mv "$DIR" "$DIR.old"; fi
mv "$NEW" "$DIR"
rm -rf "$DIR.old"
echo "tikz-tensors $TAG -> ${DIR#"$PWD"/}"
