from openbilanz.database.database import (
    engine,
    create_database
)
from sqlalchemy import inspect


from openbilanz.database.models import (
    Mandant
)


def test_database():

    create_database()

    assert True


def test_database_creation():

    create_database()

    tables = inspect(engine).get_table_names()
    assert "mandanten" in tables

    assert "wirtschaftsjahre" in tables
    
    