from openbilanz.database.connection_credentials import (
    PostgreSQLCredentials,
    database_connect_args,
)


def test_postgresql_credentials_are_passed_separately():
    credentials = PostgreSQLCredentials(
        password="test-secret"
    )

    result = database_connect_args(
        "postgresql+psycopg://testuser@localhost:5432/testdb",
        credentials,
    )

    assert result == {"password": "test-secret"}
    assert "test-secret" not in repr(credentials)


def test_postgresql_without_credentials_remains_unchanged():
    result = database_connect_args(
        "postgresql+psycopg://testuser@localhost:5432/testdb"
    )

    assert result == {}


def test_sqlite_does_not_receive_postgresql_credentials():
    result = database_connect_args(
        "sqlite:///test.db",
        PostgreSQLCredentials(password="test-secret"),
    )

    assert result == {}
