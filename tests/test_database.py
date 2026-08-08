from sqlalchemy import inspect
from sqlalchemy.orm import Session

from openbilanz.database.database import (
    create_database,
    create_session,
    engine,
)


def test_database():
    create_database()

    assert True


def test_database_creation():
    create_database()

    tables = inspect(engine).get_table_names()

    assert "mandanten" in tables
    assert "wirtschaftsjahre" in tables


def test_create_session() -> None:
    session = create_session()

    try:
        assert isinstance(session, Session)
    finally:
        session.close()
