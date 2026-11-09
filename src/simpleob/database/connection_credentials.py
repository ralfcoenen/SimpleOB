"""Laufzeit-Zugangsdaten für PostgreSQL-Verbindungen."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.engine import URL, make_url


def _escape_pgpass_field(value: str) -> str:
    if any(character in value for character in ("\x00", "\n", "\r")):
        raise ValueError("Ungültiger Wert für die PostgreSQL-Passwortdatei.")
    return value.replace("\\", "\\\\").replace(":", "\\:")


@contextmanager
def postgresql_tool_environment(
    database_url: str | URL,
    credentials: PostgreSQLCredentials | None,
    *,
    database_pattern: str | None = None,
) -> Iterator[dict[str, str]]:
    """Stellt Zugangsdaten einem libpq-Unterprozess kurzzeitig bereit.

    Ohne ausdrücklich übergebene Zugangsdaten bleibt das bisherige
    libpq-Verhalten erhalten. Mit Zugangsdaten wird eine private
    Passwortdatei im System-Temporärverzeichnis verwendet; geerbte
    Passwort- und Servicequellen werden dann ausgeschlossen.
    """
    environment = os.environ.copy()
    environment.pop("PGPASSWORD", None)

    if credentials is None:
        yield environment
        return

    url = make_url(database_url)
    username = url.username
    if not username:
        raise ValueError(
            "Für die PostgreSQL-Passwortdatei ist ein Benutzer erforderlich."
        )

    fields = (
        url.host or "*",
        str(url.port) if url.port is not None else "*",
        (database_pattern if database_pattern is not None else (url.database or "*")),
        username,
        credentials.password,
    )
    entry = ":".join(_escape_pgpass_field(field) for field in fields) + "\n"

    temporary_directory = Path(tempfile.gettempdir()).resolve()
    working_directory = Path.cwd().resolve()
    if temporary_directory == working_directory or temporary_directory.is_relative_to(
        working_directory
    ):
        temporary_directory = Path("/tmp").resolve()
    if temporary_directory == working_directory or temporary_directory.is_relative_to(
        working_directory
    ):
        raise RuntimeError(
            "Es steht kein temporärer Speicherort außerhalb des Projekts bereit."
        )

    descriptor, filename = tempfile.mkstemp(
        prefix="simpleob-pgpass-",
        dir=temporary_directory,
        text=True,
    )
    passfile = Path(filename)
    descriptor_open = True
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            descriptor_open = False
            stream.write(entry)

        environment.pop("PGSERVICE", None)
        environment.pop("PGSERVICEFILE", None)
        environment["PGPASSFILE"] = str(passfile)
        yield environment
    finally:
        if descriptor_open:
            os.close(descriptor)
        passfile.unlink(missing_ok=True)


@dataclass(frozen=True, slots=True, repr=False)
class PostgreSQLCredentials:
    """PostgreSQL-Passwort ausschließlich für die laufende Sitzung."""

    password: str

    def __repr__(self) -> str:
        return "PostgreSQLCredentials(password=<geschützt>)"


def database_connect_args(
    database_url: str | URL,
    credentials: PostgreSQLCredentials | None = None,
) -> dict[str, str]:
    """Erzeugt zusätzliche Verbindungsparameter ohne URL-Passwort."""

    url: URL = make_url(database_url)

    if url.get_backend_name() != "postgresql":
        return {}

    if credentials is None:
        return {}

    return {"password": credentials.password}
