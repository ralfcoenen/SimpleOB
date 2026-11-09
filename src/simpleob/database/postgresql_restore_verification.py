"""Wiederherstellungsprobe für PostgreSQL-Backups."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError

from simpleob.core.config import ApplicationConfig
from simpleob.database.connection_credentials import (
    PostgreSQLCredentials,
    database_connect_args,
    postgresql_tool_environment,
)


@dataclass(frozen=True, slots=True)
class PostgreSQLRestoreVerificationResult:
    """Ergebnis einer erfolgreichen Wiederherstellungsprobe."""

    backup_path: Path
    source_database: str
    restored_table_count: int


class PostgreSQLRestoreVerificationService:
    """Prüft ein Backup in einer temporären PostgreSQL-Datenbank."""

    def __init__(
        self,
        *,
        application_config: ApplicationConfig,
        credentials: PostgreSQLCredentials | None = None,
    ) -> None:
        self._application_config = application_config
        self._credentials = credentials

    def verify_backup(
        self,
        *,
        backup_path: Path,
        confirmed_source_database: str,
    ) -> PostgreSQLRestoreVerificationResult:
        """Stellt ein Backup testweise wieder her.

        Die Quelle muss ausdrücklich benannt und mit der konfigurierten
        Datenbank identisch sein. Systemdatenbanken sind ausgeschlossen.

        Die temporäre Datenbank wird nur gelöscht, wenn sie
        von diesem Aufruf erfolgreich angelegt wurde.
        """
        database_url = make_url(
            self._application_config.database_url
        )

        if database_url.get_backend_name() != "postgresql":
            raise ValueError(
                "Die Wiederherstellungsprobe ist nur "
                "für PostgreSQL vorgesehen."
            )

        source_database = database_url.database

        if (
            not confirmed_source_database
            or source_database != confirmed_source_database
            or source_database in {"postgres", "template0", "template1"}
        ):
            raise ValueError(
                "Die Wiederherstellungsprobe benötigt die ausdrücklich "
                "bestätigte Quelldatenbank."
            )

        if database_url.password is not None:
            raise ValueError(
                "Passwörter in der Datenbank-URL "
                "werden nicht unterstützt."
            )

        backup_path = Path(backup_path).expanduser().resolve()

        if not backup_path.is_file():
            raise ValueError(
                "Die Sicherungsdatei existiert nicht."
            )

        if backup_path.stat().st_size == 0:
            raise ValueError(
                "Die Sicherungsdatei ist leer."
            )

        temporary_database = (
            "simpleob_restore_verify_"
            + uuid4().hex
        )

        admin_url = database_url.set(
            database="postgres"
        )

        admin_engine = create_engine(
            admin_url,
            isolation_level="AUTOCOMMIT",
            connect_args=database_connect_args(
                admin_url,
                self._credentials,
            ),
        )

        created = False

        try:
            with admin_engine.connect() as connection:
                connection.execute(
                    text(
                        f'CREATE DATABASE "{temporary_database}"'
                    )
                )
                created = True

            restore_command = [
                "pg_restore",
                "--no-password",
                "--exit-on-error",
                "--no-owner",
                "--no-acl",
                "--dbname",
                temporary_database,
            ]

            if database_url.host:
                restore_command.extend(
                    ["--host", database_url.host]
                )

            if database_url.port:
                restore_command.extend(
                    ["--port", str(database_url.port)]
                )

            if database_url.username:
                restore_command.extend(
                    ["--username", database_url.username]
                )

            restore_command.append(str(backup_path))

            with postgresql_tool_environment(
                database_url,
                self._credentials,
                database_pattern="*",
            ) as environment:
                subprocess.run(
                    restore_command,
                    check=True,
                    capture_output=True,
                    text=True,
                    env=environment,
                )

            restored_url = database_url.set(
                database=temporary_database
            )

            restored_engine = create_engine(
                restored_url,
                connect_args=database_connect_args(
                    restored_url,
                    self._credentials,
                ),
            )

            try:
                with restored_engine.connect() as connection:
                    table_count = connection.execute(
                        text(
                            """
                            SELECT COUNT(*)
                            FROM information_schema.tables
                            WHERE table_schema = 'public'
                              AND table_type = 'BASE TABLE'
                            """
                        )
                    ).scalar_one()
            finally:
                restored_engine.dispose()

            if table_count == 0:
                raise RuntimeError(
                    "Die Wiederherstellung enthält "
                    "keine Datenbanktabellen."
                )

            return PostgreSQLRestoreVerificationResult(
                backup_path=backup_path,
                source_database=source_database,
                restored_table_count=int(table_count),
            )

        except (OSError, subprocess.CalledProcessError, DBAPIError):
            raise RuntimeError(
                "Die PostgreSQL-Wiederherstellungsprobe "
                "ist fehlgeschlagen."
            ) from None

        finally:
            try:
                if created:
                    with admin_engine.connect() as connection:
                        connection.execute(
                            text(
                                f'DROP DATABASE "{temporary_database}" '
                                "WITH (FORCE)"
                            )
                        )
            finally:
                admin_engine.dispose()
