"""Tests für die administrative PostgreSQL-Verbindungskontrolle."""

from __future__ import annotations

import os
from unittest.mock import Mock

import pytest

from openbilanz.database.postgresql_connection_control import (
    PostgreSQLConnectionControl,
    TEST_DATABASE,
)


@pytest.fixture
def database_url() -> str:
    url = os.environ.get("SIMPLEOB_POSTGRES_TEST_URL")

    if not url:
        pytest.skip("PostgreSQL-Testdatenbank nicht konfiguriert.")

    from sqlalchemy.engine import make_url

    if make_url(url).database != TEST_DATABASE:
        pytest.fail(
            "Die Tests dürfen ausschließlich "
            "simpleob_migration_test verwenden."
        )

    return url


def _control(database_url: str) -> PostgreSQLConnectionControl:
    config = Mock()
    config.database_url = database_url

    return PostgreSQLConnectionControl(
        application_config=config
    )


def test_inspect_connections_allowed(
    database_url: str,
) -> None:
    """Liest den aktuellen Verbindungsstatus."""
    result = _control(database_url).inspect()

    assert result.database_name == TEST_DATABASE
    assert isinstance(result.allows_connections, bool)
    assert result.allows_connections is True


def test_rejects_unconfirmed_change(
    database_url: str,
) -> None:
    """Ohne Bestätigung darf keine Änderung erfolgen."""
    control = _control(database_url)

    with pytest.raises(
        ValueError,
        match="ausdrücklich bestätigt",
    ):
        control.set_connections_allowed(
            allowed=False,
            confirmed=False,
        )

    assert control.inspect().allows_connections is True


def test_rejects_sqlite() -> None:
    """SQLite darf nicht administrativ gesperrt werden."""
    control = _control("sqlite:///test.db")

    with pytest.raises(ValueError, match="ausschließlich"):
        control.inspect()


def test_rejects_other_postgresql_database() -> None:
    """Andere PostgreSQL-Datenbanken bleiben geschützt."""
    control = _control(
        "postgresql+psycopg://ralf@localhost:5432/SimpleOB"
    )

    with pytest.raises(ValueError, match="ausschließlich"):
        control.inspect()


def test_rejects_password_in_url() -> None:
    """Passwörter in Verbindungs-URLs werden abgelehnt."""
    control = _control(
        "postgresql+psycopg://ralf:secret@localhost:5432/"
        "simpleob_migration_test"
    )

    with pytest.raises(ValueError, match="Passwörter"):
        control.inspect()
