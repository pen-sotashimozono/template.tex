#!/bin/sh
# tikz-tensors (the TikZ format and theme every figure page uses) is a git
# submodule at .github/tools/figures/tikz-tensors/. Its main is the one
# canonical tikz-tensors and always a release (gated there); here it is either
# pinned at a release, or developed in place on a branch named after this
# project -- a proposal, which goes to tikz-tensors as a PR when you decide.
#
#   tikz-tensors.sh ensure         # make it present (build.sh and Initialize.yml call this)
#   tikz-tensors.sh pin v0.3.0     # build with that release; stages the pin
#   tikz-tensors.sh pin latest     # tikz-tensors' main, which is its newest release
#   tikz-tensors.sh dev <topic>    # develop in place on branch <project>/<topic>
#   tikz-tensors.sh status         # release or proposal, ahead/behind main, pushed?
#   tikz-tensors.sh check          # CI: fail if the pin is not on GitHub, warn if not a release
#
# ensure: a clone that did not --recurse-submodules gets `git submodule update
# --init`. A repository made from the template has .gitmodules but no pinned
# commit ("Use this template" drops it), so the submodule is added afresh at
# tikz-tensors' main. It also sets push.recurseSubmodules=check here, so git
# refuses to push a pin whose commit was never pushed to tikz-tensors.
# TIKZ_TENSORS_URL overrides the repository (the tests).
set -eu
URL="${TIKZ_TENSORS_URL:-https://github.com/pen-sotashimozono/tikz-tensors}"
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
REL=.github/tools/figures/tikz-tensors
SUB="$ROOT/$REL"
STY="$SUB/tex/tikz-tensors.sty"

git_root() { git -C "$ROOT" "$@"; }
git_sub() { git -C "$SUB" "$@"; }
die() { echo "error: $*" >&2; exit 1; }
sty_version() { sed -n 's/.*\\ProvidesPackage{tikz-tensors}\[[0-9/]* v\([0-9.]*\) .*/\1/p' "$1" | head -1; }
pinned() { git_root ls-files -s -- "$REL" | awk '$1 == "160000" {print $2}'; }
project() { basename "$(git_root remote get-url origin 2>/dev/null || echo "$ROOT")" .git | tr 'A-Z' 'a-z'; }
fetch() { git_sub fetch -q --tags origin '+refs/heads/*:refs/remotes/origin/*'; }

release_at() {  # <commit>: v<version> if its package is exactly that release, else nothing.
  # The version is the commit's own \ProvidesPackage line; a tag that merely
  # points at the commit does not count (it may disagree with the line).
  v="$(git_sub show "$1:tex/tikz-tensors.sty" 2>/dev/null | sed -n 's/.*\\ProvidesPackage{tikz-tensors}\[[0-9/]* v\([0-9.]*\) .*/\1/p' | head -1)"
  if [ -n "$v" ] && git_sub rev-parse -q --verify "refs/tags/v$v" >/dev/null \
      && git_sub diff --quiet "v$v" "$1" -- tex theme; then
    echo "v$v"
  fi
}

checkout() {  # <tag|latest>: check it out in the submodule; it must be a release
  fetch
  if [ "$1" = latest ]; then ref=origin/main
  else
    git_sub rev-parse -q --verify "refs/tags/$1" >/dev/null || die "tikz-tensors has no tag $1 ($URL)"
    ref="refs/tags/$1"
  fi
  commit="$(git_sub rev-parse "$ref^{commit}")"
  tag="$(release_at "$commit")"
  [ -n "$tag" ] || die "tikz-tensors $1 ($(git_sub rev-parse --short "$commit")) is not a release: its \\ProvidesPackage version has no tag with the same package"
  [ "$1" = latest ] || [ "$tag" = "$1" ] || die "tikz-tensors $1 says ${tag:-another version} in its \\ProvidesPackage line"
  git_sub checkout -q "$commit"
  echo "$tag"
}

ensure() {  # [tag|latest]: make the submodule present; a new one is added at it (default latest)
  git_root config push.recurseSubmodules check
  [ -f "$STY" ] && return 0
  if [ -n "$(pinned)" ]; then
    git_root submodule update --init -- "$REL" >&2 \
      || die "the pinned tikz-tensors commit $(pinned) is not on $URL; push it from inside $REL"
  else
    rm -rf "$SUB"
    git_root submodule add --force "$URL" "$REL" >&2
    tag="$(checkout "${1:-latest}")"
    git_root add .gitmodules "$REL"
    echo "tikz-tensors: added as a submodule at $tag (staged; commit it)" >&2
  fi
  [ -f "$STY" ] || die "$REL/tex/tikz-tensors.sty still missing"
}

describe() {  # <commit>: one line on what it is relative to tikz-tensors' main
  tag="$(release_at "$1")"
  counts="$(git_sub rev-list --left-right --count "origin/main...$1")"
  behind="$(echo "$counts" | awk '{print $1}')"; ahead="$(echo "$counts" | awk '{print $2}')"
  if [ -n "$tag" ]; then
    echo "release $tag (main: $ahead ahead, $behind behind)"
  else
    branches="$(git_sub branch -r --contains "$1" | sed 's#^ *origin/##' | grep -v '^HEAD' | tr '\n' ' ' | sed 's/ $//')"
    echo "proposal, not a release: on ${branches:-no pushed branch}; main: $ahead ahead, $behind behind"
  fi
}

case "${1:-}" in
  ensure)
    ensure ;;
  pin)
    target="${2:?usage: $0 pin <tag|latest>}"
    ensure "$target"
    tag="$(checkout "$target")"
    git_root add "$REL"
    echo "tikz-tensors: pinned at $tag (staged; commit it)" ;;
  dev)
    topic="${2:?usage: $0 dev <topic>}"
    ensure
    fetch
    branch="$(project)/$topic"
    if git_sub rev-parse -q --verify "refs/remotes/origin/$branch" >/dev/null; then
      git_sub switch -q -C "$branch" --track "origin/$branch"
    else
      git_sub switch -q -c "$branch"
    fi
    echo "tikz-tensors: on $branch. Edit $REL, build, commit and push inside it"
    echo "(git -C $REL push -u origin $branch), then git add $REL here." ;;
  status)
    ensure
    fetch
    head="$(git_sub rev-parse HEAD)"
    branch="$(git_sub symbolic-ref -q --short HEAD || echo 'no branch')"
    echo "tikz-tensors v$(sty_version "$STY") at $(git_sub rev-parse --short HEAD) ($branch)"
    echo "  $(describe "$head")"
    if [ -z "$(git_sub branch -r --contains "$head")" ] && [ -z "$(git_sub tag --points-at "$head")" ]; then
      echo "  not pushed: the commit exists only here (git -C $REL push -u origin <branch>)"
    fi
    [ -z "$(git_sub status --porcelain)" ] || echo "  uncommitted edits inside the submodule"
    [ "$(pinned)" = "$head" ] || echo "  differs from the commit this repository records (git add $REL)" ;;
  check)
    pin="$(pinned)"
    [ -n "$pin" ] || die "$REL is not a submodule here; run $0 ensure and commit"
    git_root submodule update --init -- "$REL" >/dev/null 2>&1 \
      || { echo "::error::the pinned tikz-tensors commit $pin is not on $URL: push it from inside $REL"; exit 1; }
    fetch
    line="$(describe "$pin")"
    case "$line" in
      release*) echo "tikz-tensors: $line. OK" ;;
      *"no pushed branch"*) echo "::error::tikz-tensors $pin: $line"; exit 1 ;;
      *) echo "::warning::tikz-tensors $(git_sub rev-parse --short "$pin"): $line" ;;
    esac ;;
  *)
    sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'; exit 2 ;;
esac
