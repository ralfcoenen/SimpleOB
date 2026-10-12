"""Administrative Prüfungen für PostgreSQL-Datenbanken."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import create_engine, text
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
from openbilanz.database.postgresql_maintenance_isolation import (
    postgresql_maintenance_isolation,
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
        """Prüft das Schema unter einer administrativen PostgreSQL-Sperre.

        Die exklusive Sperre wird über die Datenbank 'postgres'
        gehalten. Die Schemaprüfung erfolgt über die eigentliche
        Anwendungsdatenbank.

        Andere Sitzungen und unbekannte Schemazustände
        führen zum Abbruch. Es erfolgt keine Migration.
        """
        database_url = self._application_config.database_url
        url = make_url(database_url)

        if url.get_backend_name() != "postgresql":
            raise ValueError(
                "Die administrative Schemaprüfung "
                "ist nur für PostgreSQL vorgesehen."
            )

        admin_engine = create_engine(
            url.set(database="postgres")
        )
        database_engine = create_engine(database_url)

        try:
            with admin_engine.connect() as admin_connection:
                with postgresql_migration_lock(admin_connection):
                    with database_engine.connect() as connection:
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
            database_engine.dispose()
            admin_engine.dispose()

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

        admin_engine = create_engine(
            make_url(database_url).set(database="postgres")
        )
        database_engine = create_engine(database_url)

        try:
            with admin_engine.connect() as admin_connection:
                with postgresql_migration_lock(admin_connection):
                    with database_engine.connect() as connection:
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
            database_engine.dispose()
            admin_engine.dispose()

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

        admin_engine = create_engine(
            database_url.set(database="postgres")
        )
        database_engine = create_engine(
            self._application_config.database_url
        )

        try:
            with admin_engine.connect() as admin_connection:
                with postgresql_migration_lock(admin_connection):
                    with database_engine.connect() as connection:
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
            database_engine.dispose()
            admin_engine.dispose()


    def verify_maintenance_isolation(self) -> None:
        """Prüft die Wartungsisolierung ohne Schemaänderungen.

        Ausschließlich simpleob_migration_test.
        Die administrative Sperre wird während der gesamten
        Prüfung auf der Datenbank 'postgres' gehalten.
        """
        database_url = self._application_config.database_url
        url = make_url(database_url)

        if (
            url.get_backend_name() != "postgresql"
            or url.database != "simpleob_migration_test"
        ):
            raise ValueError(
                "Die Prüfung der Wartungsisolierung ist "
                "ausschließlich für die PostgreSQL-Testdatenbank "
                "'simpleob_migration_test' zugelassen."
            )

        if url.password is not None:
            raise ValueError(
                "Passwörter in der Datenbank-URL "
                "werden nicht unterstützt."
            )

        admin_engine = create_engine(
            url.set(database="postgres"),
            isolation_level="AUTOCOMMIT",
        )
        database_engine = create_engine(database_url)

        try:
            with admin_engine.connect() as admin_connection:
                with postgresql_migration_lock(admin_connection):
                    with database_engine.connect() as migration_connection:
                        with postgresql_maintenance_isolation(
                            application_config=self._application_config,
                            admin_connection=admin_connection,
                            migration_connection=migration_connection,
                        ):
                            database_name = migration_connection.execute(
                                text("SELECT current_database()")
                            ).scalar_one()

                            if database_name != "simpleob_migration_test":
                                raise RuntimeError(
                                    "Die bestehende Migrationsverbindung "
                                    "verweist auf eine unerwartete Datenbank."
                                )

            # Erst nach Aufhebung der Verbindungssperre wird
            # eine neue Verbindung zur Testdatenbank geöffnet.
            with database_engine.connect() as connection:
                connection.execute(text("SELECT 1")).scalar_one()

        finally:
            database_engine.dispose()
            admin_engine.dispose()

    def run_maintenance_dry_run(
        self,
        *,
        approval: PostgreSQLMigrationApproval,
        backup_path: Path,
    ) -> PostgreSQLMigrationDryRunResult:
        """Prüft Backup und Wartungsisolierung ohne Alembic-Migration.

        Ausschließlich für simpleob_migration_test.
        """
        database_url = self._application_config.database_url
        url = make_url(database_url)

        if (
            url.get_backend_name() != "postgresql"
            or url.database != "simpleob_migration_test"
        ):
            raise ValueError(
                "Der Wartungsprobelauf ist ausschließlich für "
                "'simpleob_migration_test' zugelassen."
            )

        if url.password is not None:
            raise ValueError(
                "Passwörter in der Datenbank-URL "
                "werden nicht unterstützt."
            )

        admin_engine = create_engine(
            url.set(database="postgres"),
            isolation_level="AUTOCOMMIT",
        )
        database_engine = create_engine(database_url)

        try:
            with admin_engine.connect() as admin_connection:
                with postgresql_migration_lock(admin_connection):
                    with database_engine.connect() as migration_connection:
                        sessions = inspect_postgresql_sessions(
                            migration_connection
                        )

                        if sessions.has_other_sessions:
                            raise RuntimeError(
                                "Der Wartungsprobelauf wurde abgebrochen: "
                                "Weitere PostgreSQL-Sitzungen sind aktiv."
                            )

                        inspection = (
                            self._migration_service
                            .inspect_postgresql_schema_on_connection(
                                migration_connection
                            )
                        )

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

                        effective_approval = PostgreSQLMigrationApproval(
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

                        action = validate_postgresql_migration(
                            inspection=inspection,
                            approval=effective_approval,
                        )

                        # Die Schemaprüfung hat eine Lesetransaktion
                        # eröffnet. Diese wird vor der späteren
                        # Wartungsphase ausdrücklich beendet.
                        migration_connection.rollback()

                        with postgresql_maintenance_isolation(
                            application_config=self._application_config,
                            admin_connection=admin_connection,
                            migration_connection=migration_connection,
                        ):
                            actual_database = (
                                migration_connection.exec_driver_sql(
                                    "SELECT current_database()"
                                ).scalar_one()
                            )

                            if actual_database != "simpleob_migration_test":
                                raise RuntimeError(
                                    "Die Migrationsverbindung verweist "
                                    "auf eine unerwartete Datenbank."
                                )

                            # Noch keine Alembic-Migration.
                            migration_connection.rollback()

                        return PostgreSQLMigrationDryRunResult(
                            action=action,
                            backup_path=backup_result.backup_path,
                            backup_size=backup_result.backup_size,
                            restored_table_count=(
                                restore_result.restored_table_count
                            ),
                        )
        finally:
            database_engine.dispose()
            admin_engine.dispose()
