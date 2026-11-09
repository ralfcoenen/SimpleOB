"""Tests des administrativen PostgreSQL-Backupdienstes."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest
from sqlalchemy.engine import make_url

from simpleob.database.connection_credentials import PostgreSQLCredentials
from simpleob.database.postgresql_backup_service import (
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


def test_backup_uses_and_removes_explicit_temporary_passfile(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config = Mock()
    config.database_url = (
        "postgresql+psycopg://testuser@localhost:5432/"
        "simpleob_migration_test"
    )
    service = PostgreSQLBackupService(
        application_config=config,
        credentials=PostgreSQLCredentials("one-time-secret"),
    )
    backup = tmp_path / "backup.dump"
    calls: list[tuple[list[str], dict[str, str], Path]] = []

    monkeypatch.setenv("PGPASSWORD", "ambient-secret")
    monkeypatch.setenv("PGPASSFILE", "/tmp/ambient-passfile")
    monkeypatch.setenv("PGSERVICE", "ambient-service")

    def fake_run(command, *, env, **_kwargs):
        passfile = Path(env["PGPASSFILE"])
        assert passfile.is_file()
        calls.append((command, env, passfile))
        if command[0] == "pg_dump":
            backup.write_bytes(b"archive")
        return Mock()

    monkeypatch.setattr(
        "simpleob.database.postgresql_backup_service.subprocess.run",
        fake_run,
    )

    result = service.create_backup(backup_path=backup)

    assert result.backup_size == len(b"archive")
    assert len(calls) == 2
    assert calls[0][2] == calls[1][2]
    assert calls[0][1]["PGPASSFILE"] != "/tmp/ambient-passfile"
    assert "PGPASSWORD" not in calls[0][1]
    assert "PGSERVICE" not in calls[0][1]
    assert not calls[0][2].exists()


def test_backup_removes_passfile_and_hides_subprocess_error(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config = Mock()
    config.database_url = (
        "postgresql+psycopg://testuser@localhost:5432/"
        "simpleob_migration_test"
    )
    service = PostgreSQLBackupService(
        application_config=config,
        credentials=PostgreSQLCredentials("one-time-secret"),
    )
    backup = tmp_path / "failed.dump"
    paths: list[Path] = []

    def failing_run(_command, *, env, **_kwargs):
        paths.append(Path(env["PGPASSFILE"]))
        raise subprocess.CalledProcessError(
            1,
            "pg_dump",
            stderr="diagnostic containing one-time-secret",
        )

    monkeypatch.setattr(
        "simpleob.database.postgresql_backup_service.subprocess.run",
        failing_run,
    )

    with pytest.raises(RuntimeError) as error:
        service.create_backup(backup_path=backup)

    assert "one-time-secret" not in str(error.value)
    assert error.value.__cause__ is None
    assert paths and not paths[0].exists()
    assert not backup.exists()
