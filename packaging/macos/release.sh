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

if [[ "$#" -ne 1 ]]; then
    echo >&2 "Verwendung:"
    echo >&2 "  packaging/macos/release.sh VERSION"
    echo >&2
    echo >&2 "Beispiel:"
    echo >&2 "  packaging/macos/release.sh 0.47.2"
    exit 1
fi

RELEASE_VERSION="$1"

cd "${PROJECT_ROOT}"

#
# Der Orchestrator startet nur aus einem vollständig sauberen
# Repository. Die aufgerufenen Einzelskripte führen zusätzlich
# ihre eigenen Sicherheitsprüfungen aus.
#

if [[ -n "$(git status --porcelain)" ]]; then
    echo >&2 \
        "Fehler: Der Git-Working-Tree ist nicht vollständig sauber."
    echo >&2
    git status --short >&2
    echo >&2
    echo >&2 \
        "Vor der Release-Vorbereitung dürfen weder Änderungen noch untracked Dateien vorhanden sein."
    exit 1
fi

echo
echo "SimpleOB Release vorbereiten"
echo
echo "  Zielversion: ${RELEASE_VERSION}"
echo
echo "Ablauf:"
echo "  1. Version setzen und Release-Commit erzeugen"
echo "  2. macOS-App bauen"
echo "  3. Auslieferungspaket erzeugen und prüfen"
echo
echo "Nicht automatisch ausgeführt:"
echo "  - git push origin main"
echo "  - Git-Tag erzeugen"
echo "  - GitHub Release veröffentlichen"
echo

read -r -p \
    "Release ${RELEASE_VERSION} jetzt vorbereiten? [y/N] " \
    CONFIRMATION

case "${CONFIRMATION}" in
    y|Y|yes|YES|Yes|ja|JA|Ja)
        ;;
    *)
        echo
        echo "Release-Vorbereitung abgebrochen."
        exit 0
        ;;
esac

echo
echo "============================================================"
echo "1/3 Versionierung"
echo "============================================================"
echo

"${SCRIPT_DIR}/version_release.sh" "${RELEASE_VERSION}"

echo
echo "============================================================"
echo "2/3 macOS-Build"
echo "============================================================"
echo

"${SCRIPT_DIR}/build.sh"

echo
echo "============================================================"
echo "3/3 Release-Paket"
echo "============================================================"
echo

"${SCRIPT_DIR}/package_release.sh"

RELEASE_ARCHIVE="$(
    printf '%s/dist/release/SimpleOB-%s-macOS.zip' \
        "${PROJECT_ROOT}" \
        "${RELEASE_VERSION}"
)"

echo
echo "============================================================"
echo "Release-Vorbereitung abgeschlossen"
echo "============================================================"
echo
echo "Version:"
echo "  ${RELEASE_VERSION}"
echo
echo "Auslieferungsarchiv:"
echo "  ${RELEASE_ARCHIVE}"
echo
echo "Das Release wurde noch NICHT veröffentlicht."
echo
echo "Nächste Schritte:"
echo
echo "  1. Die gebaute SimpleOB.app praktisch testen."
echo "  2. Das Auslieferungsarchiv bei Bedarf zusätzlich prüfen."
echo "  3. Den Release-Commit bewusst pushen:"
echo
echo "       git push origin main"
echo
echo "  4. Danach veröffentlichen:"
echo
echo "       packaging/macos/publish_release.sh"
echo
