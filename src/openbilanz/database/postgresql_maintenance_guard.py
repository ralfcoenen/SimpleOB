"""Transaktionsgebundener Wartungsschutz für PostgreSQL."""

from __future__ import annotations

import time

from sqlalchemy import event
from sqlalchemy.engine import Engine

from openbilanz.database.lock_error import DatabaseLockError
from openbilanz.database.postgresql_migration_lock import (
    MIGRATION_LOCK_KEY,
)

LOCK_TIMEOUT_SECONDS = 3.0
LOCK_RETRY_SECONDS = 0.05


def install_postgresql_maintenance_guard(
    engine: Engine,
) -> None:
    """Schützt reguläre PostgreSQL-Transaktionen während Migrationen."""

    if engine.dialect.name != "postgresql":
        return

    @event.listens_for(engine, "before_cursor_execute")
    def acquire_maintenance_lock(
        conn,
        cursor,
        statement,
        parameters,
        context,
        executemany,
    ) -> None:
        deadline = time.monotonic() + LOCK_TIMEOUT_SECONDS

        while True:
            # Direkte DBAPI-Ausführung verhindert eine Rekursion
            # des SQLAlchemy-Ereignisses.
            cursor.execute(
                "SELECT pg_try_advisory_xact_lock_shared(%s)",
                (MIGRATION_LOCK_KEY,),
            )

            acquired = cursor.fetchone()[0]

            if acquired:
                return

            if time.monotonic() >= deadline:
                raise DatabaseLockError(
                    "Die PostgreSQL-Datenbank wird derzeit "
                    "administrativ gewartet. "
                    "Bitte versuchen Sie es später erneut."
                )

            time.sleep(LOCK_RETRY_SECONDS)
