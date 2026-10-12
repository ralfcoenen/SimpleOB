"""Tests für die administrative PostgreSQL-Schemaprüfung."""

from __future__ import annotations

import os
from unittest.mock import Mock

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from openbilanz.database.migration_service import (
    PostgreSQLSchemaStatus,
)
from openbilanz.database.postgresql_administration_service import (
    PostgreSQLAdministrationService,
)
from openbilanz.database.postgresql_migration_lock import (
    MIGRATION_LOCK_KEY,
)
from pathlib import Path

from openbilanz.database.postgresql_migration_safety import (
    PostgreSQLMigrationAction,
    PostgreSQLMigrationApproval,
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


def _assert_migration_lock_available(database_url: str) -> None:
    """Prüft die Freigabe der exklusiven administrativen Sperre."""
    engine = create_engine(database_url)

    try:
        with engine.connect() as connection:
            acquired = connection.execute(
                text("SELECT pg_try_advisory_lock(:key)"),
                {"key": MIGRATION_LOCK_KEY},
            ).scalar_one()

            try:
                assert acquired is True
            finally:
                if acquired:
                    connection.execute(
                        text("SELECT pg_advisory_unlock(:key)"),
                        {"key": MIGRATION_LOCK_KEY},
                    )
                    connection.rollback()
    finally:
        engine.dispose()

def _service(database_url: str) -> PostgreSQLAdministrationService:
    config = Mock()
    config.database_url = database_url

    return PostgreSQLAdministrationService(
        application_config=config
    )


def test_administrative_inspection_returns_current_schema(
    database_url: str,
) -> None:
    """Die bestehende Testdatenbank wird korrekt erkannt."""
    result = _service(database_url).inspect_schema()

    assert result.status == PostgreSQLSchemaStatus.CURRENT


def test_administrative_inspection_rejects_existing_lock(
    database_url: str,
) -> None:
    """Eine bereits aktive administrative Sperre verhindert die Prüfung."""
    engine = create_engine(
        make_url(database_url).set(database="postgres")
    )
    try:
        with engine.connect() as connection:
            connection.execute(
                text("SELECT pg_advisory_lock(:key)"),
                {"key": MIGRATION_LOCK_KEY},
            )
            connection.commit()

            try:
                with pytest.raises(
                    RuntimeError,
                    match="bereits aktiv",
                ):
                    _service(database_url).inspect_schema()
            finally:
                connection.execute(
                    text("SELECT pg_advisory_unlock(:key)"),
                    {"key": MIGRATION_LOCK_KEY},
                )
                connection.rollback()
    finally:
        engine.dispose()


def test_administrative_inspection_releases_lock(
    database_url: str,
) -> None:
    """Nach der Prüfung kann eine andere Verbindung die Sperre erwerben."""
    _service(database_url).inspect_schema()

    engine = create_engine(database_url)

    try:
        with engine.connect() as connection:
            acquired = connection.execute(
                text("SELECT pg_try_advisory_lock(:key)"),
                {"key": MIGRATION_LOCK_KEY},
            ).scalar_one()

            assert acquired is True

            connection.execute(
                text("SELECT pg_advisory_unlock(:key)"),
                {"key": MIGRATION_LOCK_KEY},
            )
            connection.rollback()
    finally:
        engine.dispose()


def test_administrative_inspection_rejects_sqlite() -> None:
    """SQLite darf nicht an den PostgreSQL-Administrationsdienst gelangen."""
    service = _service("sqlite:///:memory:")

    with pytest.raises(
        ValueError,
        match="nur für PostgreSQL",
    ):
        service.inspect_schema()


def test_administrative_inspection_rejects_other_sessions(
    database_url: str,
) -> None:
    """Andere Datenbanksitzungen verhindern die administrative Prüfung."""
    engine = create_engine(database_url)

    try:
        with engine.connect() as other_connection:
            other_connection.execute(text("SELECT 1"))

            with pytest.raises(
                RuntimeError,
                match="anderen Sitzungen",
            ):
                _service(database_url).inspect_schema()
    finally:
        engine.dispose()


def test_prepare_migration_current_schema(
    database_url: str,
) -> None:
    """Ein aktuelles Schema benötigt keine Migration."""
    result = _service(database_url).prepare_migration(
        approval=PostgreSQLMigrationApproval()
    )

    assert result == PostgreSQLMigrationAction.NONE


def test_prepare_migration_rejects_other_sessions(
    database_url: str,
) -> None:
    """Andere Sitzungen verhindern die Migrationsvorbereitung."""
    engine = create_engine(database_url)

    try:
        with engine.connect() as other_connection:
            other_connection.execute(text("SELECT 1"))

            with pytest.raises(
                RuntimeError,
                match="anderen Sitzungen",
            ):
                _service(database_url).prepare_migration(
                    approval=PostgreSQLMigrationApproval()
                )
    finally:
        engine.dispose()


def test_prepare_migration_rejects_sqlite() -> None:
    """Der administrative Ablauf ist ausschließlich für PostgreSQL."""
    service = _service("sqlite:///:memory:")

    with pytest.raises(
        ValueError,
        match="nur für PostgreSQL",
    ):
        service.prepare_migration(
            approval=PostgreSQLMigrationApproval()
        )


def test_migration_dry_run_current_schema(
    database_url: str,
    tmp_path: Path,
) -> None:
    """Der Probelauf erstellt und prüft ein Backup ohne Migration."""
    backup_path = tmp_path / "administrative_dry_run.dump"

    result = _service(database_url).run_migration_dry_run(
        approval=PostgreSQLMigrationApproval(),
        backup_path=backup_path,
    )

    assert result.action == PostgreSQLMigrationAction.NONE
    assert result.backup_path == backup_path.resolve()
    assert result.backup_size > 0
    assert result.restored_table_count > 0
    assert backup_path.is_file()


def test_migration_dry_run_rejects_other_sessions(
    database_url: str,
    tmp_path: Path,
) -> None:
    """Bei weiteren Sitzungen wird kein Backup erstellt."""
    backup_path = tmp_path / "blocked_dry_run.dump"
    engine = create_engine(database_url)

    try:
        with engine.connect() as other_connection:
            other_connection.execute(text("SELECT 1"))

            with pytest.raises(
                RuntimeError,
                match="Weitere PostgreSQL-Sitzungen",
            ):
                _service(database_url).run_migration_dry_run(
                    approval=PostgreSQLMigrationApproval(),
                    backup_path=backup_path,
                )
    finally:
        engine.dispose()

    assert not backup_path.exists()


def test_migration_dry_run_releases_lock_after_backup_failure(
    database_url: str,
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Ein Backupfehler beendet den Probelauf und gibt die Sperre frei."""
    from openbilanz.database import postgresql_administration_service as module

    def failing_backup(self, *, backup_path):
        raise RuntimeError("Simulierter Backupfehler")

    monkeypatch.setattr(
        module.PostgreSQLBackupService,
        "create_backup",
        failing_backup,
    )

    with pytest.raises(
        RuntimeError,
        match="Simulierter Backupfehler",
    ):
        _service(database_url).run_migration_dry_run(
            approval=PostgreSQLMigrationApproval(),
            backup_path=tmp_path / "failed_backup.dump",
        )

    _assert_migration_lock_available(database_url)


def test_migration_dry_run_releases_lock_after_restore_failure(
    database_url: str,
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Ein Restorefehler beendet den Probelauf und gibt die Sperre frei."""
    from openbilanz.database import postgresql_administration_service as module

    def failing_restore(self, *, backup_path):
        raise RuntimeError("Simulierter Restorefehler")

    monkeypatch.setattr(
        module.PostgreSQLRestoreVerificationService,
        "verify_backup",
        failing_restore,
    )

    backup_path = tmp_path / "failed_restore.dump"

    with pytest.raises(
        RuntimeError,
        match="Simulierter Restorefehler",
    ):
        _service(database_url).run_migration_dry_run(
            approval=PostgreSQLMigrationApproval(),
            backup_path=backup_path,
        )

    assert backup_path.is_file()
    _assert_migration_lock_available(database_url)



def test_inspect_schema_rejects_administrative_lock_on_postgres(
    database_url: str,
) -> None:
    """Eine Sperre auf 'postgres' verhindert die Schemaprüfung."""
    url = make_url(database_url)

    admin_engine = create_engine(
        url.set(database="postgres")
    )

    try:
        with admin_engine.connect() as connection:
            acquired = connection.execute(
                text("SELECT pg_try_advisory_lock(:key)"),
                {"key": MIGRATION_LOCK_KEY},
            ).scalar_one()

            connection.commit()

            assert acquired is True

            try:
                with pytest.raises(
                    RuntimeError,
                    match="andere administrative PostgreSQL-Migration",
                ):
                    _service(database_url).inspect_schema()
            finally:
                connection.execute(
                    text("SELECT pg_advisory_unlock(:key)"),
                    {"key": MIGRATION_LOCK_KEY},
                )
                connection.rollback()
    finally:
        admin_engine.dispose()


def test_migration_dry_run_rejects_administrative_lock_on_postgres(
    database_url: str,
    tmp_path: Path,
) -> None:
    """Eine administrative Sperre verhindert den Probelauf."""
    admin_engine = create_engine(
        make_url(database_url).set(database="postgres")
    )

    backup_path = tmp_path / "blocked_administrative_dry_run.dump"

    try:
        with admin_engine.connect() as connection:
            acquired = connection.execute(
                text("SELECT pg_try_advisory_lock(:key)"),
                {"key": MIGRATION_LOCK_KEY},
            ).scalar_one()

            connection.commit()
            assert acquired is True

            try:
                with pytest.raises(
                    RuntimeError,
                    match="bereits aktiv",
                ):
                    _service(database_url).run_migration_dry_run(
                        approval=PostgreSQLMigrationApproval(),
                        backup_path=backup_path,
                    )
            finally:
                connection.execute(
                    text("SELECT pg_advisory_unlock(:key)"),
                    {"key": MIGRATION_LOCK_KEY},
                )
                connection.rollback()
    finally:
        admin_engine.dispose()

    assert not backup_path.exists()
