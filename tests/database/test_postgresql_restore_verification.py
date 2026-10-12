"""Tests der PostgreSQL-Wiederherstellungsprobe."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import Mock

import pytest
from sqlalchemy.engine import make_url

from openbilanz.database.postgresql_backup_service import (
    PostgreSQLBackupService,
)
from openbilanz.database.postgresql_restore_verification import (
    PostgreSQLRestoreVerificationService,
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
            "Die Tests dürfen ausschließlich "
            "'simpleob_migration_test' verwenden."
        )

    return url


def _config(database_url: str) -> Mock:
    config = Mock()
    config.database_url = database_url
    return config


def test_restore_verification_rejects_sqlite(
    tmp_path: Path,
) -> None:
    service = PostgreSQLRestoreVerificationService(
        application_config=_config("sqlite:///:memory:")
    )

    with pytest.raises(
        ValueError,
        match="nur für PostgreSQL",
    ):
        service.verify_backup(
            backup_path=tmp_path / "backup.dump"
        )


def test_restore_verification_rejects_missing_backup(
    database_url: str,
    tmp_path: Path,
) -> None:
    service = PostgreSQLRestoreVerificationService(
        application_config=_config(database_url)
    )

    with pytest.raises(
        ValueError,
        match="existiert nicht",
    ):
        service.verify_backup(
            backup_path=tmp_path / "missing.dump"
        )


def test_restore_verification_rejects_other_database(
    database_url: str,
    tmp_path: Path,
) -> None:
    other_url = make_url(database_url).set(
        database="andere_datenbank"
    )

    service = PostgreSQLRestoreVerificationService(
        application_config=_config(
            other_url.render_as_string(
                hide_password=False
            )
        )
    )

    with pytest.raises(
        ValueError,
        match="simpleob_migration_test",
    ):
        service.verify_backup(
            backup_path=tmp_path / "backup.dump"
        )


def test_restore_verification_succeeds(
    database_url: str,
    tmp_path: Path,
) -> None:
    """Eine Sicherung lässt sich in einer Testdatenbank einspielen."""
    config = _config(database_url)

    backup = tmp_path / "restore_test.dump"

    PostgreSQLBackupService(
        application_config=config
    ).create_backup(
        backup_path=backup
    )

    result = PostgreSQLRestoreVerificationService(
        application_config=config
    ).verify_backup(
        backup_path=backup
    )

    assert result.source_database == "simpleob_migration_test"
    assert result.backup_path == backup.resolve()
    assert result.restored_table_count > 0
