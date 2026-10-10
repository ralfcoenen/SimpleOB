"""Tests für die konfigurierbare Datenbank."""

from pathlib import Path

from sqlalchemy import inspect

from openbilanz.core.config import ApplicationConfig
from openbilanz.database.database import Database


def create_config(
    tmp_path: Path,
) -> ApplicationConfig:
    """Erzeugt eine isolierte Testkonfiguration."""

    return ApplicationConfig(
        data_dir=tmp_path,
        database_file=(
            tmp_path
            / "openbilanz.db"
        ),
        taxonomy_dir=(
            tmp_path
            / "taxonomy"
        ),
        config_file=(
            tmp_path
            / "config.toml"
        ),
    )


def test_database_uses_configured_database_file(
    tmp_path: Path,
) -> None:
    config = create_config(
        tmp_path
    )

    database = Database(
        config
    )

    try:
        assert str(
            database.engine.url
        ) == config.database_url
    finally:
        database.dispose()


def test_database_creates_schema(
    tmp_path: Path,
) -> None:
    config = create_config(
        tmp_path
    )

    database = Database(
        config
    )

    try:
        database.create_database()

        tables = inspect(
            database.engine
        ).get_table_names()

        assert "mandanten" in tables
        assert "wirtschaftsjahre" in tables
        assert "buchungen" in tables
        assert "buchungszeilen" in tables
    finally:
        database.dispose()


def test_database_creates_session(
    tmp_path: Path,
) -> None:
    config = create_config(
        tmp_path
    )

    database = Database(
        config
    )

    try:
        database.create_database()

        session = database.create_session()

        try:
            assert session.bind is database.engine
        finally:
            session.close()
    finally:
        database.dispose()


def test_database_uses_postgresql_configuration(
    tmp_path: Path,
) -> None:
    config = ApplicationConfig(
        data_dir=tmp_path,
        database_file=tmp_path / "openbilanz.db",
        taxonomy_dir=tmp_path / "taxonomy",
        config_file=tmp_path / "config.toml",
        database_url_override=(
            "postgresql+psycopg://"
            "simpleob@localhost:5432/simpleob"
        ),
    )

    database = Database(config)

    try:
        assert database.engine.dialect.name == "postgresql"
        assert database.engine.url.drivername == (
            "postgresql+psycopg"
        )
    finally:
        database.dispose()
