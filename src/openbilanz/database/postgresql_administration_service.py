"""Administrative Prüfungen für PostgreSQL-Datenbanken."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url

from openbilanz.core.config import ApplicationConfig
from openbilanz.database.migration_service import (
    DatabaseMigrationService,
    PostgreSQLSchemaInspection,
    PostgreSQLSchemaStatus,
)
from openbilanz.database.postgresql_migration_lock import (
    postgresql_migration_lock,
)
from openbilanz.database.postgresql_session_inspection import (
    inspect_postgresql_sessions,
)
from openbilanz.database.postgresql_migration_safety import (
    PostgreSQLMigrationAction,
    PostgreSQLMigrationApproval,
    validate_postgresql_migration,
)
from openbilanz.database.postgresql_backup_service import (
    PostgreSQLBackupService,
)
from openbilanz.database.postgresql_restore_verification import (
    PostgreSQLRestoreVerificationService,
)


@dataclass(frozen=True, slots=True)
class PostgreSQLMigrationDryRunResult:
    """Ergebnis eines administrativen Probelaufs."""

    action: PostgreSQLMigrationAction
    backup_path: Path | None
    backup_size: int
    restored_table_count: int


class PostgreSQLAdministrationService:
    """Prüft PostgreSQL unter einer exklusiven Migrationssperre."""

    def __init__(
        self,
        *,
        application_config: ApplicationConfig,
    ) -> None:
        self._application_config = application_config
        self._migration_service = DatabaseMigrationService(
            application_config=application_config
        )

    def inspect_schema(
        self,
    ) -> PostgreSQLSchemaInspection:
        """Prüft das Schema unter exklusiver administrativer Sperre.

        Weitere Datenbanksitzungen und unbekannte Schemazustände
        führen zum Abbruch. Es werden keine Migrationen ausgeführt.
        """
        database_url = self._application_config.database_url

        if make_url(database_url).get_backend_name() != "postgresql":
            raise ValueError(
                "Die administrative Schemaprüfung "
                "ist nur für PostgreSQL vorgesehen."
            )

        engine = create_engine(database_url)

        try:
            with engine.connect() as connection:
                with postgresql_migration_lock(connection):
                    sessions = inspect_postgresql_sessions(
                        connection
                    )

                    if sessions.has_other_sessions:
                        raise RuntimeError(
                            "Die PostgreSQL-Datenbank wird noch "
                            "von anderen Sitzungen verwendet "
                            f"({sessions.other_session_count}). "
                            "Bitte alle anderen Datenbankverbindungen "
                            "vor der administrativen Wartung beenden."
                        )

                    inspection = (
                        self._migration_service
                        .inspect_postgresql_schema_on_connection(
                            connection
                        )
                    )

                    if (
                        inspection.status
                        == PostgreSQLSchemaStatus.UNKNOWN
                    ):
                        raise RuntimeError(
                            "Der PostgreSQL-Schemazustand ist unbekannt. "
                            "Eine administrative Migration "
                            "ist nicht zulässig."
                        )

                    return inspection
        finally:
            engine.dispose()

    def prepare_migration(
        self,
        *,
        approval: PostgreSQLMigrationApproval,
    ) -> PostgreSQLMigrationAction:
        """Prüft die Voraussetzungen einer administrativen Migration.

        Die Prüfungen erfolgen unter einer exklusiven
        PostgreSQL-Migrationssperre.

        Es werden keine Migrationen ausgeführt. Die zurückgegebene
        Aktion ist keine dauerhaft gültige Freigabe.
        """
        database_url = self._application_config.database_url

        if make_url(database_url).get_backend_name() != "postgresql":
            raise ValueError(
                "Die administrative Migrationsvorbereitung "
                "ist nur für PostgreSQL vorgesehen."
            )

        engine = create_engine(database_url)

        try:
            with engine.connect() as connection:
                with postgresql_migration_lock(connection):
                    sessions = inspect_postgresql_sessions(
                        connection
                    )

                    if sessions.has_other_sessions:
                        raise RuntimeError(
                            "Die PostgreSQL-Datenbank wird noch "
                            "von anderen Sitzungen verwendet "
                            f"({sessions.other_session_count}). "
                            "Bitte alle anderen Datenbankverbindungen "
                            "vor der administrativen Wartung beenden."
                        )

                    inspection = (
                        self._migration_service
                        .inspect_postgresql_schema_on_connection(
                            connection
                        )
                    )

                    return validate_postgresql_migration(
                        inspection=inspection,
                        approval=approval,
                    )
        finally:
            engine.dispose()

    def run_migration_dry_run(
        self,
        *,
        approval: PostgreSQLMigrationApproval,
        backup_path: Path,
    ) -> PostgreSQLMigrationDryRunResult:
        """Prüft den administrativen Ablauf ohne Migration.

        Ausschließlich simpleob_migration_test ist zugelassen.
        Die exklusive Migrationssperre bleibt während des
        gesamten Probelaufs bestehen.
        """
        database_url = make_url(
            self._application_config.database_url
        )

        if (
            database_url.get_backend_name() != "postgresql"
            or database_url.database != "simpleob_migration_test"
        ):
            raise ValueError(
                "Der administrative Probelauf ist ausschließlich "
                "für die PostgreSQL-Datenbank "
                "'simpleob_migration_test' zugelassen."
            )

        engine = create_engine(
            self._application_config.database_url
        )

        try:
            with engine.connect() as connection:
                with postgresql_migration_lock(connection):
                    sessions = inspect_postgresql_sessions(
                        connection
                    )

                    if sessions.has_other_sessions:
                        raise RuntimeError(
                            "Der Probelauf wurde abgebrochen: "
                            "Weitere PostgreSQL-Sitzungen sind aktiv."
                        )

                    inspection = (
                        self._migration_service
                        .inspect_postgresql_schema_on_connection(
                            connection
                        )
                    )

                    # Für OUTDATED wird die frisch zu erzeugende
                    # Sicherung erst nach erfolgreicher Prüfung
                    # als Backup-Nachweis verwendet.
                    if (
                        inspection.status
                        == PostgreSQLSchemaStatus.OUTDATED
                    ):
                        if not approval.migration_confirmed:
                            raise RuntimeError(
                                "Die Migration muss ausdrücklich "
                                "bestätigt werden."
                            )

                        if not approval.maintenance_confirmed:
                            raise RuntimeError(
                                "Der Wartungsbetrieb muss "
                                "ausdrücklich bestätigt werden."
                            )

                    else:
                        validate_postgresql_migration(
                            inspection=inspection,
                            approval=approval,
                        )

                    backup_result = PostgreSQLBackupService(
                        application_config=self._application_config
                    ).create_backup(
                        backup_path=backup_path
                    )

                    restore_result = (
                        PostgreSQLRestoreVerificationService(
                            application_config=self._application_config
                        ).verify_backup(
                            backup_path=backup_result.backup_path
                        )
                    )

                    effective_approval = (
                        PostgreSQLMigrationApproval(
                            initialize_confirmed=(
                                approval.initialize_confirmed
                            ),
                            migration_confirmed=(
                                approval.migration_confirmed
                            ),
                            maintenance_confirmed=(
                                approval.maintenance_confirmed
                            ),
                            backup_path=backup_result.backup_path,
                        )
                    )

                    action = validate_postgresql_migration(
                        inspection=inspection,
                        approval=effective_approval,
                    )

                    return PostgreSQLMigrationDryRunResult(
                        action=action,
                        backup_path=backup_result.backup_path,
                        backup_size=backup_result.backup_size,
                        restored_table_count=(
                            restore_result.restored_table_count
                        ),
                    )
        finally:
            engine.dispose()
