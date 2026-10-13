"""Tests für die grundlegenden Datenbankfunktionen."""

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session, sessionmaker

from openbilanz.database.models import Base


def test_database(tmp_path):
    """Eine neue SQLite-Datenbank kann angelegt werden."""

    database_file = tmp_path / "test_database.db"

    engine = create_engine(
        f"sqlite:///{database_file}"
    )

    try:
        Base.metadata.create_all(engine)

        assert database_file.exists()
    finally:
        engine.dispose()


def test_database_creation(tmp_path):
    """Die erwarteten Tabellen werden angelegt."""

    database_file = tmp_path / "test_database.db"

    engine = create_engine(
        f"sqlite:///{database_file}"
    )

    try:
        Base.metadata.create_all(engine)

        tables = inspect(engine).get_table_names()

        assert "mandanten" in tables
        assert "wirtschaftsjahre" in tables
    finally:
        engine.dispose()


def test_create_session(tmp_path) -> None:
    """Eine SQLAlchemy-Session kann erstellt werden."""

    database_file = tmp_path / "test_database.db"

    engine = create_engine(
        f"sqlite:///{database_file}"
    )

    try:
        session_factory = sessionmaker(bind=engine)
        session = session_factory()

        try:
            assert isinstance(session, Session)
        finally:
            session.close()
    finally:
        engine.dispose()
