"""Persistenz der ERiC-Datenschutz-Kenntnisnahme."""

from __future__ import annotations

import tomllib
from pathlib import Path


ERIC_PRIVACY_NOTICE_VERSION = "2021-07-01"

ERIC_PRIVACY_ACKNOWLEDGEMENT_FILENAME = (
    "eric_privacy_acknowledgement.toml"
)


def is_eric_privacy_acknowledged(
    data_dir: Path,
) -> bool:
    """Prüft die Kenntnisnahme der aktuellen ERiC-Datenschutzinformation."""

    path = (
        data_dir
        / ERIC_PRIVACY_ACKNOWLEDGEMENT_FILENAME
    )

    if not path.is_file():
        return False

    try:
        with path.open("rb") as file:
            data = tomllib.load(file)
    except (OSError, tomllib.TOMLDecodeError):
        return False

    eric_privacy = data.get(
        "eric_privacy",
        {},
    )

    return (
        eric_privacy.get("notice_version")
        == ERIC_PRIVACY_NOTICE_VERSION
    )


def save_eric_privacy_acknowledgement(
    data_dir: Path,
) -> None:
    """Speichert die Kenntnisnahme der aktuellen ERiC-Datenschutzinformation."""

    data_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    path = (
        data_dir
        / ERIC_PRIVACY_ACKNOWLEDGEMENT_FILENAME
    )

    path.write_text(
        (
            "[eric_privacy]\n"
            f'notice_version = "{ERIC_PRIVACY_NOTICE_VERSION}"\n'
        ),
        encoding="utf-8",
    )
