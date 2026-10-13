#!/bin/sh
# aux_dir.sh [<latexmkrc>] -- print the directory where latexmk keeps the
# auxiliary files of a build (.aux, .toc, .bbl, .fls, .fdb_latexmk, ...), as the
# .latexmkrc sets it: $aux_dir, else $out_dir, else the working directory.
#
# It reads the plain string assignments of those two variables and runs
# nothing, so it gives the same answer on a writer's machine, in a container
# and on a runner, and it never starts a build. Keep both assignments as plain
# strings for it to find them.
rc="${1:-.latexmkrc}"
dir="$(perl -ne '
  $a = $2 if /^\s*\$aux_dir\s*=\s*([\x27"])(.*?)\1\s*;/;
  $o = $2 if /^\s*\$out_dir\s*=\s*([\x27"])(.*?)\1\s*;/;
  END { print defined $a ? $a : defined $o ? $o : "." }' "$rc" 2>/dev/null)"
echo "${dir:-.}"
