"""Tests für die PostgreSQL-Wartungsisolierung."""

from __future__ import annotations

import os
from unittest.mock import Mock

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from openbilanz.database.postgresql_maintenance_isolation import (
    postgresql_maintenance_isolation,
)


TEST_DATABASE = "simpleob_migration_test"


@pytest.fixture
def database_url() -> str:
    url = os.environ.get("SIMPLEOB_POSTGRES_TEST_URL")

    if not url:
        pytest.skip("PostgreSQL-Testdatenbank nicht konfiguriert.")

    if make_url(url).database != TEST_DATABASE:
        pytest.fail(
            "Tests dürfen ausschließlich simpleob_migration_test verwenden."
        )

    return url


def _config(database_url: str) -> Mock:
    config = Mock()
    config.database_url = database_url
    return config


def _connections_allowed(database_url: str) -> bool:
    url = make_url(database_url)
    engine = create_engine(url.set(database="postgres"))

    try:
        with engine.connect() as connection:
            result = connection.execute(
                text(
                    "SELECT datallowconn FROM pg_database "
                    "WHERE datname = :name"
                ),
                {"name": TEST_DATABASE},
            ).scalar_one()

            return bool(result)
    finally:
        engine.dispose()


def test_rejects_sqlite() -> None:
    with pytest.raises(ValueError, match="ausschließlich"):
        with postgresql_maintenance_isolation(
            application_config=_config("sqlite:///test.db"),
        ):
            pass


def test_rejects_other_postgresql_database() -> None:
    with pytest.raises(ValueError, match="ausschließlich"):
        with postgresql_maintenance_isolation(
            application_config=_config(
                "postgresql+psycopg://ralf@localhost:5432/SimpleOB"
            ),
        ):
            pass


def test_rejects_password_in_url() -> None:
    with pytest.raises(ValueError, match="Passwörter"):
        with postgresql_maintenance_isolation(
            application_config=_config(
                "postgresql+psycopg://ralf:secret@localhost:5432/"
                "simpleob_migration_test"
            ),
        ):
            pass


def test_rejects_already_blocked_database(
    database_url: str,
) -> None:
    """Ein bereits gesperrter Datenbankzustand wird nicht übernommen."""
    url = make_url(database_url)

    admin_engine = create_engine(
        url.set(database="postgres"),
        isolation_level="AUTOCOMMIT",
    )

    try:
        with admin_engine.connect() as connection:
            assert _connections_allowed(database_url) is True

            connection.execute(
                text(
                    'ALTER DATABASE "simpleob_migration_test" '
                    "WITH ALLOW_CONNECTIONS false"
                )
            )

            try:
                with pytest.raises(
                    RuntimeError,
                    match="bereits.*gesperrt",
                ):
                    with postgresql_maintenance_isolation(
                        application_config=_config(database_url),
                    ):
                        pytest.fail(
                            "Bereits gesperrte Datenbank wurde akzeptiert."
                        )

                assert _connections_allowed(database_url) is False
            finally:
                connection.execute(
                    text(
                        'ALTER DATABASE "simpleob_migration_test" '
                        "WITH ALLOW_CONNECTIONS true"
                    )
                )
    finally:
        admin_engine.dispose()

    assert _connections_allowed(database_url) is True


def test_rejects_concurrent_administrative_lock(
    database_url: str,
) -> None:
    """Eine bereits gehaltene Administrationssperre verhindert Wartung."""
    from openbilanz.database.postgresql_migration_lock import (
        MIGRATION_LOCK_KEY,
    )

    url = make_url(database_url)
    engine = create_engine(
        url.set(database="postgres"),
        isolation_level="AUTOCOMMIT",
    )

    try:
        with engine.connect() as connection:
            acquired = connection.execute(
                text("SELECT pg_try_advisory_lock(:key)"),
                {"key": MIGRATION_LOCK_KEY},
            ).scalar_one()

            assert acquired is True

            try:
                with pytest.raises(
                    RuntimeError,
                    match="andere administrative PostgreSQL-Wartung",
                ):
                    with postgresql_maintenance_isolation(
                        application_config=_config(database_url),
                    ):
                        pytest.fail(
                            "Parallele Wartung wurde nicht verhindert."
                        )
            finally:
                connection.execute(
                    text("SELECT pg_advisory_unlock(:key)"),
                    {"key": MIGRATION_LOCK_KEY},
                )
    finally:
        engine.dispose()


def test_maintenance_isolation_restores_connections_after_success(
    database_url: str,
) -> None:
    """Nach erfolgreicher Wartung sind neue Verbindungen wieder erlaubt."""
    assert _connections_allowed(database_url) is True

    with postgresql_maintenance_isolation(
        application_config=_config(database_url),
    ):
        assert _connections_allowed(database_url) is False

        with pytest.raises(Exception):
            engine = create_engine(database_url)

            try:
                with engine.connect():
                    pass
            finally:
                engine.dispose()

    assert _connections_allowed(database_url) is True


def test_maintenance_isolation_restores_connections_after_error(
    database_url: str,
) -> None:
    """Auch nach einer Ausnahme wird die Verbindungssperre aufgehoben."""
    assert _connections_allowed(database_url) is True

    with pytest.raises(
        RuntimeError,
        match="Simulierter Wartungsfehler",
    ):
        with postgresql_maintenance_isolation(
            application_config=_config(database_url),
        ):
            assert _connections_allowed(database_url) is False

            raise RuntimeError("Simulierter Wartungsfehler")

    assert _connections_allowed(database_url) is True
