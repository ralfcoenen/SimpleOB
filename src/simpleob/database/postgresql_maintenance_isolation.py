
"""Kontrollierte Wartungsisolierung einer PostgreSQL-Testdatenbank."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, make_url

from simpleob.core.config import ApplicationConfig
from simpleob.database.postgresql_migration_lock import (
    MIGRATION_LOCK_KEY,
)

TEST_DATABASE = "simpleob_migration_test"


def _count_test_database_sessions(
    connection: Connection,
    *,
    excluded_pid: int | None = None,
) -> int:
    """Zählt Sitzungen der Testdatenbank ohne eine erlaubte Sitzung."""
    return int(
        connection.execute(
            text(
                "SELECT COUNT(*) "
                "FROM pg_stat_activity "
                "WHERE datname = :database_name "
                "AND (CAST(:excluded_pid AS integer) IS NULL "
                "OR pid <> CAST(:excluded_pid AS integer))"
            ),
            {
                "database_name": TEST_DATABASE,
                "excluded_pid": excluded_pid,
            },
        ).scalar_one()
    )


def _migration_backend_pid(
    connection: Connection,
) -> int:
    """Prüft die übergebene Migrationsverbindung und ermittelt ihre PID."""
    if connection.closed or connection.dialect.name != "postgresql":
        raise ValueError(
            "Es ist eine offene PostgreSQL-Migrationsverbindung erforderlich."
        )

    database_name, backend_pid = connection.execute(
        text("SELECT current_database(), pg_backend_pid()")
    ).one()

    if database_name != TEST_DATABASE:
        raise ValueError(
            "Die Migrationsverbindung muss zur Datenbank "
            "'simpleob_migration_test' gehören."
        )

    return int(backend_pid)


@contextmanager
def postgresql_maintenance_isolation(
    *,
    application_config: ApplicationConfig,
    admin_connection: Connection | None = None,
    migration_connection: Connection | None = None,
) -> Iterator[None]:
    """Sperrt neue Verbindungen während eines Wartungsabschnitts.

    Ausschließlich für simpleob_migration_test.

    Bei übergebener admin_connection muss der Aufrufer die
    administrative Advisory-Sperre bereits halten. Diese Funktion
    übernimmt dann weder Erwerb noch Freigabe dieser Sperre.

    Eine übergebene migration_connection bleibt als einzige Sitzung
    der Testdatenbank zugelassen.
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

    if admin_connection is not None:
        if (
            admin_connection.closed
            or admin_connection.dialect.name != "postgresql"
        ):
            raise ValueError(
                "Es ist eine offene administrative "
                "PostgreSQL-Verbindung erforderlich."
            )

        admin_database = admin_connection.execute(
            text("SELECT current_database()")
        ).scalar_one()

        if admin_database != "postgres":
            raise ValueError(
                "Die administrative Verbindung muss zur "
                "Datenbank 'postgres' gehören."
            )

        # PostgreSQL-Advisory-Sperren sind sitzungsgebunden.
        # pg_locks bestätigt, dass genau diese Sitzung die Sperre hält.
        lock_held = admin_connection.execute(
            text(
                "SELECT EXISTS ("
                "SELECT 1 FROM pg_locks "
                "WHERE locktype = 'advisory' "
                "AND pid = pg_backend_pid() "
                "AND granted "
                "AND classid = "
                "CAST((CAST(:lock_key AS bigint) >> 32) AS oid) "
                "AND objid = "
                "CAST((CAST(:lock_key AS bigint) & 4294967295) AS oid) "
                "AND objsubid = 1"
                ")"
            ),
            {"lock_key": MIGRATION_LOCK_KEY},
        ).scalar_one()

        if not lock_held:
            raise RuntimeError(
                "Die übergebene administrative Verbindung "
                "hält die erforderliche PostgreSQL-Sperre nicht."
            )

    excluded_pid = (
        _migration_backend_pid(migration_connection)
        if migration_connection is not None
        else None
    )

    @contextmanager
    def isolate(connection: Connection) -> Iterator[None]:
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

        sessions_before = _count_test_database_sessions(
            connection,
            excluded_pid=excluded_pid,
        )

        if sessions_before:
            raise RuntimeError(
                "Die PostgreSQL-Testdatenbank wird noch "
                f"von {sessions_before} Sitzung(en) verwendet. "
                "Die Wartungsisolierung wurde nicht aktiviert."
            )

        connection.execute(
            text(
                'ALTER DATABASE "simpleob_migration_test" '
                "WITH ALLOW_CONNECTIONS false"
            )
        )

        # Ab hier muss jede Ausnahme die Verbindungssperre aufheben.
        try:
            sessions_after = _count_test_database_sessions(
                connection,
                excluded_pid=excluded_pid,
            )

            if sessions_after:
                raise RuntimeError(
                    "Nach Aktivierung der Verbindungssperre "
                    f"bestehen noch {sessions_after} Sitzung(en). "
                    "Die Wartungsisolierung wird abgebrochen."
                )

            yield
        finally:
            connection.execute(
                text(
                    'ALTER DATABASE "simpleob_migration_test" '
                    "WITH ALLOW_CONNECTIONS true"
                )
            )

    if admin_connection is not None:
        # Die Sperre gehört dem Aufrufer.
        with isolate(admin_connection):
            yield
        return

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
                with isolate(connection):
                    yield
            finally:
                connection.execute(
                    text("SELECT pg_advisory_unlock(:lock_key)"),
                    {"lock_key": MIGRATION_LOCK_KEY},
                )
    finally:
        admin_engine.dispose()
