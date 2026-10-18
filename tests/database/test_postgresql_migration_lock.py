"""Tests für die administrative PostgreSQL-Migrationssperre."""

from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from simpleob.database.postgresql_migration_lock import (
    MIGRATION_LOCK_KEY,
    postgresql_migration_lock,
)


@pytest.fixture
def database_url() -> str:
    url = os.environ.get("SIMPLEOB_POSTGRES_TEST_URL")

    if not url:
        pytest.skip(
            "SIMPLEOB_POSTGRES_TEST_URL ist nicht gesetzt."
        )

    parsed = make_url(url)

    if (
        parsed.get_backend_name() != "postgresql"
        or parsed.database != "simpleob_migration_test"
    ):
        pytest.fail(
            "Die Tests dürfen ausschließlich "
            "'simpleob_migration_test' verwenden."
        )

    return url


def test_lock_rejects_sqlite(tmp_path) -> None:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}"
    )

    try:
        with engine.connect() as connection:
            with pytest.raises(
                ValueError,
                match="nur für PostgreSQL",
            ):
                with postgresql_migration_lock(connection):
                    pass
    finally:
        engine.dispose()


def test_second_connection_cannot_acquire_lock(
    database_url: str,
) -> None:
    engine = create_engine(database_url)

    try:
        with (
            engine.connect() as first,
            engine.connect() as second,
        ):
            with postgresql_migration_lock(first):
                with pytest.raises(
                    RuntimeError,
                    match="bereits aktiv",
                ):
                    with postgresql_migration_lock(second):
                        pass

            with postgresql_migration_lock(second):
                assert second.execute(
                    text(
                        "SELECT pg_try_advisory_lock(:key)"
                    ),
                    {"key": MIGRATION_LOCK_KEY},
                ).scalar_one()

                # PostgreSQL-Advisory-Sperren sind innerhalb
                # derselben Session mehrfach erwerbbar.
                # Den zusätzlichen Erwerb wieder freigeben.
                second.execute(
                    text(
                        "SELECT pg_advisory_unlock(:key)"
                    ),
                    {"key": MIGRATION_LOCK_KEY},
                )

    finally:
        engine.dispose()


def test_lock_is_released_after_exception(
    database_url: str,
) -> None:
    engine = create_engine(database_url)

    try:
        with (
            engine.connect() as first,
            engine.connect() as second,
        ):
            with pytest.raises(
                RuntimeError,
                match="Testfehler",
            ):
                with postgresql_migration_lock(first):
                    raise RuntimeError("Testfehler")

            with postgresql_migration_lock(second):
                assert second.execute(
                    text("SELECT 1")
                ).scalar_one() == 1

    finally:
        engine.dispose()


def test_lock_survives_transaction_commit(
    database_url: str,
) -> None:
    """Die sessiongebundene Sperre überlebt einen Commit."""
    engine = create_engine(database_url)

    try:
        with (
            engine.connect() as first,
            engine.connect() as second,
        ):
            with postgresql_migration_lock(first):
                with first.begin():
                    first.execute(text("SELECT 1"))

                with pytest.raises(
                    RuntimeError,
                    match="bereits aktiv",
                ):
                    with postgresql_migration_lock(second):
                        pass

            with postgresql_migration_lock(second):
                pass

    finally:
        engine.dispose()
