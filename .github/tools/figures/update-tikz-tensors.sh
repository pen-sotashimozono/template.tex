#!/bin/sh
# Vendor a pinned release of tikz-tensors (the TikZ format and theme shared by
# every figure repository) into .github/tools/figures/tikz-tensors/.
#
#   .github/tools/figures/update-tikz-tensors.sh v0.1.0
#
# The copy is committed, so a figure builds offline and the same everywhere
# until this script is run for a newer tag. build.sh puts tikz-tensors/tex on
# TEXINPUTS; pages write \usepackage{tikz-tensors}. theme.css is kept too, for
# the HTML notes and storyboards.
set -eu
TAG="${1:?usage: $0 <tag, e.g. v0.1.0>}"
DIR="$(cd "$(dirname "$0")" && pwd)/tikz-tensors"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
curl -sfL "https://github.com/pen-sotashimozono/tikz-tensors/archive/refs/tags/$TAG.tar.gz" \
  | tar xz -C "$TMP" --strip-components=1
mkdir -p "$DIR/tex" "$DIR/theme"
cp "$TMP"/tex/*.sty "$TMP"/tex/*.tex "$DIR/tex/"
cp "$TMP"/theme/theme.css "$TMP"/theme/tokens.toml "$DIR/theme/"
cp "$TMP"/LICENSE "$DIR/LICENSE"
echo "$TAG" > "$DIR/VERSION"
echo "tikz-tensors $TAG -> ${DIR#"$PWD"/}"
