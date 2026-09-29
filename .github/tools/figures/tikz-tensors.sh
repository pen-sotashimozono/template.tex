#!/bin/sh
# tikz-tensors (the TikZ format and theme every figure page uses) is a git
# submodule at .github/tools/figures/tikz-tensors/: edit it in place, commit and
# push from inside it, and this repository records which commit it builds with.
#
#   .github/tools/figures/tikz-tensors.sh ensure       # make it present (build.sh calls this)
#   .github/tools/figures/tikz-tensors.sh pin v0.3.0   # build with that release; stages the pin
#   .github/tools/figures/tikz-tensors.sh pin latest   # the newest release
#   .github/tools/figures/tikz-tensors.sh status       # which version, and is it a release
#
# ensure: a clone that did not --recurse-submodules gets `git submodule update
# --init`. A repository made from the template has .gitmodules but no pinned
# commit (GitHub's "Use this template" drops submodules), so the submodule is
# added afresh at the newest release; Initialize.yml does this once, and
# build.sh does it for any checkout that still lacks it.
#
# pin: checks the tag out inside the submodule, confirms its \ProvidesPackage
# line carries the same version, and stages the new pin (commit it with the
# figures it changes). While you edit tikz-tensors itself the submodule may sit
# on any commit; `status` says when that commit is not a release, so pin a tag
# before merging. TIKZ_TENSORS_URL overrides the repository (the tests).
set -eu
URL="${TIKZ_TENSORS_URL:-https://github.com/pen-sotashimozono/tikz-tensors}"
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
REL=.github/tools/figures/tikz-tensors
SUB="$ROOT/$REL"
STY="$SUB/tex/tikz-tensors.sty"

git_root() { git -C "$ROOT" "$@"; }
latest_tag() {
  git ls-remote --tags --refs "$URL" 'v*' | sed 's#.*refs/tags/##' \
    | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' | sort -t. -k1.2,1n -k2,2n -k3,3n | tail -1
}
sty_version() { sed -n 's/.*\\ProvidesPackage{tikz-tensors}\[[0-9/]* v\([0-9.]*\) .*/\1/p' "$1" | head -1; }
pinned() { git_root ls-files -s -- "$REL" | awk '$1 == "160000" {print $2}'; }

checkout_tag() {  # <tag>: check the tag out in the submodule and check its version line
  git -C "$SUB" fetch -q --tags origin
  if ! git -C "$SUB" rev-parse -q --verify "refs/tags/$1" >/dev/null; then
    echo "error: tikz-tensors has no tag $1 ($URL)" >&2; exit 1
  fi
  git -C "$SUB" checkout -q "refs/tags/$1"
  v="$(sty_version "$STY")"
  if [ "v$v" != "$1" ]; then
    echo "error: tikz-tensors $1 says v$v in its \\ProvidesPackage line" >&2; exit 1
  fi
}

ensure() {  # [tag]: make the submodule present; a new one is added at tag (default: newest)
  [ -f "$STY" ] && return 0
  if [ -n "$(pinned)" ]; then
    git_root submodule update --init -- "$REL" >&2
  else
    tag="${1:-$(latest_tag)}"
    [ -n "$tag" ] || { echo "error: no release of tikz-tensors found at $URL" >&2; exit 1; }
    rm -rf "$SUB"
    git_root submodule add --force "$URL" "$REL" >&2
    checkout_tag "$tag"
    git_root add .gitmodules "$REL"
    echo "tikz-tensors: added as a submodule at $tag (staged; commit it)" >&2
  fi
  [ -f "$STY" ] || { echo "error: $REL/tex/tikz-tensors.sty still missing" >&2; exit 1; }
}

case "${1:-}" in
  ensure)
    ensure ;;
  pin)
    tag="${2:?usage: $0 pin <tag|latest>}"
    [ "$tag" != latest ] || tag="$(latest_tag)"
    ensure "$tag"
    checkout_tag "$tag"
    git_root add "$REL"
    echo "tikz-tensors: pinned at $tag (staged; commit it)" ;;
  status)
    ensure
    commit="$(git -C "$SUB" rev-parse --short HEAD)"
    tag="$(git -C "$SUB" describe --tags --exact-match HEAD 2>/dev/null || true)"
    dirty="$(git -C "$SUB" status --porcelain)"
    echo "tikz-tensors v$(sty_version "$STY") at $commit${tag:+ = release $tag}"
    [ -n "$tag" ] || echo "  not a release: pin a tag before merging ($0 pin <tag>)"
    [ -z "$dirty" ] || echo "  uncommitted edits inside the submodule"
    [ "$(pinned)" = "$(git -C "$SUB" rev-parse HEAD)" ] \
      || echo "  differs from the commit this repository records (git add $REL to record it)" ;;
  *)
    sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'; exit 2 ;;
esac
