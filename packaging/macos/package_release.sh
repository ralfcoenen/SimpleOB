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

if ! command -v python >/dev/null 2>&1; then
    echo >&2 \
        "Fehler: python wurde in der aktuellen Build-Umgebung nicht gefunden."
    exit 1
fi

APPLICATION_VERSION="$(
    python -c \
        'from importlib.metadata import version; print(version("openbilanz"))'
)"

if [[ -z "${SIMPLEOB_ERIC_SDK_ROOT:-}" ]]; then
    echo >&2 \
        "Fehler: SIMPLEOB_ERIC_SDK_ROOT ist nicht gesetzt."
    echo >&2 \
        "Der Pfad muss auf das Darwin-universal-Verzeichnis des ERiC-SDK zeigen."
    exit 1
fi

APP_SOURCE="${PROJECT_ROOT}/dist/SimpleOB.app"
MANUAL_SOURCE="${PROJECT_ROOT}/docs/SimpleOB_Benutzerhandbuch.pdf"

TEST_CERTIFICATE_SOURCE="${SIMPLEOB_ERIC_SDK_ROOT}/Beispiel/ericdemo-python/test-softidnr-pse.pfx"

RELEASE_ROOT="${PROJECT_ROOT}/dist/release"
RELEASE_DIR="${RELEASE_ROOT}/SimpleOB"
RELEASE_ARCHIVE="${RELEASE_ROOT}/SimpleOB-${APPLICATION_VERSION}-macOS.zip"
TEST_CERTIFICATE_DIR="${RELEASE_DIR}/ELSTER-Testzertifikat"

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

if [[ ! -f "${TEST_CERTIFICATE_SOURCE}" ]]; then
    echo >&2 \
        "Fehler: Das ELSTER-Testzertifikat wurde im ERiC-SDK nicht gefunden:"
    echo >&2 \
        "  ${TEST_CERTIFICATE_SOURCE}"
    exit 1
fi

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

(
    cd "${RELEASE_ROOT}"
    ditto \
        -c \
        -k \
        --keepParent \
        "SimpleOB" \
        "$(basename "${RELEASE_ARCHIVE}")"
)

echo
echo "SimpleOB-Release wurde erstellt:"
echo
echo "  ${RELEASE_DIR}"
echo
echo
echo "Enthalten:"
echo "  SimpleOB.app"
echo "  SimpleOB_Benutzerhandbuch.pdf"
echo "  ELSTER-Testzertifikat/test-softidnr-pse.pfx"
echo
echo "Auslieferungsarchiv:"
echo "  ${RELEASE_ARCHIVE}"
