"""Tests der PostgreSQL-Wiederherstellungsprobe."""

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
from simpleob.database.postgresql_restore_verification import (
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
            backup_path=tmp_path / "backup.dump",
            confirmed_source_database="andere_datenbank",
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
            backup_path=tmp_path / "missing.dump",
            confirmed_source_database="simpleob_migration_test",
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
        match="bestätigte Quelldatenbank",
    ):
        service.verify_backup(
            backup_path=tmp_path / "backup.dump",
            confirmed_source_database="simpleob_migration_test",
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
        backup_path=backup,
    )

    result = PostgreSQLRestoreVerificationService(
        application_config=config
    ).verify_backup(
        backup_path=backup,
        confirmed_source_database="simpleob_migration_test",
    )

    assert result.source_database == "simpleob_migration_test"
    assert result.backup_path == backup.resolve()
    assert result.restored_table_count > 0


def _mock_restore_engines(monkeypatch):
    admin_connection = Mock()
    admin_context = Mock()
    admin_context.__enter__ = Mock(return_value=admin_connection)
    admin_context.__exit__ = Mock(return_value=False)
    admin_engine = Mock()
    admin_engine.connect.return_value = admin_context

    restored_connection = Mock()
    restored_connection.execute.return_value.scalar_one.return_value = 2
    restored_context = Mock()
    restored_context.__enter__ = Mock(return_value=restored_connection)
    restored_context.__exit__ = Mock(return_value=False)
    restored_engine = Mock()
    restored_engine.connect.return_value = restored_context

    create_engine = Mock(side_effect=[admin_engine, restored_engine])
    monkeypatch.setattr(
        "simpleob.database.postgresql_restore_verification.create_engine",
        create_engine,
    )
    return create_engine, admin_engine, restored_engine


def test_restore_uses_explicit_credentials_for_cli_and_sqlalchemy(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config = _config(
        "postgresql+psycopg://testuser@localhost:5432/"
        "simpleob_migration_test"
    )
    service = PostgreSQLRestoreVerificationService(
        application_config=config,
        credentials=PostgreSQLCredentials("one-time-secret"),
    )
    backup = tmp_path / "restore.dump"
    backup.write_bytes(b"archive")
    create_engine, _admin_engine, _restored_engine = _mock_restore_engines(
        monkeypatch
    )
    subprocess_calls: list[
        tuple[list[str], dict[str, str], Path, str]
    ] = []

    monkeypatch.setenv("PGPASSWORD", "ambient-secret")
    monkeypatch.setenv("PGPASSFILE", "/tmp/ambient-passfile")
    monkeypatch.setenv("PGSERVICE", "ambient-service")

    def fake_run(command, *, env, **_kwargs):
        passfile = Path(env["PGPASSFILE"])
        assert passfile.is_file()
        subprocess_calls.append(
            (
                command,
                env,
                passfile,
                passfile.read_text(encoding="utf-8"),
            )
        )
        return Mock()

    monkeypatch.setattr(
        "simpleob.database.postgresql_restore_verification.subprocess.run",
        fake_run,
    )

    result = service.verify_backup(backup_path=backup, confirmed_source_database="simpleob_migration_test")

    assert result.restored_table_count == 2
    assert len(subprocess_calls) == 1
    assert "PGPASSWORD" not in subprocess_calls[0][1]
    assert "PGSERVICE" not in subprocess_calls[0][1]
    assert subprocess_calls[0][1]["PGPASSFILE"] != "/tmp/ambient-passfile"
    assert subprocess_calls[0][3] == (
        "localhost:5432:*:testuser:one-time-secret\n"
    )
    assert not subprocess_calls[0][2].exists()

    engine_calls = create_engine.call_args_list
    assert engine_calls[0].kwargs["connect_args"] == {
        "password": "one-time-secret"
    }
    assert engine_calls[1].kwargs["connect_args"] == {
        "password": "one-time-secret"
    }


def test_restore_failure_removes_passfile_and_hides_subprocess_error(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config = _config(
        "postgresql+psycopg://testuser@localhost:5432/"
        "simpleob_migration_test"
    )
    service = PostgreSQLRestoreVerificationService(
        application_config=config,
        credentials=PostgreSQLCredentials("one-time-secret"),
    )
    backup = tmp_path / "restore-failure.dump"
    backup.write_bytes(b"archive")
    _mock_restore_engines(monkeypatch)
    passfiles: list[Path] = []

    def failing_run(_command, *, env, **_kwargs):
        passfiles.append(Path(env["PGPASSFILE"]))
        raise subprocess.CalledProcessError(
            1,
            "pg_restore",
            stderr="diagnostic containing one-time-secret",
        )

    monkeypatch.setattr(
        "simpleob.database.postgresql_restore_verification.subprocess.run",
        failing_run,
    )

    with pytest.raises(RuntimeError) as error:
        service.verify_backup(backup_path=backup, confirmed_source_database="simpleob_migration_test")

    assert "one-time-secret" not in str(error.value)
    assert error.value.__cause__ is None
    assert passfiles and not passfiles[0].exists()
