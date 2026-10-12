"""Tests für die administrative PostgreSQL-Schemaprüfung."""

from __future__ import annotations

import os
from unittest.mock import Mock

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from openbilanz.database.migration_service import (
    PostgreSQLSchemaStatus,
)
from openbilanz.database.postgresql_administration_service import (
    PostgreSQLAdministrationService,
)
from openbilanz.database.postgresql_migration_lock import (
    MIGRATION_LOCK_KEY,
)


@pytest.fixture
def database_url() -> str:
    url = os.environ.get("SIMPLEOB_POSTGRES_TEST_URL")

    if not url:
        pytest.skip(
            "SIMPLEOB_POSTGRES_TEST_URL ist nicht gesetzt."
        )

    if make_url(url).database != "simpleob_migration_test":
        pytest.fail(
            "Die Tests dürfen ausschließlich "
            "'simpleob_migration_test' verwenden."
        )

    return url


def _service(database_url: str) -> PostgreSQLAdministrationService:
    config = Mock()
    config.database_url = database_url

    return PostgreSQLAdministrationService(
        application_config=config
    )


def test_administrative_inspection_returns_current_schema(
    database_url: str,
) -> None:
    """Die bestehende Testdatenbank wird korrekt erkannt."""
    result = _service(database_url).inspect_schema()

    assert result.status == PostgreSQLSchemaStatus.CURRENT


def test_administrative_inspection_rejects_existing_lock(
    database_url: str,
) -> None:
    """Eine bereits aktive administrative Sperre verhindert die Prüfung."""
    engine = create_engine(database_url)

    try:
        with engine.connect() as connection:
            connection.execute(
                text("SELECT pg_advisory_lock(:key)"),
                {"key": MIGRATION_LOCK_KEY},
            )
            connection.commit()

            try:
                with pytest.raises(
                    RuntimeError,
                    match="bereits aktiv",
                ):
                    _service(database_url).inspect_schema()
            finally:
                connection.execute(
                    text("SELECT pg_advisory_unlock(:key)"),
                    {"key": MIGRATION_LOCK_KEY},
                )
                connection.rollback()
    finally:
        engine.dispose()


def test_administrative_inspection_releases_lock(
    database_url: str,
) -> None:
    """Nach der Prüfung kann eine andere Verbindung die Sperre erwerben."""
    _service(database_url).inspect_schema()

    engine = create_engine(database_url)

    try:
        with engine.connect() as connection:
            acquired = connection.execute(
                text("SELECT pg_try_advisory_lock(:key)"),
                {"key": MIGRATION_LOCK_KEY},
            ).scalar_one()

            assert acquired is True

            connection.execute(
                text("SELECT pg_advisory_unlock(:key)"),
                {"key": MIGRATION_LOCK_KEY},
            )
            connection.rollback()
    finally:
        engine.dispose()


def test_administrative_inspection_rejects_sqlite() -> None:
    """SQLite darf nicht an den PostgreSQL-Administrationsdienst gelangen."""
    service = _service("sqlite:///:memory:")

    with pytest.raises(
        ValueError,
        match="nur für PostgreSQL",
    ):
        service.inspect_schema()


def test_administrative_inspection_rejects_other_sessions(
    database_url: str,
) -> None:
    """Andere Datenbanksitzungen verhindern die administrative Prüfung."""
    engine = create_engine(database_url)

    try:
        with engine.connect() as other_connection:
            other_connection.execute(text("SELECT 1"))

            with pytest.raises(
                RuntimeError,
                match="anderen Sitzungen",
            ):
                _service(database_url).inspect_schema()
    finally:
        engine.dispose()
