#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(
    cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1
    pwd
)"

PROJECT_ROOT="$(
    cd -- "${SCRIPT_DIR}/../.." >/dev/null 2>&1
    pwd
)"

cd "${PROJECT_ROOT}"

#
# Voraussetzungen
#

for command_name in \
    git \
    gh \
    python
do
    if ! command -v "${command_name}" >/dev/null 2>&1; then
        echo >&2 \
            "Fehler: ${command_name} wurde nicht gefunden."
        exit 1
    fi
done

if ! gh auth status >/dev/null 2>&1; then
    echo >&2 \
        "Fehler: Keine funktionierende GitHub-CLI-Anmeldung gefunden."
    echo >&2 \
        "Bitte zuerst 'gh auth login' ausführen."
    exit 1
fi

#
# Git-Zustand
#

if [[ -n "$(git status --porcelain)" ]]; then
    echo >&2 \
        "Fehler: Der Git-Working-Tree ist nicht vollständig sauber."
    echo >&2
    git status --short >&2
    echo >&2
    echo >&2 \
        "Vor der Veröffentlichung dürfen weder Änderungen noch untracked Dateien vorhanden sein."
    exit 1
fi

CURRENT_BRANCH="$(
    git branch --show-current
)"

if [[ "${CURRENT_BRANCH}" != "main" ]]; then
    echo >&2 \
        "Fehler: Veröffentlichung ist nur vom Branch 'main' erlaubt."
    echo >&2 \
        "Aktueller Branch: ${CURRENT_BRANCH}"
    exit 1
fi

if ! git remote get-url origin >/dev/null 2>&1; then
    echo >&2 \
        "Fehler: Git-Remote 'origin' wurde nicht gefunden."
    exit 1
fi

echo "Aktualisiere Remote-Referenzen ..."

git fetch origin

LOCAL_HEAD="$(
    git rev-parse HEAD
)"

REMOTE_HEAD="$(
    git rev-parse origin/main
)"

if [[ "${LOCAL_HEAD}" != "${REMOTE_HEAD}" ]]; then
    echo >&2
    echo >&2 \
        "Fehler: Lokaler main und origin/main stimmen nicht überein."
    echo >&2
    echo >&2 \
        "  HEAD:        ${LOCAL_HEAD}"
    echo >&2 \
        "  origin/main: ${REMOTE_HEAD}"
    echo >&2
    echo >&2 \
        "Bitte den aktuellen main zuerst bewusst zu origin pushen."
    exit 1
fi

#
# Version
#

PROJECT_VERSION="$(
    python - <<'PY'
from pathlib import Path
import tomllib

with Path("pyproject.toml").open("rb") as file:
    data = tomllib.load(file)

print(data["project"]["version"])
PY
)"

INSTALLED_VERSION="$(
    python -c \
        'from importlib.metadata import version; print(version("openbilanz"))'
)"

if [[ "${PROJECT_VERSION}" != "${INSTALLED_VERSION}" ]]; then
    echo >&2 \
        "Fehler: Die Projekt- und Paketversionen stimmen nicht überein."
    echo >&2
    echo >&2 \
        "  pyproject.toml:  ${PROJECT_VERSION}"
    echo >&2 \
        "  Paket-Metadaten: ${INSTALLED_VERSION}"
    exit 1
fi

RELEASE_TAG="v${PROJECT_VERSION}"
RELEASE_TITLE="SimpleOB ${RELEASE_TAG}"
RELEASE_ARCHIVE="${PROJECT_ROOT}/dist/release/SimpleOB-${PROJECT_VERSION}-macOS.zip"

#
# Release-Artefakt
#

if [[ ! -s "${RELEASE_ARCHIVE}" ]]; then
    echo >&2 \
        "Fehler: Das Release-Archiv wurde nicht gefunden oder ist leer:"
    echo >&2 \
        "  ${RELEASE_ARCHIVE}"
    echo >&2
    echo >&2 \
        "Bitte zuerst packaging/macos/package_release.sh ausführen."
    exit 1
fi


#
# LGPL-Quellarchive vor der Veröffentlichung prüfen.
#

QT_SOURCE_DIR="${HOME}/SimpleOB-LGPL-Sources/Qt-6.11.2"
GETTEXT_SOURCE_DIR="${HOME}/SimpleOB-LGPL-Sources/gettext-1.0"

SOURCE_ARCHIVES=(
    "${QT_SOURCE_DIR}/qtbase-everywhere-src-6.11.2.tar.xz"
    "${QT_SOURCE_DIR}/qtsvg-everywhere-src-6.11.2.tar.xz"
    "${QT_SOURCE_DIR}/pyside-setup-everywhere-src-6.11.2.zip"
    "${GETTEXT_SOURCE_DIR}/gettext-1.0.tar.gz"
)

SOURCE_SHA256=(
    "5b2e00eccaf5a4d8c14134ffa0ea8dfd0a35ae1ffc7f8d87fa4305a1ed23cf22"
    "d594337feca84c26fb67fe87b85e6a5c12fda404b611d905f9d138210c311876"
    "c0fdd62b91a1d36d5ee2e1fb71050a32fbc93fcdeef0fdcb41d29afaaf00d9b5"
    "85d99b79c981a404874c02e0342176cf75c7698e2b51fe41031cf6526d974f1a"
)

for index in "${!SOURCE_ARCHIVES[@]}"; do
    archive="${SOURCE_ARCHIVES[$index]}"
    expected_sha="${SOURCE_SHA256[$index]}"

    if [[ ! -s "${archive}" ]]; then
        echo >&2 "Fehler: LGPL-Quellarchiv fehlt oder ist leer:"
        echo >&2 "  ${archive}"
        exit 1
    fi

    actual_sha="$(
        shasum -a 256 "${archive}" | awk '{print $1}'
    )"

    if [[ "${actual_sha}" != "${expected_sha}" ]]; then
        echo >&2 "Fehler: SHA-256 stimmt nicht überein:"
        echo >&2 "  ${archive}"
        exit 1
    fi

    echo "LGPL-Quellarchiv geprüft: $(basename "${archive}")"
done

#
# Vorhandene Tags und Releases niemals überschreiben.
#

if git rev-parse \
    --verify \
    --quiet \
    "refs/tags/${RELEASE_TAG}" \
    >/dev/null
then
    echo >&2 \
        "Fehler: Der lokale Tag ${RELEASE_TAG} existiert bereits."
    exit 1
fi

if git ls-remote \
    --exit-code \
    --tags \
    origin \
    "refs/tags/${RELEASE_TAG}" \
    >/dev/null 2>&1
then
    echo >&2 \
        "Fehler: Der Tag ${RELEASE_TAG} existiert bereits auf origin."
    exit 1
fi

if gh release view \
    "${RELEASE_TAG}" \
    >/dev/null 2>&1
then
    echo >&2 \
        "Fehler: Der GitHub Release ${RELEASE_TAG} existiert bereits."
    exit 1
fi

#
# Zusammenfassung und ausdrückliche Freigabe.
#

echo
echo "SimpleOB-Veröffentlichung"
echo
echo "  Version:       ${PROJECT_VERSION}"
echo "  Tag:           ${RELEASE_TAG}"
echo "  Commit:        ${LOCAL_HEAD}"
echo "  Branch:        ${CURRENT_BRANCH}"
echo "  Release-Datei: ${RELEASE_ARCHIVE}"
echo
echo "Folgende Schritte werden ausgeführt:"
echo "  1. Annotierten Git-Tag ${RELEASE_TAG} erstellen"
echo "  2. Tag zu origin pushen"
echo "  3. GitHub Release '${RELEASE_TITLE}' veröffentlichen"
echo "  4. Release-ZIP hochladen"
echo

read -r -p \
    "Release ${RELEASE_TAG} jetzt veröffentlichen? [y/N] " \
    confirmation

case "${confirmation}" in
    y|Y|yes|YES|Yes)
        ;;
    *)
        echo "Abgebrochen."
        exit 0
        ;;
esac

#
# Release Notes.
#

RELEASE_NOTES_FILE="$(
    mktemp "${TMPDIR:-/tmp}/simpleob-release-notes.XXXXXX"
)"

CHECKSUM_FILE="$(
    mktemp -d "${TMPDIR:-/tmp}/simpleob-checksums.XXXXXX"
)/SHA256SUMS"

cleanup() {
    rm -f "${RELEASE_NOTES_FILE}"
    rm -rf "$(dirname "${CHECKSUM_FILE}")"
}

trap cleanup EXIT

for index in "${!SOURCE_ARCHIVES[@]}"; do
    printf '%s  %s\n' \
        "${SOURCE_SHA256[$index]}" \
        "$(basename "${SOURCE_ARCHIVES[$index]}")"
done > "${CHECKSUM_FILE}"

cat > "${RELEASE_NOTES_FILE}" <<EOF_NOTES
## SimpleOB ${RELEASE_TAG}

Diese Version stellt das aktuelle macOS-Auslieferungspaket von SimpleOB bereit.

### Inhalt des Auslieferungspakets

- SimpleOB.app
- SimpleOB_Benutzerhandbuch.pdf
- ELSTER-Testzertifikat/test-softidnr-pse.pfx

### Installation

SimpleOB wird derzeit ohne Apple-Developer-ID und ohne Apple-Notarisierung
ausgeliefert. Hinweise zur erstmaligen Freigabe unter macOS befinden sich im
Benutzerhandbuch.

### ELSTER

Das mitgelieferte Testzertifikat ist ausschließlich für Testübermittlungen
vorgesehen. Vor einer produktiven Übermittlung muss in SimpleOB das persönliche
ELSTER-Zertifikat ausgewählt werden.

### LGPL-Quellcode

Die zu dieser Version gehörenden Quellarchive für Qt, PySide6,
Shiboken6 und GNU gettext stehen als separate Downloads
in diesem GitHub Release bereit.

Die Lizenztexte sowie Hinweise zum Austausch LGPL-lizenzierter
Bibliotheken befinden sich im SimpleOB-App-Bundle.
EOF_NOTES

#
# Tag erstellen und veröffentlichen.
#

git tag \
    -a "${RELEASE_TAG}" \
    -m "Release ${RELEASE_TAG}" \
    "${LOCAL_HEAD}"

TAG_COMMIT="$(
    git rev-list -n 1 "${RELEASE_TAG}"
)"

if [[ "${TAG_COMMIT}" != "${LOCAL_HEAD}" ]]; then
    echo >&2 \
        "Fehler: Der erzeugte Tag zeigt nicht auf HEAD."
    exit 1
fi

git push origin "${RELEASE_TAG}"

#
# GitHub Release erstellen.
#

if ! gh release create \
    "${RELEASE_TAG}" \
    "${RELEASE_ARCHIVE}" \
    "${SOURCE_ARCHIVES[@]}" \
    "${CHECKSUM_FILE}" \
    --title "${RELEASE_TITLE}" \
    --notes-file "${RELEASE_NOTES_FILE}" \
    --latest
then
    echo >&2
    echo >&2 \
        "Fehler: Der Git-Tag wurde bereits veröffentlicht,"
    echo >&2 \
        "aber der GitHub Release konnte nicht erstellt werden."
    echo >&2
    echo >&2 \
        "Der vorhandene Tag wird NICHT automatisch gelöscht oder verschoben."
    echo >&2 \
        "Bitte den Fehler prüfen und den GitHub Release anschließend gezielt erstellen."
    exit 1
fi

echo
echo "GitHub Release erfolgreich veröffentlicht:"
echo
echo "  ${RELEASE_TITLE}"
echo "  ${RELEASE_ARCHIVE}"
echo
echo "  Commit: ${LOCAL_HEAD}"
