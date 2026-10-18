"""Integrationstests für den PostgreSQL-Wartungsschutz."""

import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from simpleob.database.postgresql_maintenance_guard import (
    install_postgresql_maintenance_guard,
)
from simpleob.database.postgresql_migration_lock import (
    postgresql_migration_lock,
)
from simpleob.database.lock_error import DatabaseLockError

@pytest.fixture
def database_url() -> str:
    url = os.environ.get("SIMPLEOB_POSTGRES_TEST_URL")

    if not url:
        pytest.skip("SIMPLEOB_POSTGRES_TEST_URL ist nicht gesetzt.")

    parsed = make_url(url)

    if (
        parsed.get_backend_name() != "postgresql"
        or parsed.database != "simpleob_migration_test"
    ):
        pytest.fail(
            "Nur simpleob_migration_test ist für diesen Test erlaubt."
        )

    return url


def test_active_transaction_blocks_migration_lock(
    database_url: str,
) -> None:
    application_engine = create_engine(database_url)
    administration_engine = create_engine(database_url)

    install_postgresql_maintenance_guard(application_engine)

    try:
        with (
            application_engine.connect() as application,
            administration_engine.connect() as administration,
        ):
            application.execute(text("SELECT 1"))

            with pytest.raises(
                RuntimeError,
                match="bereits aktiv",
            ):
                with postgresql_migration_lock(administration):
                    pass

            application.rollback()

            with postgresql_migration_lock(administration):
                pass

    finally:
        application_engine.dispose()
        administration_engine.dispose()


def test_lock_is_reacquired_after_commit(
    database_url: str,
) -> None:
    application_engine = create_engine(database_url)
    administration_engine = create_engine(database_url)

    install_postgresql_maintenance_guard(application_engine)

    try:
        with (
            application_engine.connect() as application,
            administration_engine.connect() as administration,
        ):
            application.execute(text("SELECT 1"))
            application.commit()

            with postgresql_migration_lock(administration):
                with pytest.raises(
                    DatabaseLockError,
                    match="administrativ gewartet",
                ):
                    application.execute(text("SELECT 2"))

            application.rollback()
            assert application.execute(
                text("SELECT 3")
            ).scalar_one() == 3

    finally:
        application_engine.dispose()
        administration_engine.dispose()


def test_lock_is_reacquired_after_rollback(
    database_url: str,
) -> None:
    application_engine = create_engine(database_url)
    administration_engine = create_engine(database_url)

    install_postgresql_maintenance_guard(application_engine)

    try:
        with (
            application_engine.connect() as application,
            administration_engine.connect() as administration,
        ):
            application.execute(text("SELECT 1"))
            application.rollback()

            with postgresql_migration_lock(administration):
                with pytest.raises(
                    DatabaseLockError,
                    match="administrativ gewartet",
                ):
                    application.execute(text("SELECT 2"))

            application.rollback()

    finally:
        application_engine.dispose()
        administration_engine.dispose()


def test_maintenance_lock_with_reused_pool_connection(
    database_url: str,
) -> None:
    """Eine wiederverwendete Verbindung erwirbt die Sperre erneut."""
    from sqlalchemy.pool import QueuePool

    application_engine = create_engine(
        database_url,
        poolclass=QueuePool,
        pool_size=1,
        max_overflow=0,
    )
    administration_engine = create_engine(database_url)

    install_postgresql_maintenance_guard(application_engine)

    try:
        # Erster Checkout: Transaktion ausführen und abschließen.
        with application_engine.connect() as application:
            backend_pid_first = application.execute(
                text("SELECT pg_backend_pid()")
            ).scalar_one()

            application.commit()

        # Zweiter Checkout: dieselbe physische PostgreSQL-Verbindung.
        with (
            application_engine.connect() as application,
            administration_engine.connect() as administration,
        ):
            backend_pid_second = application.execute(
                text("SELECT pg_backend_pid()")
            ).scalar_one()

            assert backend_pid_second == backend_pid_first

            # Die neue Transaktion muss die administrative
            # Migrationssperre verhindern.
            with pytest.raises(
                RuntimeError,
                match="bereits aktiv",
            ):
                with postgresql_migration_lock(administration):
                    pass

            application.rollback()

            # Nach Transaktionsende muss die exklusive
            # Migrationssperre wieder verfügbar sein.
            with postgresql_migration_lock(administration):
                pass

    finally:
        application_engine.dispose()
        administration_engine.dispose()


def test_connection_recovers_after_maintenance_timeout(
    database_url: str,
) -> None:
    """Nach einem Wartungs-Timeout ist die Verbindung wieder nutzbar."""
    application_engine = create_engine(database_url)
    administration_engine = create_engine(database_url)

    install_postgresql_maintenance_guard(application_engine)

    try:
        with (
            application_engine.connect() as application,
            administration_engine.connect() as administration,
        ):
            with postgresql_migration_lock(administration):
                with pytest.raises(
                    DatabaseLockError,
                    match="administrativ gewartet",
                ):
                    application.execute(text("SELECT 1"))

                # Fehlgeschlagene Transaktion ausdrücklich beenden.
                application.rollback()

            # Nach Freigabe der Wartungssperre muss dieselbe
            # Verbindung wieder normal arbeiten können.
            assert application.execute(
                text("SELECT 2")
            ).scalar_one() == 2

            application.commit()

    finally:
        application_engine.dispose()
        administration_engine.dispose()
