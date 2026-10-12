"""Administrative Prüfungen für PostgreSQL-Datenbanken."""

from __future__ import annotations

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
