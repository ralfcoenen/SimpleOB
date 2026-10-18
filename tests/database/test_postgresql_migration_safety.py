"""Tests der administrativen PostgreSQL-Migrationsfreigabe."""

from pathlib import Path

import pytest

from simpleob.database.migration_service import (
    PostgreSQLSchemaInspection,
    PostgreSQLSchemaStatus,
)
from simpleob.database.postgresql_migration_safety import (
    PostgreSQLMigrationAction,
    PostgreSQLMigrationApproval,
    validate_postgresql_migration,
)


def _inspection(
    status: PostgreSQLSchemaStatus,
) -> PostgreSQLSchemaInspection:
    return PostgreSQLSchemaInspection(
        status=status,
        current_revision=(
            "alte_revision"
            if status == PostgreSQLSchemaStatus.OUTDATED
            else None
        ),
        head_revision="aktuelle_revision",
    )


def test_current_schema_requires_no_action() -> None:
    result = validate_postgresql_migration(
        inspection=_inspection(PostgreSQLSchemaStatus.CURRENT),
        approval=PostgreSQLMigrationApproval(),
    )

    assert result == PostgreSQLMigrationAction.NONE


def test_unknown_schema_is_rejected() -> None:
    with pytest.raises(RuntimeError, match="Unbekannter"):
        validate_postgresql_migration(
            inspection=_inspection(PostgreSQLSchemaStatus.UNKNOWN),
            approval=PostgreSQLMigrationApproval(
                initialize_confirmed=True,
                migration_confirmed=True,
                maintenance_confirmed=True,
            ),
        )


def test_empty_schema_requires_confirmation() -> None:
    with pytest.raises(RuntimeError, match="ausdrücklich bestätigt"):
        validate_postgresql_migration(
            inspection=_inspection(PostgreSQLSchemaStatus.EMPTY),
            approval=PostgreSQLMigrationApproval(),
        )

    result = validate_postgresql_migration(
        inspection=_inspection(PostgreSQLSchemaStatus.EMPTY),
        approval=PostgreSQLMigrationApproval(
            initialize_confirmed=True
        ),
    )

    assert result == PostgreSQLMigrationAction.INITIALIZE


@pytest.mark.parametrize(
    ("approval", "expected_message"),
    [
        (
            PostgreSQLMigrationApproval(),
            "ausdrücklich bestätigt",
        ),
        (
            PostgreSQLMigrationApproval(
                migration_confirmed=True
            ),
            "Wartungsbetrieb",
        ),
        (
            PostgreSQLMigrationApproval(
                migration_confirmed=True,
                maintenance_confirmed=True,
            ),
            "Datensicherung",
        ),
    ],
)
def test_upgrade_requires_all_approvals(
    approval: PostgreSQLMigrationApproval,
    expected_message: str,
) -> None:
    with pytest.raises(RuntimeError, match=expected_message):
        validate_postgresql_migration(
            inspection=_inspection(PostgreSQLSchemaStatus.OUTDATED),
            approval=approval,
        )


def test_upgrade_rejects_missing_backup(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="keine vorhandene Datei"):
        validate_postgresql_migration(
            inspection=_inspection(PostgreSQLSchemaStatus.OUTDATED),
            approval=PostgreSQLMigrationApproval(
                migration_confirmed=True,
                maintenance_confirmed=True,
                backup_path=tmp_path / "missing.dump",
            ),
        )


def test_upgrade_rejects_empty_backup(tmp_path: Path) -> None:
    backup = tmp_path / "empty.dump"
    backup.touch()

    with pytest.raises(RuntimeError, match="leer"):
        validate_postgresql_migration(
            inspection=_inspection(PostgreSQLSchemaStatus.OUTDATED),
            approval=PostgreSQLMigrationApproval(
                migration_confirmed=True,
                maintenance_confirmed=True,
                backup_path=backup,
            ),
        )


def test_upgrade_accepts_existing_backup(tmp_path: Path) -> None:
    backup = tmp_path / "backup.dump"
    backup.write_bytes(b"test-backup")

    result = validate_postgresql_migration(
        inspection=_inspection(PostgreSQLSchemaStatus.OUTDATED),
        approval=PostgreSQLMigrationApproval(
            migration_confirmed=True,
            maintenance_confirmed=True,
            backup_path=backup,
        ),
    )

    assert result == PostgreSQLMigrationAction.UPGRADE
