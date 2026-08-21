"""Datenbankkonfiguration von OpenBilanz."""

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import (
    Session,
    declarative_base,
    sessionmaker,
)

from openbilanz.core.config import (
    ApplicationConfig,
    load_config,
)

Base = declarative_base()


from openbilanz.database import models  # noqa: E402, F401


class Database:
    """Kapselt Engine und Sitzungen einer OpenBilanz-Datenbank."""

    def __init__(
        self,
        config: ApplicationConfig,
    ) -> None:
        self._config = config

        config.data_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        config.database_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._engine = create_engine(
            config.database_url,
            echo=False,
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

_default_database = Database(
    load_config()
)

engine = _default_database.engine


def create_database() -> None:
    """Erzeugt die Tabellen der Standarddatenbank."""

    _default_database.create_database()


def create_session() -> Session:
    """Erzeugt eine Sitzung der Standarddatenbank."""

    return _default_database.create_session()
