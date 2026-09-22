#!/bin/bash
# Export an export's source to PDF with Office (pptx: PowerPoint, docx: Word)
# and stamp it. macOS only.
#
#   ./.github/scripts/office2pdf.sh review
#
# Converts a copy inside the app's sandbox container: a file under Dropbox
# triggers a file-access dialog that hangs the AppleEvent. File references are
# built outside `tell`; inside it, `POSIX file <var>` fails with -4960/-9074.
set -euo pipefail

doc="${1:?usage: office2pdf.sh <export id from docs.toml>}"
here="$(cd "$(dirname "$0")" && pwd)"

{ read -r src; read -r pdf; read -r _; } < <(python3 "$here/exports.py" paths "$doc")
[ -f "$src" ] || { echo "error: $src does not exist" >&2; exit 1; }

case "${src##*.}" in
  pptx) app="Microsoft PowerPoint"; bundle="com.microsoft.Powerpoint" ;;
  docx) app="Microsoft Word";       bundle="com.microsoft.Word" ;;
  *)    echo "error: no exporter for $src" >&2; exit 1 ;;
esac

container="$HOME/Library/Containers/$bundle/Data"
[ -d "$container" ] || { echo "error: $app is not installed" >&2; exit 1; }
stage="$(mktemp -d "$container/office2pdf.XXXXXX")"
trap 'rm -rf "$stage"' EXIT
cp "$src" "$stage/"

if [ "$bundle" = com.microsoft.Powerpoint ]; then
  osascript - "$stage/$(basename "$src")" "$stage/out.pdf" <<'EOF'
on run argv
  set srcName to do shell script "basename " & quoted form of (item 1 of argv)
  set srcFile to POSIX file (item 1 of argv)
  set pdfFile to POSIX file (item 2 of argv)
  tell application "Microsoft PowerPoint"
    with timeout of 300 seconds
      repeat with p in presentations
        if name of p is srcName then error srcName & " is open in PowerPoint; save and close it first"
      end repeat
      open srcFile
      set pres to active presentation
      save pres in pdfFile as save as PDF
      close pres saving no
    end timeout
  end tell
end run
EOF
else
  osascript - "$stage/$(basename "$src")" "$stage/out.pdf" <<'EOF'
on run argv
  set srcName to do shell script "basename " & quoted form of (item 1 of argv)
  set srcFile to POSIX file (item 1 of argv)
  set pdfName to (POSIX file (item 2 of argv)) as text
  tell application "Microsoft Word"
    with timeout of 300 seconds
      repeat with d in documents
        if name of d is srcName then error srcName & " is open in Word; save and close it first"
      end repeat
      open srcFile
      set doc to active document
      save as doc file name pdfName file format format PDF
      close doc saving no
    end timeout
  end tell
end run
EOF
fi

mv "$stage/out.pdf" "$pdf"
python3 "$here/exports.py" stamp "$doc"
echo "$doc: exported $pdf"
