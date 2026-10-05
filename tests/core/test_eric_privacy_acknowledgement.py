"""Tests für die ERiC-Datenschutz-Kenntnisnahme."""

from pathlib import Path

from openbilanz.core.eric_privacy_acknowledgement import (
    ERIC_PRIVACY_ACKNOWLEDGEMENT_FILENAME,
    ERIC_PRIVACY_NOTICE_VERSION,
    is_eric_privacy_acknowledged,
    save_eric_privacy_acknowledgement,
)


def test_missing_acknowledgement_is_not_current(
    tmp_path: Path,
) -> None:
    assert not is_eric_privacy_acknowledged(
        tmp_path
    )


def test_current_acknowledgement_is_recognized(
    tmp_path: Path,
) -> None:
    save_eric_privacy_acknowledgement(
        tmp_path
    )

    assert is_eric_privacy_acknowledged(
        tmp_path
    )


def test_saved_acknowledgement_contains_current_version(
    tmp_path: Path,
) -> None:
    save_eric_privacy_acknowledgement(
        tmp_path
    )

    path = (
        tmp_path
        / ERIC_PRIVACY_ACKNOWLEDGEMENT_FILENAME
    )

    content = path.read_text(
        encoding="utf-8"
    )

    assert (
        f'notice_version = "{ERIC_PRIVACY_NOTICE_VERSION}"'
        in content
    )


def test_old_acknowledgement_is_not_current(
    tmp_path: Path,
) -> None:
    path = (
        tmp_path
        / ERIC_PRIVACY_ACKNOWLEDGEMENT_FILENAME
    )

    path.write_text(
        (
            "[eric_privacy]\n"
            'notice_version = "2020-01-01"\n'
        ),
        encoding="utf-8",
    )

    assert not is_eric_privacy_acknowledged(
        tmp_path
    )


def test_invalid_acknowledgement_is_not_current(
    tmp_path: Path,
) -> None:
    path = (
        tmp_path
        / ERIC_PRIVACY_ACKNOWLEDGEMENT_FILENAME
    )

    path.write_text(
        "not valid toml = [",
        encoding="utf-8",
    )

    assert not is_eric_privacy_acknowledged(
        tmp_path
    )
