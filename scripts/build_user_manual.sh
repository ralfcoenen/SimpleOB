#!/usr/bin/env bash

set -euo pipefail

# ---------------------------------------------------------------------------
# SimpleOB – Benutzerhandbuch als PDF erzeugen
#
# Quelle:
#   docs/SimpleOB_Benutzerhandbuch.md
#
# Ausgabe:
#   docs/SimpleOB_Benutzerhandbuch.pdf
#
# Voraussetzungen:
#   - pandoc
#   - asciidoctor-pdf
#
# Die Markdown-Datei bleibt die alleinige gepflegte Quelle.
# Die AsciiDoc-Datei wird ausschließlich temporär erzeugt.
# ---------------------------------------------------------------------------

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

SOURCE_MD="${PROJECT_ROOT}/docs/SimpleOB_Benutzerhandbuch.md"
OUTPUT_PDF="${PROJECT_ROOT}/docs/SimpleOB_Benutzerhandbuch.pdf"

WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/simpleob-handbuch.XXXXXX")"
ADOC_FILE="${WORK_DIR}/SimpleOB_Benutzerhandbuch.adoc"

cleanup() {
    rm -rf "${WORK_DIR}"
}
trap cleanup EXIT

require_command() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "Fehler: Benötigtes Programm '$1' wurde nicht gefunden." >&2
        exit 1
    fi
}

require_command pandoc
require_command asciidoctor-pdf
require_command ruby

if [[ ! -f "${SOURCE_MD}" ]]; then
    echo "Fehler: Quelldatei nicht gefunden:" >&2
    echo "  ${SOURCE_MD}" >&2
    exit 1
fi

echo "SimpleOB – Benutzerhandbuch"
echo
echo "Quelle:"
echo "  ${SOURCE_MD}"
echo
echo "Ausgabe:"
echo "  ${OUTPUT_PDF}"
echo

echo "1/4 Markdown nach AsciiDoc konvertieren ..."

pandoc \
    "${SOURCE_MD}" \
    --from=gfm \
    --to=asciidoc \
    --standalone \
    --shift-heading-level-by=-1 \
    --output="${ADOC_FILE}"

echo "2/4 Pandoc-Anker entfernen ..."

ruby - "${ADOC_FILE}" <<'RUBY'
path = ARGV.fetch(0)

lines = File.readlines(path, chomp: true)

lines.reject! do |line|
  line.match?(/^\[\[.*\]\]$/)
end

File.write(path, lines.join("\n") + "\n")
RUBY

echo "3/4 Seitenumbrüche vor Hauptkapiteln einfügen ..."

ruby - "${ADOC_FILE}" <<'RUBY'
path = ARGV.fetch(0)

lines = File.readlines(path, chomp: true)
result = []

lines.each do |line|
  if line.start_with?("== ") && !result.empty?
    result << ""
    result << "<<<"
    result << ""
  end

  result << line
end

File.write(path, result.join("\n") + "\n")
RUBY

echo "4/4 PDF erzeugen ..."

asciidoctor-pdf \
    -a toc \
    -a toc-title="Inhaltsverzeichnis" \
    -a toclevels=2 \
    -a lang=de \
    -a pdf-page-size=A4 \
    -o "${OUTPUT_PDF}" \
    "${ADOC_FILE}"

echo
echo "PDF erfolgreich erzeugt:"
echo "  ${OUTPUT_PDF}"
