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
    python \
    pyinstaller
do
    if ! command -v "${command_name}" >/dev/null 2>&1; then
        echo >&2 \
            "Fehler: ${command_name} wurde in der aktuellen Build-Umgebung nicht gefunden."
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
# Ein Release-Build darf ausschließlich aus einem vollständig
# sauberen Git-Working-Tree erzeugt werden.
#

if [[ -n "$(git status --porcelain)" ]]; then
    echo >&2 \
        "Fehler: Der Git-Working-Tree ist nicht vollständig sauber."
    echo >&2
    git status --short >&2
    echo >&2
    echo >&2 \
        "Vor dem Build dürfen weder Änderungen noch untracked Dateien vorhanden sein."
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

echo
echo "SimpleOB macOS Build"
echo
echo "  Version: ${PROJECT_VERSION}"
echo "  ERiC SDK: ${SIMPLEOB_ERIC_SDK_ROOT}"
echo

#
# Anwendung bauen
#

pyinstaller \
    --clean \
    --noconfirm \
    --distpath "${PROJECT_ROOT}/dist" \
    --workpath "${PROJECT_ROOT}/build/pyinstaller-macos" \
    "${SCRIPT_DIR}/SimpleOB.spec"

#
# Ergebnis prüfen
#

APP_PATH="${PROJECT_ROOT}/dist/SimpleOB.app"

if [[ ! -d "${APP_PATH}" ]]; then
    echo >&2
    echo >&2 \
        "Fehler: SimpleOB.app wurde nach dem Build nicht gefunden:"
    echo >&2 \
        "  ${APP_PATH}"
    exit 1
fi

APP_VERSION="$(
    /usr/libexec/PlistBuddy \
        -c 'Print :CFBundleShortVersionString' \
        "${APP_PATH}/Contents/Info.plist"
)"

if [[ "${APP_VERSION}" != "${PROJECT_VERSION}" ]]; then
    echo >&2
    echo >&2 \
        "Fehler: Die gebaute App enthält nicht die erwartete Version."
    echo >&2
    echo >&2 \
        "  Projektversion: ${PROJECT_VERSION}"
    echo >&2 \
        "  App-Version:    ${APP_VERSION}"
    exit 1
fi

echo
echo "Build erfolgreich:"
echo
echo "  ${APP_PATH}"
echo "  Version: ${APP_VERSION}"
