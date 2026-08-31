# One line per bibliography entry: key<TAB>eprint<TAB>doi, with "-" for absent.
#
# Shared by fetch_sources.sh and refs_sync.sh. Two consumers parsing the same
# file two ways is how they end up disagreeing about which entries exist.
#
#   awk -f .github/scripts/bibentries.awk references.bib | tr -d '\r'
#
# tr -d '\r' at the call site matters: a CR from a Windows checkout ends up
# inside the DOI and every lookup fails.

/^@/ {
  if (key != "") print key "\t" ep "\t" doi
  key = ""; ep = "-"; doi = "-"
  if (match($0, /\{[^,]+,/)) {
    key = substr($0, RSTART + 1, RLENGTH - 2)
    gsub(/[ \t]/, "", key)
  }
}
/eprint[ \t]*=/ { if (match($0, /\{[^}]*\}/)) ep  = substr($0, RSTART + 1, RLENGTH - 2) }
/doi[ \t]*=/    { if (match($0, /\{[^}]*\}/)) doi = substr($0, RSTART + 1, RLENGTH - 2) }
END { if (key != "") print key "\t" ep "\t" doi }
