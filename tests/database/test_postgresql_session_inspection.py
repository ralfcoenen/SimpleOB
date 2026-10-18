"""Tests der schreibgeschützten PostgreSQL-Sitzungsprüfung."""

from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url

from simpleob.database.postgresql_session_inspection import (
    inspect_postgresql_sessions,
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
            "Der Test darf ausschließlich "
            "'simpleob_migration_test' verwenden."
        )

    return url


def test_session_inspection_rejects_sqlite() -> None:
    engine = create_engine("sqlite:///:memory:")

    try:
        with engine.connect() as connection:
            with pytest.raises(
                ValueError,
                match="nur für PostgreSQL",
            ):
                inspect_postgresql_sessions(connection)
    finally:
        engine.dispose()


def test_session_inspection_detects_other_connection(
    database_url: str,
) -> None:
    engine = create_engine(database_url)

    try:
        with engine.connect() as first:
            with engine.connect() as second:
                # Die zweite Verbindung führt eine Abfrage aus,
                # damit eine eigene PostgreSQL-Sitzung besteht.
                second.exec_driver_sql("SELECT 1")

                result = inspect_postgresql_sessions(first)

                assert result.has_other_sessions
                assert result.other_session_count >= 1
    finally:
        engine.dispose()


def test_session_inspection_excludes_own_connection(
    database_url: str,
) -> None:
    engine = create_engine(database_url)

    try:
        with engine.connect() as connection:
            result = inspect_postgresql_sessions(connection)

            assert result.other_session_count >= 0
            assert (
                result.other_session_count
                == result.active_session_count
                + result.idle_session_count
                + result.unknown_state_count
            )
    finally:
        engine.dispose()
