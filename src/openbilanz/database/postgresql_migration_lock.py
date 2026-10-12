"""Exklusive administrative PostgreSQL-Migrationssperre."""

from __future__ import annotations

from contextlib import contextmanager
from collections.abc import Iterator

from sqlalchemy import text
from sqlalchemy.engine import Connection


# Fester, SimpleOB-spezifischer Advisory-Lock-Schlüssel.
# Innerhalb einer PostgreSQL-Datenbank müssen alle
# administrativen Migrationen denselben Schlüssel verwenden.
MIGRATION_LOCK_KEY = 726184391


@contextmanager
def postgresql_migration_lock(
    connection: Connection,
) -> Iterator[Connection]:
    """Hält eine exklusive Migrationssperre auf der Verbindung.

    Die Verbindung wird vom Aufrufer bereitgestellt und bleibt
    in dessen Verantwortung.
    """

    if connection.dialect.name != "postgresql":
        raise ValueError(
            "Die Migrationssperre ist nur für PostgreSQL vorgesehen."
        )

    acquired = connection.execute(
        text("SELECT pg_try_advisory_lock(:lock_key)"),
        {"lock_key": MIGRATION_LOCK_KEY},
    ).scalar_one()

    # Die SELECT-Anweisung kann eine implizite Transaktion
    # beginnen. Diese beenden wir, ohne die sessiongebundene
    # Advisory-Sperre freizugeben.
    connection.commit()

    if not acquired:
        raise RuntimeError(
            "Eine andere administrative PostgreSQL-Migration "
            "ist bereits aktiv."
        )

    try:
        yield connection

    finally:
        try:
            connection.execute(
                text("SELECT pg_advisory_unlock(:lock_key)"),
                {"lock_key": MIGRATION_LOCK_KEY},
            )
        finally:
            # Eine durch die Freigabeabfrage begonnene
            # implizite Transaktion abschließen.
            connection.rollback()
