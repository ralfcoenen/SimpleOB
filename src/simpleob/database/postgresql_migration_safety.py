"""Sicherheitsvoraussetzungen für administrative PostgreSQL-Migrationen."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from simpleob.database.migration_service import (
    PostgreSQLSchemaInspection,
    PostgreSQLSchemaStatus,
)


class PostgreSQLMigrationAction(str, Enum):
    INITIALIZE = "initialize"
    UPGRADE = "upgrade"
    NONE = "none"


@dataclass(frozen=True, slots=True)
class PostgreSQLMigrationApproval:
    """Explizite Freigaben für einen administrativen Vorgang."""

    initialize_confirmed: bool = False
    migration_confirmed: bool = False
    maintenance_confirmed: bool = False
    backup_path: Path | None = None


def validate_postgresql_migration(
    *,
    inspection: PostgreSQLSchemaInspection,
    approval: PostgreSQLMigrationApproval,
) -> PostgreSQLMigrationAction:
    """Prüft die Voraussetzungen ohne Datenbankänderungen."""

    status = inspection.status

    if status == PostgreSQLSchemaStatus.UNKNOWN:
        raise RuntimeError(
            "Unbekannter PostgreSQL-Schemazustand. "
            "Eine Migration ist nicht zulässig."
        )

    if status == PostgreSQLSchemaStatus.CURRENT:
        return PostgreSQLMigrationAction.NONE

    if status == PostgreSQLSchemaStatus.EMPTY:
        if not approval.initialize_confirmed:
            raise RuntimeError(
                "Die Initialisierung der PostgreSQL-Datenbank "
                "muss ausdrücklich bestätigt werden."
            )

        return PostgreSQLMigrationAction.INITIALIZE

    if status == PostgreSQLSchemaStatus.OUTDATED:
        if not approval.migration_confirmed:
            raise RuntimeError(
                "Die PostgreSQL-Migration muss "
                "ausdrücklich bestätigt werden."
            )

        if not approval.maintenance_confirmed:
            raise RuntimeError(
                "Der Wartungsbetrieb muss "
                "ausdrücklich bestätigt werden."
            )

        backup_path = approval.backup_path

        if backup_path is None:
            raise RuntimeError(
                "Für die PostgreSQL-Migration "
                "ist eine Datensicherung erforderlich."
            )

        if not backup_path.is_file():
            raise RuntimeError(
                "Die angegebene Datensicherung "
                "ist keine vorhandene Datei."
            )

        if backup_path.stat().st_size == 0:
            raise RuntimeError(
                "Die angegebene Datensicherung ist leer."
            )

        try:
            with backup_path.open("rb") as backup:
                if not backup.read(1):
                    raise RuntimeError(
                        "Die angegebene Datensicherung ist leer."
                    )
        except OSError as exc:
            raise RuntimeError(
                "Die angegebene Datensicherung "
                "kann nicht gelesen werden."
            ) from exc

        return PostgreSQLMigrationAction.UPGRADE

    raise RuntimeError(
        "Nicht unterstützter PostgreSQL-Schemazustand."
    )
