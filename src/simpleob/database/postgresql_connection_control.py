"""Administrative Kontrolle von PostgreSQL-Datenbankverbindungen."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from simpleob.core.config import ApplicationConfig


TEST_DATABASE = "simpleob_migration_test"


@dataclass(frozen=True, slots=True)
class PostgreSQLConnectionStatus:
    database_name: str
    allows_connections: bool


class PostgreSQLConnectionControl:
    """Kontrolliert den Verbindungsstatus einer PostgreSQL-Testdatenbank."""

    def __init__(
        self,
        *,
        application_config: ApplicationConfig,
    ) -> None:
        self._application_config = application_config

    def _database_url(self):
        url = make_url(self._application_config.database_url)

        if (
            url.get_backend_name() != "postgresql"
            or url.database != TEST_DATABASE
        ):
            raise ValueError(
                "Die Verbindungskontrolle ist ausschließlich "
                "für 'simpleob_migration_test' zugelassen."
            )

        if url.password is not None:
            raise ValueError(
                "Passwörter in der Datenbank-URL "
                "werden nicht unterstützt."
            )

        return url

    def inspect(self) -> PostgreSQLConnectionStatus:
        """Liest den Verbindungsstatus ohne Änderung."""
        url = self._database_url()
        engine = create_engine(url.set(database="postgres"))

        try:
            with engine.connect() as connection:
                result = connection.execute(
                    text(
                        "SELECT datallowconn "
                        "FROM pg_database "
                        "WHERE datname = :database_name"
                    ),
                    {"database_name": TEST_DATABASE},
                ).scalar_one_or_none()

                if result is None:
                    raise RuntimeError(
                        "Die PostgreSQL-Testdatenbank existiert nicht."
                    )

                return PostgreSQLConnectionStatus(
                    database_name=TEST_DATABASE,
                    allows_connections=bool(result),
                )
        finally:
            engine.dispose()

    def set_connections_allowed(
        self,
        *,
        allowed: bool,
        confirmed: bool,
    ) -> PostgreSQLConnectionStatus:
        """Ändert den Verbindungsstatus nach ausdrücklicher Freigabe."""
        if not confirmed:
            raise ValueError(
                "Die administrative Änderung muss "
                "ausdrücklich bestätigt werden."
            )

        url = self._database_url()

        engine = create_engine(
            url.set(database="postgres"),
            isolation_level="AUTOCOMMIT",
        )

        try:
            with engine.connect() as connection:
                connection.execute(
                    text(
                        f'ALTER DATABASE "{TEST_DATABASE}" '
                        f'WITH ALLOW_CONNECTIONS '
                        f'{"true" if allowed else "false"}'
                    )
                )
        finally:
            engine.dispose()

        return self.inspect()
