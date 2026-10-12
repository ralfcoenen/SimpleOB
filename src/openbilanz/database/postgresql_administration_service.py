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
