"""Kontrollierte Wartungsisolierung einer PostgreSQL-Testdatenbank."""

from __future__ import annotations

from contextlib import contextmanager
from collections.abc import Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from openbilanz.core.config import ApplicationConfig
from openbilanz.database.postgresql_migration_lock import (
    MIGRATION_LOCK_KEY,
)


TEST_DATABASE = "simpleob_migration_test"


@contextmanager
def postgresql_maintenance_isolation(
    *,
    application_config: ApplicationConfig,
) -> Iterator[None]:
    """Sperrt neue Verbindungen während eines Wartungsabschnitts.

    Ausschließlich für simpleob_migration_test.
    Bereits bestehende Sitzungen werden nicht beendet.
    """
    url = make_url(application_config.database_url)

    if (
        url.get_backend_name() != "postgresql"
        or url.database != TEST_DATABASE
    ):
        raise ValueError(
            "Die Wartungsisolierung ist ausschließlich "
            "für 'simpleob_migration_test' zugelassen."
        )

    if url.password is not None:
        raise ValueError(
            "Passwörter in der Datenbank-URL "
            "werden nicht unterstützt."
        )

    admin_engine = create_engine(
        url.set(database="postgres"),
        isolation_level="AUTOCOMMIT",
    )

    try:
        with admin_engine.connect() as connection:
            acquired = connection.execute(
                text("SELECT pg_try_advisory_lock(:lock_key)"),
                {"lock_key": MIGRATION_LOCK_KEY},
            ).scalar_one()

            if not acquired:
                raise RuntimeError(
                    "Eine andere administrative PostgreSQL-Wartung "
                    "ist bereits aktiv."
                )

            try:
                status = connection.execute(
                    text(
                        "SELECT datallowconn FROM pg_database "
                        "WHERE datname = :database_name"
                    ),
                    {"database_name": TEST_DATABASE},
                ).scalar_one_or_none()

                if status is None:
                    raise RuntimeError(
                        "Die PostgreSQL-Testdatenbank existiert nicht."
                    )

                if not status:
                    raise RuntimeError(
                        "Die PostgreSQL-Testdatenbank ist bereits "
                        "für neue Verbindungen gesperrt. "
                        "Der Wartungszustand ist ungeklärt."
                    )

                connection.execute(
                    text(
                        'ALTER DATABASE "simpleob_migration_test" '
                        "WITH ALLOW_CONNECTIONS false"
                    )
                )

                try:
                    yield
                finally:
                    connection.execute(
                        text(
                            'ALTER DATABASE "simpleob_migration_test" '
                            "WITH ALLOW_CONNECTIONS true"
                        )
                    )
            finally:
                connection.execute(
                    text("SELECT pg_advisory_unlock(:lock_key)"),
                    {"lock_key": MIGRATION_LOCK_KEY},
                )
    finally:
        admin_engine.dispose()
