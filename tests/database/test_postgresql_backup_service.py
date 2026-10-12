"""Tests des administrativen PostgreSQL-Backupdienstes."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import Mock

import pytest
from sqlalchemy.engine import make_url

from openbilanz.database.postgresql_backup_service import (
    PostgreSQLBackupService,
)


@pytest.fixture
def database_url() -> str:
    url = os.environ.get("SIMPLEOB_POSTGRES_TEST_URL")

    if not url:
        pytest.skip(
            "SIMPLEOB_POSTGRES_TEST_URL ist nicht gesetzt."
        )

    if make_url(url).database != "simpleob_migration_test":
        pytest.fail(
            "Der Test darf ausschließlich "
            "'simpleob_migration_test' verwenden."
        )

    return url


def _service(database_url: str) -> PostgreSQLBackupService:
    config = Mock()
    config.database_url = database_url

    return PostgreSQLBackupService(
        application_config=config
    )


def test_backup_rejects_sqlite(tmp_path: Path) -> None:
    service = _service("sqlite:///:memory:")

    with pytest.raises(
        ValueError,
        match="nur für PostgreSQL",
    ):
        service.create_backup(
            backup_path=tmp_path / "backup.dump"
        )


def test_backup_rejects_existing_file(
    database_url: str,
    tmp_path: Path,
) -> None:
    backup = tmp_path / "existing.dump"
    backup.write_bytes(b"vorhandene Daten")

    service = _service(database_url)

    with pytest.raises(FileExistsError):
        service.create_backup(
            backup_path=backup
        )

    assert backup.read_bytes() == b"vorhandene Daten"


def test_backup_creates_valid_archive(
    database_url: str,
    tmp_path: Path,
) -> None:
    """Erstellt ein lesbares Archiv der PostgreSQL-Testdatenbank."""
    backup = tmp_path / "simpleob_migration_test.dump"

    result = _service(database_url).create_backup(
        backup_path=backup
    )

    assert result.backup_path == backup.resolve()
    assert result.database_name == "simpleob_migration_test"
    assert result.backup_size > 0
    assert backup.is_file()
