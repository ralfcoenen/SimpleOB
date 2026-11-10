"""Datenbankkonfiguration von OpenBilanz."""

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import (
    Session,
    declarative_base,
    sessionmaker,
)

from simpleob.core.config import (
    ApplicationConfig,
    load_config,
)
from simpleob.database.connection_credentials import (
    PostgreSQLCredentials,
    database_connect_args,
)
from simpleob.database.postgresql_maintenance_guard import (
    install_postgresql_maintenance_guard,
)

Base = declarative_base()


from simpleob.database import models  # noqa: E402, F401


class Database:
    """Kapselt Engine und Sitzungen einer OpenBilanz-Datenbank."""

    def __init__(
        self,
        config: ApplicationConfig,
        *,
        credentials: PostgreSQLCredentials | None = None,
    ) -> None:
        self._config = config

        self._engine = create_engine(
            config.database_url,
            echo=False,
            connect_args=database_connect_args(
                config.database_url,
                credentials,
            ),
        )

        if self._engine.dialect.name == "sqlite":
            @event.listens_for(self._engine, "connect")
            def _enable_sqlite_foreign_keys(connection, _record) -> None:
                connection.execute("PRAGMA foreign_keys=ON")

        install_postgresql_maintenance_guard(
            self._engine
        )

        self._session_factory = sessionmaker(
            bind=self._engine,
        )

    @property
    def config(self) -> ApplicationConfig:
        """Liefert die verwendete Anwendungskonfiguration."""

        return self._config

    @property
    def engine(self) -> Engine:
        """Liefert die SQLAlchemy-Engine."""

        return self._engine

    def create_database(self) -> None:
        """Erzeugt die Datenbanktabellen."""

        Base.metadata.create_all(
            self._engine
        )

    def create_session(self) -> Session:
        """Erzeugt eine neue Datenbanksitzung."""

        return self._session_factory()

    def dispose(self) -> None:
        """Gibt die Ressourcen der Engine frei."""

        self._engine.dispose()


# ---------------------------------------------------------
# Übergangskompatibilität
# ---------------------------------------------------------

_default_database: Database | None = None


def _get_default_database() -> Database:
    """Erzeugt die Kompatibilitätsdatenbank erst bei tatsächlicher Verwendung."""

    global _default_database
    if _default_database is None:
        _default_database = Database(load_config())
    return _default_database


def __getattr__(name: str) -> Engine:
    """Liefert die bisherige globale Engine erst bei explizitem Zugriff."""

    if name == "engine":
        return _get_default_database().engine
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def create_database() -> None:
    """Erzeugt die Tabellen der Standarddatenbank."""

    _get_default_database().create_database()


def create_session() -> Session:
    """Erzeugt eine Sitzung der Standarddatenbank."""

    return _get_default_database().create_session()
