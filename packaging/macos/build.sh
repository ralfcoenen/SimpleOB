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

if [[ -z "${SIMPLEOB_ERIC_SDK_ROOT:-}" ]]; then
    echo >&2 \
        "Fehler: SIMPLEOB_ERIC_SDK_ROOT ist nicht gesetzt."
    echo >&2 \
        "Der Pfad muss auf das Darwin-universal-Verzeichnis des ERiC-SDK zeigen."
    exit 1
fi

if ! command -v pyinstaller >/dev/null 2>&1; then
    echo >&2 \
        "Fehler: pyinstaller wurde in der aktuellen Build-Umgebung nicht gefunden."
    exit 1
fi

cd "${PROJECT_ROOT}"

pyinstaller \
    --clean \
    --noconfirm \
    --distpath "${PROJECT_ROOT}/dist" \
    --workpath "${PROJECT_ROOT}/build/pyinstaller-macos" \
    "${SCRIPT_DIR}/SimpleOB.spec"
