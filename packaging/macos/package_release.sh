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
    python \
    git \
    ditto \
    codesign
do
    if ! command -v "${command_name}" >/dev/null 2>&1; then
        echo >&2 \
            "Fehler: ${command_name} wurde nicht gefunden."
        exit 1
    fi
done

if [[ -z "${SIMPLEOB_ERIC_SDK_ROOT:-}" ]]; then
    echo >&2 \
        "Fehler: SIMPLEOB_ERIC_SDK_ROOT ist nicht gesetzt."
    echo >&2 \
        "Der Pfad muss auf das Darwin-universal-Verzeichnis des ERiC-SDK zeigen."
    exit 1
fi

#
# Ein Release-Paket darf nur aus einem vollständig sauberen
# Git-Working-Tree erzeugt werden.
#

if [[ -n "$(git status --porcelain)" ]]; then
    echo >&2 \
        "Fehler: Der Git-Working-Tree ist nicht vollständig sauber."
    echo >&2
    git status --short >&2
    echo >&2
    echo >&2 \
        "Vor dem Packaging dürfen weder Änderungen noch untracked Dateien vorhanden sein."
    exit 1
fi

#
# Versionskonsistenz
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
    echo >&2
    echo >&2 \
        "Bitte zuerst die Paket-Metadaten aktualisieren."
    exit 1
fi

APPLICATION_VERSION="${PROJECT_VERSION}"

#
# Quellen und Ziele
#

APP_SOURCE="${PROJECT_ROOT}/dist/SimpleOB.app"
MANUAL_SOURCE="${PROJECT_ROOT}/docs/SimpleOB_Benutzerhandbuch.pdf"

TEST_CERTIFICATE_SOURCE="${SIMPLEOB_ERIC_SDK_ROOT}/Beispiel/ericdemo-python/test-softidnr-pse.pfx"

RELEASE_ROOT="${PROJECT_ROOT}/dist/release"
RELEASE_DIR="${RELEASE_ROOT}/SimpleOB"
RELEASE_ARCHIVE="${RELEASE_ROOT}/SimpleOB-${APPLICATION_VERSION}-macOS.zip"
TEST_CERTIFICATE_DIR="${RELEASE_DIR}/ELSTER-Testzertifikat"

#
# Quelldateien prüfen
#

if [[ ! -d "${APP_SOURCE}" ]]; then
    echo >&2 \
        "Fehler: SimpleOB.app wurde nicht gefunden:"
    echo >&2 \
        "  ${APP_SOURCE}"
    echo >&2 \
        "Bitte zuerst packaging/macos/build.sh ausführen."
    exit 1
fi

if [[ ! -f "${MANUAL_SOURCE}" ]]; then
    echo >&2 \
        "Fehler: Das Benutzerhandbuch wurde nicht gefunden:"
    echo >&2 \
        "  ${MANUAL_SOURCE}"
    echo >&2 \
        "Bitte zuerst scripts/build_user_manual.sh ausführen."
    exit 1
fi

if [[ ! -s "${MANUAL_SOURCE}" ]]; then
    echo >&2 \
        "Fehler: Das Benutzerhandbuch ist leer:"
    echo >&2 \
        "  ${MANUAL_SOURCE}"
    exit 1
fi

if [[ ! -f "${TEST_CERTIFICATE_SOURCE}" ]]; then
    echo >&2 \
        "Fehler: Das ELSTER-Testzertifikat wurde im ERiC-SDK nicht gefunden:"
    echo >&2 \
        "  ${TEST_CERTIFICATE_SOURCE}"
    exit 1
fi

#
# Prüfen, ob die gebaute App tatsächlich zur Release-Version gehört.
#

APP_VERSION="$(
    /usr/libexec/PlistBuddy \
        -c 'Print :CFBundleShortVersionString' \
        "${APP_SOURCE}/Contents/Info.plist"
)"

if [[ "${APP_VERSION}" != "${APPLICATION_VERSION}" ]]; then
    echo >&2 \
        "Fehler: Die gebaute SimpleOB.app hat nicht die erwartete Version."
    echo >&2
    echo >&2 \
        "  Projektversion: ${APPLICATION_VERSION}"
    echo >&2 \
        "  App-Version:    ${APP_VERSION}"
    echo >&2
    echo >&2 \
        "Bitte SimpleOB.app mit packaging/macos/build.sh neu bauen."
    exit 1
fi

#
# Release-Verzeichnis erzeugen
#

rm -rf "${RELEASE_DIR}"
rm -f "${RELEASE_ARCHIVE}"

mkdir -p "${TEST_CERTIFICATE_DIR}"

cp -R \
    "${APP_SOURCE}" \
    "${RELEASE_DIR}/SimpleOB.app"

cp \
    "${MANUAL_SOURCE}" \
    "${RELEASE_DIR}/SimpleOB_Benutzerhandbuch.pdf"

cp \
    "${TEST_CERTIFICATE_SOURCE}" \
    "${TEST_CERTIFICATE_DIR}/test-softidnr-pse.pfx"

#
# ZIP erzeugen
#

(
    cd "${RELEASE_ROOT}"

    ditto \
        -c \
        -k \
        --keepParent \
        "SimpleOB" \
        "$(basename "${RELEASE_ARCHIVE}")"
)

if [[ ! -s "${RELEASE_ARCHIVE}" ]]; then
    echo >&2 \
        "Fehler: Das Release-Archiv wurde nicht korrekt erzeugt."
    exit 1
fi

#
# Das tatsächlich auszuliefernde ZIP erneut entpacken und prüfen.
#

VERIFY_DIR="$(
    mktemp -d "${TMPDIR:-/tmp}/simpleob-release-verify.XXXXXX"
)"

cleanup() {
    rm -rf "${VERIFY_DIR}"
}

trap cleanup EXIT

ditto \
    -x \
    -k \
    "${RELEASE_ARCHIVE}" \
    "${VERIFY_DIR}"

VERIFIED_RELEASE_DIR="${VERIFY_DIR}/SimpleOB"
VERIFIED_APP="${VERIFIED_RELEASE_DIR}/SimpleOB.app"
VERIFIED_MANUAL="${VERIFIED_RELEASE_DIR}/SimpleOB_Benutzerhandbuch.pdf"
VERIFIED_CERTIFICATE="${VERIFIED_RELEASE_DIR}/ELSTER-Testzertifikat/test-softidnr-pse.pfx"

if [[ ! -d "${VERIFIED_APP}" ]]; then
    echo >&2 \
        "Fehler: SimpleOB.app fehlt im entpackten Release."
    exit 1
fi

if [[ ! -s "${VERIFIED_MANUAL}" ]]; then
    echo >&2 \
        "Fehler: Das Benutzerhandbuch fehlt oder ist leer im entpackten Release."
    exit 1
fi

if [[ ! -f "${VERIFIED_CERTIFICATE}" ]]; then
    echo >&2 \
        "Fehler: Das ELSTER-Testzertifikat fehlt im entpackten Release."
    exit 1
fi

if find "${VERIFY_DIR}" \
    -name '__MACOSX' \
    -print \
    -quit \
    | grep -q .
then
    echo >&2 \
        "Fehler: Das Release-Archiv enthält ein __MACOSX-Verzeichnis."
    exit 1
fi

if ! cmp \
    "${TEST_CERTIFICATE_SOURCE}" \
    "${VERIFIED_CERTIFICATE}"
then
    echo >&2 \
        "Fehler: Das ELSTER-Testzertifikat im Release stimmt nicht mit der SDK-Datei überein."
    exit 1
fi

VERIFIED_APP_VERSION="$(
    /usr/libexec/PlistBuddy \
        -c 'Print :CFBundleShortVersionString' \
        "${VERIFIED_APP}/Contents/Info.plist"
)"

if [[ "${VERIFIED_APP_VERSION}" != "${APPLICATION_VERSION}" ]]; then
    echo >&2 \
        "Fehler: Die App-Version im entpackten Release stimmt nicht."
    echo >&2
    echo >&2 \
        "  Erwartet: ${APPLICATION_VERSION}"
    echo >&2 \
        "  Gefunden: ${VERIFIED_APP_VERSION}"
    exit 1
fi

echo
echo "Prüfe Codesignatur des entpackten Release ..."

codesign \
    --verify \
    --deep \
    --strict \
    --verbose=2 \
    "${VERIFIED_APP}"

echo
echo "Release-Prüfung erfolgreich:"
echo
echo "  Version:          ${APPLICATION_VERSION}"
echo "  App-Signatur:     OK"
echo "  Benutzerhandbuch: OK"
echo "  Testzertifikat:   OK"
echo "  __MACOSX:         nicht vorhanden"
echo
echo "SimpleOB-Release wurde erstellt:"
echo
echo "  ${RELEASE_DIR}"
echo
echo "Auslieferungsarchiv:"
echo "  ${RELEASE_ARCHIVE}"
