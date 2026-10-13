"""Einmalige Einrichtung einer neu angelegten SimpleOB-PostgreSQL-Datenbank.

Keine Migration vorhandener Datenbanken; keine automatische Bereinigung.
"""

from __future__ import annotations

from dataclasses import dataclass

from alembic import command
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from openbilanz.core.config import ApplicationConfig
from openbilanz.database.connection_credentials import (
    PostgreSQLCredentials,
    database_connect_args,
)
from openbilanz.database.migration_service import (
    DatabaseMigrationService,
    PostgreSQLSchemaStatus,
)
from openbilanz.database.postgresql_migration_lock import (
    postgresql_migration_lock,
)


@dataclass(frozen=True, slots=True)
class PostgreSQLInitializationResult:
    database_name: str
    owner_role: str
    initialized: bool


class PostgreSQLInitializationService:
    """Erstellt und initialisiert nur eine während des Aufrufs neu angelegte DB."""

    def initialize_database(
        self,
        *,
        application_config: ApplicationConfig,
        admin_username: str,
        admin_credentials: PostgreSQLCredentials,
        application_credentials: PostgreSQLCredentials,
        confirmed: bool,
    ) -> PostgreSQLInitializationResult:
        if not confirmed:
            raise ValueError(
                "Die Datenbankneuanlage muss ausdrücklich bestätigt werden."
            )
        if not isinstance(admin_credentials, PostgreSQLCredentials):
            raise TypeError("Administrative Zugangsdaten fehlen.")
        if not isinstance(application_credentials, PostgreSQLCredentials):
            raise TypeError("Zugangsdaten der Anwendungsrolle fehlen.")
        if not isinstance(admin_username, str) or not admin_username.strip():
            raise ValueError("Eine Administrationsrolle muss angegeben werden.")

        database_url = application_config.database_url
        target_url = make_url(database_url)
        if target_url.drivername != "postgresql+psycopg":
            raise ValueError("PostgreSQL mit psycopg ist erforderlich.")
        database_name = target_url.database
        owner_role = target_url.username
        if not database_name or not owner_role:
            raise ValueError("Datenbankname und Anwendungsrolle fehlen.")
        if not target_url.host or target_url.port is None:
            raise ValueError("Server und Port müssen angegeben werden.")
        if target_url.password is not None:
            raise ValueError("Die Anwendungs-URL darf kein Passwort enthalten.")
        if database_name in {"postgres", "template0", "template1"}:
            raise ValueError("Eine PostgreSQL-Systemdatenbank ist unzulässig.")

        admin_url = target_url.set(
            database="postgres",
            username=admin_username.strip(),
            password=None,
        )
        admin_url_string = admin_url.render_as_string(hide_password=False)
        admin_engine = create_engine(
            admin_url,
            connect_args=database_connect_args(
                admin_url_string, admin_credentials
            ),
            isolation_level="AUTOCOMMIT",
        )

        created = False
        try:
            with admin_engine.connect() as admin_connection:
                with postgresql_migration_lock(admin_connection):
                    exists = admin_connection.execute(
                        text("SELECT 1 FROM pg_database WHERE datname = :name"),
                        {"name": database_name},
                    ).scalar_one_or_none()
                    if exists is not None:
                        raise RuntimeError(
                            "Die gewünschte PostgreSQL-Datenbank existiert bereits."
                        )

                    preparer = admin_connection.dialect.identifier_preparer
                    db_identifier = preparer.quote_identifier(database_name)
                    owner_identifier = preparer.quote_identifier(owner_role)
                    admin_connection.exec_driver_sql(
                        f"CREATE DATABASE {db_identifier} OWNER {owner_identifier}"
                    )
                    created = True

                    # Die Anwendungsrolle führt die Erstinitialisierung selbst aus.
                    app_engine = create_engine(
                        target_url,
                        connect_args=database_connect_args(
                            database_url, application_credentials
                        ),
                    )
                    try:
                        with app_engine.connect() as app_connection:
                            actual_db, actual_user = app_connection.exec_driver_sql(
                                "SELECT current_database(), current_user"
                            ).one()
                            if actual_db != database_name or actual_user != owner_role:
                                raise RuntimeError(
                                    "Anwendungsverbindung verwendet eine unerwartete "
                                    "Datenbank oder Rolle."
                                )

                            migration_service = DatabaseMigrationService(
                                application_config=application_config,
                                credentials=application_credentials,
                            )
                            inspection = (
                                migration_service.inspect_postgresql_schema_on_connection(
                                    app_connection
                                )
                            )
                            if inspection.status != PostgreSQLSchemaStatus.EMPTY:
                                raise RuntimeError(
                                    "Die neu angelegte Datenbank ist nicht leer; "
                                    "Initialisierung abgebrochen."
                                )
                            app_connection.rollback()

                            # Ausschließlich Erstinitialisierung der gerade
                            # angelegten Datenbank; kein Aufruf der auf
                            # simpleob_migration_test begrenzten Migration.
                            alembic_config = migration_service._create_alembic_config()
                            alembic_config.attributes["connection"] = app_connection
                            with app_connection.begin():
                                command.upgrade(alembic_config, "head")

                            final_status = (
                                migration_service.inspect_postgresql_schema_on_connection(
                                    app_connection
                                )
                            )
                            if final_status.status != PostgreSQLSchemaStatus.CURRENT:
                                raise RuntimeError(
                                    "Die Datenbank wurde nicht bis zur aktuellen "
                                    "Alembic-Revision initialisiert."
                                )
                            app_connection.rollback()
                    finally:
                        app_engine.dispose()

                    # Die Abschlussprüfung bleibt unter derselben
                    # administrativen Advisory-Sperre.
                    DatabaseMigrationService(
                        application_config=application_config,
                        credentials=application_credentials,
                    ).check_ready_for_start()
        except Exception as exc:
            if created:
                raise RuntimeError(
                    "Die neue PostgreSQL-Datenbank wurde angelegt, aber die "
                    "Einrichtung oder Abschlussprüfung ist fehlgeschlagen. "
                    "Sie wird nicht automatisch gelöscht. Bitte den Fehler "
                    "administrativ prüfen; nicht unter demselben Namen "
                    "erneut anlegen."
                ) from exc
            raise
        finally:
            admin_engine.dispose()

        return PostgreSQLInitializationResult(
            database_name=database_name,
            owner_role=owner_role,
            initialized=True,
        )
