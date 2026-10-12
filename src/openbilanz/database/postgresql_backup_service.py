"""Erstellung und Prüfung administrativer PostgreSQL-Sicherungen."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.engine import make_url

from openbilanz.core.config import ApplicationConfig


@dataclass(frozen=True, slots=True)
class PostgreSQLBackupResult:
    """Ergebnis einer erfolgreich geprüften Sicherung."""

    backup_path: Path
    database_name: str
    backup_size: int


class PostgreSQLBackupService:
    """Erstellt PostgreSQL-Sicherungen im Custom-Format."""

    def __init__(
        self,
        *,
        application_config: ApplicationConfig,
    ) -> None:
        self._application_config = application_config

    def create_backup(
        self,
        *,
        backup_path: Path,
    ) -> PostgreSQLBackupResult:
        """Erstellt eine neue Sicherung und prüft das Archiv.

        Bestehende Dateien werden nicht überschrieben.
        Die Sicherung wird nicht wiederhergestellt.
        """
        database_url = make_url(
            self._application_config.database_url
        )

        if database_url.get_backend_name() != "postgresql":
            raise ValueError(
                "PostgreSQL-Sicherungen sind nur "
                "für PostgreSQL-Datenbanken vorgesehen."
            )

        database_name = database_url.database

        if not database_name:
            raise ValueError(
                "In der Datenbankverbindung fehlt der Datenbankname."
            )

        if database_url.password is not None:
            raise ValueError(
                "Datenbankpasswörter in der Verbindungs-URL "
                "werden für administrative Sicherungen "
                "nicht unterstützt."
            )

        backup_path = Path(backup_path).expanduser().resolve()

        # Exklusive Erstellung verhindert das Überschreiben
        # einer bereits vorhandenen Sicherungsdatei.
        with backup_path.open("xb"):
            pass

        command = [
            "pg_dump",
            "--format=custom",
            "--no-password",
            "--file",
            str(backup_path),
        ]

        if database_url.host:
            command.extend(
                ["--host", database_url.host]
            )

        if database_url.port:
            command.extend(
                ["--port", str(database_url.port)]
            )

        if database_url.username:
            command.extend(
                ["--username", database_url.username]
            )

        command.append(database_name)

        try:
            environment = os.environ.copy()

            # Eine eventuell vorhandene Passwortvariable
            # wird nicht an den Unterprozess weitergegeben.
            environment.pop("PGPASSWORD", None)

            subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                env=environment,
            )

            subprocess.run(
                [
                    "pg_restore",
                    "--list",
                    str(backup_path),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=environment,
            )

            backup_size = backup_path.stat().st_size

            if backup_size == 0:
                raise RuntimeError(
                    "Die PostgreSQL-Sicherung ist leer."
                )

            return PostgreSQLBackupResult(
                backup_path=backup_path,
                database_name=database_name,
                backup_size=backup_size,
            )

        except (
            OSError,
            subprocess.CalledProcessError,
            RuntimeError,
        ) as exc:
            backup_path.unlink(missing_ok=True)

            raise RuntimeError(
                "Die PostgreSQL-Datensicherung "
                "konnte nicht erfolgreich erstellt "
                "und geprüft werden."
            ) from exc
