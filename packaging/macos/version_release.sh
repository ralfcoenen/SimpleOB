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

if [[ $# -ne 1 ]]; then
    echo >&2 "Verwendung:"
    echo >&2 "  packaging/macos/version_release.sh VERSION"
    echo >&2
    echo >&2 "Beispiel:"
    echo >&2 "  packaging/macos/version_release.sh 0.47.2"
    exit 1
fi

NEW_VERSION="$1"
NEW_TAG="v${NEW_VERSION}"

if [[ ! "${NEW_VERSION}" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo >&2 \
        "Fehler: Ungültige Versionsnummer '${NEW_VERSION}'."
    echo >&2 \
        "Erwartet wird MAJOR.MINOR.PATCH, z. B. 0.47.2."
    exit 1
fi

for command_name in git python; do
    if ! command -v "${command_name}" >/dev/null 2>&1; then
        echo >&2 \
            "Fehler: ${command_name} wurde nicht gefunden."
        exit 1
    fi
done

#
# Ein Release darf ausschließlich aus einem vollständig sauberen
# Git-Working-Tree begonnen werden. Das umfasst ausdrücklich auch
# untracked Dateien.
#
if [[ -n "$(git status --porcelain)" ]]; then
    echo >&2 \
        "Fehler: Der Git-Working-Tree ist nicht vollständig sauber."
    echo >&2
    git status --short >&2
    echo >&2
    echo >&2 \
        "Vor der Versionierung dürfen weder Änderungen noch untracked Dateien vorhanden sein."
    exit 1
fi

CURRENT_VERSION="$(
    python - <<'PY'
from pathlib import Path
import tomllib

with Path("pyproject.toml").open("rb") as file:
    data = tomllib.load(file)

print(data["project"]["version"])
PY
)"

if [[ "${CURRENT_VERSION}" == "${NEW_VERSION}" ]]; then
    echo >&2 \
        "Fehler: Die aktuelle Version ist bereits ${NEW_VERSION}."
    exit 1
fi

#
# Vorhandene Release-Tags werden niemals überschrieben oder verschoben.
#
if git rev-parse \
    --verify \
    --quiet \
    "refs/tags/${NEW_TAG}" \
    >/dev/null
then
    echo >&2 \
        "Fehler: Der lokale Tag ${NEW_TAG} existiert bereits."
    exit 1
fi

if git ls-remote \
    --exit-code \
    --tags \
    origin \
    "refs/tags/${NEW_TAG}" \
    >/dev/null 2>&1
then
    echo >&2 \
        "Fehler: Der Tag ${NEW_TAG} existiert bereits auf origin."
    exit 1
fi

echo
echo "SimpleOB-Versionierung"
echo
echo "  Aktuelle Version: ${CURRENT_VERSION}"
echo "  Neue Version:      ${NEW_VERSION}"
echo "  Vorgesehener Tag:  ${NEW_TAG}"
echo

read -r -p \
    "Version auf ${NEW_VERSION} setzen und Release-Commit vorbereiten? [y/N] " \
    confirmation

case "${confirmation}" in
    y|Y|yes|YES|Yes)
        ;;
    *)
        echo "Abgebrochen."
        exit 1
        ;;
esac

python - "${CURRENT_VERSION}" "${NEW_VERSION}" <<'PY'
from pathlib import Path
import sys

path = Path("pyproject.toml")
old_version = sys.argv[1]
new_version = sys.argv[2]

text = path.read_text(encoding="utf-8")

old_line = f'version = "{old_version}"'
new_line = f'version = "{new_version}"'

if text.count(old_line) != 1:
    raise SystemExit(
        "Fehler: Die bisherige Versionszeile wurde nicht genau einmal gefunden."
    )

path.write_text(
    text.replace(old_line, new_line, 1),
    encoding="utf-8",
)
PY

echo
echo "Aktualisiere die installierten Paket-Metadaten ..."

if ! python -m pip install --no-deps -e .; then
    echo >&2
    echo >&2 \
        "Fehler: Die Paket-Metadaten konnten nicht aktualisiert werden."
    echo >&2 \
        "pyproject.toml bleibt geändert und muss geprüft werden."
    exit 1
fi

INSTALLED_VERSION="$(
    python -c \
        'from importlib.metadata import version; print(version("openbilanz"))'
)"

PROJECT_VERSION="$(
    python - <<'PY'
from pathlib import Path
import tomllib

with Path("pyproject.toml").open("rb") as file:
    data = tomllib.load(file)

print(data["project"]["version"])
PY
)"

if [[ "${PROJECT_VERSION}" != "${NEW_VERSION}" ]]; then
    echo >&2 \
        "Fehler: pyproject.toml enthält Version ${PROJECT_VERSION}, erwartet wurde ${NEW_VERSION}."
    exit 1
fi

if [[ "${INSTALLED_VERSION}" != "${NEW_VERSION}" ]]; then
    echo >&2 \
        "Fehler: Installierte Paketversion ist ${INSTALLED_VERSION}, erwartet wurde ${NEW_VERSION}."
    exit 1
fi

echo
echo "Versionsprüfung erfolgreich:"
echo "  pyproject.toml:  ${PROJECT_VERSION}"
echo "  Paket-Metadaten: ${INSTALLED_VERSION}"
echo

git diff --check -- pyproject.toml
git diff -- pyproject.toml

echo
read -r -p \
    "Release-Commit 'Release ${NEW_TAG}' jetzt erstellen? [y/N] " \
    commit_confirmation

case "${commit_confirmation}" in
    y|Y|yes|YES|Yes)
        ;;
    *)
        echo
        echo "Kein Commit erstellt."
        echo "pyproject.toml enthält jetzt Version ${NEW_VERSION}."
        exit 1
        ;;
esac

git add -- pyproject.toml

git commit \
    -m "Release ${NEW_TAG}" \
    -- \
    pyproject.toml

echo
echo "Versionierung abgeschlossen."
echo
echo "  Version: ${NEW_VERSION}"
echo "  Commit:  $(git rev-parse --short HEAD)"
echo
echo
echo "Noch nicht ausgeführt:"
echo "  - Build"
echo "  - Packaging"
echo "  - Push"
echo "  - Tag"
echo "  - GitHub Release"
