"""Laufzeit-Zugangsdaten für PostgreSQL-Verbindungen."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.engine import URL, make_url


@dataclass(frozen=True, slots=True, repr=False)
class PostgreSQLCredentials:
    """PostgreSQL-Passwort ausschließlich für die laufende Sitzung."""

    password: str

    def __repr__(self) -> str:
        return "PostgreSQLCredentials(password=<geschützt>)"


def database_connect_args(
    database_url: str,
    credentials: PostgreSQLCredentials | None = None,
) -> dict[str, str]:
    """Erzeugt zusätzliche Verbindungsparameter ohne URL-Passwort."""

    url: URL = make_url(database_url)

    if url.get_backend_name() != "postgresql":
        return {}

    if credentials is None:
        return {}

    return {"password": credentials.password}
