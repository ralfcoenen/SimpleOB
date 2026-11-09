"""Kontrollierte Wartungsisolierung einer PostgreSQL-Zieldatenbank."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, make_url

from simpleob.core.config import ApplicationConfig
from simpleob.database.postgresql_migration_lock import (
    MIGRATION_LOCK_KEY,
)
from simpleob.database.postgresql_session_inspection import (
    inspect_postgresql_sessions,
)


def _count_database_sessions(
    connection: Connection,
    database_name: str,
) -> int:
    """Zählt Sitzungen der Ziel-Datenbank ohne eine erlaubte Sitzung."""
    return int(
        connection.execute(
            text(
                "SELECT COUNT(*) "
                "FROM pg_stat_activity "
                "WHERE datname = :database_name "
                "AND pid <> pg_backend_pid()"
            ),
            {"database_name": database_name},
        ).scalar_one()
    )


def _migration_backend_pid(
    connection: Connection,
    target_database: str,
) -> int:
    """Prüft die übergebene Migrationsverbindung und ermittelt ihre PID."""
    if connection.closed or connection.dialect.name != "postgresql":
        raise ValueError(
            "Es ist eine offene PostgreSQL-Migrationsverbindung erforderlich."
        )

    database_name, backend_pid = connection.execute(
        text("SELECT current_database(), pg_backend_pid()")
    ).one()

    if database_name != target_database:
        raise ValueError(
            "Die Migrationsverbindung muss zur bestätigten "
            "Ziel-Datenbank gehören."
        )

    return int(backend_pid)


@contextmanager
def postgresql_maintenance_isolation(
    *,
    application_config: ApplicationConfig,
    target_database: str,
    admin_connection: Connection | None = None,
    migration_connection: Connection | None = None,
    migration_owner_connection: Connection | None = None,
    session_inspection_connection: Connection | None = None,
) -> Iterator[None]:
    """Sperrt neue Verbindungen der ausdrücklich bestätigten Zieldatenbank.

    Bei übergebener admin_connection muss der Aufrufer die
    administrative Advisory-Sperre bereits halten. Diese Funktion
    übernimmt dann weder Erwerb noch Freigabe dieser Sperre.

    Eine übergebene migration_connection bleibt als einzige Sitzung
    der Testdatenbank zugelassen.
    """
    url = make_url(application_config.database_url)

    if (
        url.get_backend_name() != "postgresql"
        or not target_database
        or url.database != target_database
        or target_database in {"postgres", "template0", "template1"}
    ):
        raise ValueError(
            "Die Wartungsisolierung erfordert die ausdrücklich bestätigte "
            "Ziel-Datenbank."
        )

    if url.password is not None:
        raise ValueError("Passwörter in der Datenbank-URL werden nicht unterstützt.")

    if admin_connection is not None:
        if admin_connection.closed or admin_connection.dialect.name != "postgresql":
            raise ValueError(
                "Es ist eine offene administrative PostgreSQL-Verbindung erforderlich."
            )

        admin_database = admin_connection.execute(
            text("SELECT current_database()")
        ).scalar_one()

        if admin_database != "postgres":
            raise ValueError(
                "Die administrative Verbindung muss zur Datenbank 'postgres' gehören."
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
        _migration_backend_pid(migration_connection, target_database)
        if migration_connection is not None
        else None
    )
    operation_connection = migration_owner_connection or admin_connection
    if operation_connection is None:
        raise RuntimeError(
            "Für die Wartungsisolierung wird eine administrative "
            "oder migrationsberechtigte Verbindung benötigt."
        )
    if operation_connection.closed or operation_connection.dialect.name != "postgresql":
        raise ValueError("Die Wartungsverbindung ist nicht gültig.")
    operation_database = operation_connection.execute(
        text("SELECT current_database(), current_user")
    ).one()
    if operation_database.current_database != "postgres":
        raise ValueError(
            "Die Wartungsverbindung muss zur Datenbank 'postgres' gehören."
        )
    if migration_owner_connection is not None:
        owner_check = operation_connection.execute(
            text(
                "SELECT pg_get_userbyid(datdba) = current_user "
                "FROM pg_database WHERE datname = :database_name"
            ),
            {"database_name": target_database},
        ).scalar_one_or_none()
        if not owner_check:
            raise RuntimeError(
                "Die Migrationsrolle ist nicht Eigentümerin der "
                "PostgreSQL-Testdatenbank und darf die Wartungssperre "
                "nicht ändern."
            )

    inspection_connection = session_inspection_connection or migration_connection
    if inspection_connection is None:
        inspection_connection = operation_connection
    if inspection_connection.dialect.name != "postgresql":
        raise ValueError("Die Sitzungsprüfverbindung ist nicht gültig.")

    @contextmanager
    def isolate() -> Iterator[None]:
        status = operation_connection.execute(
            text("SELECT datallowconn FROM pg_database WHERE datname = :database_name"),
            {"database_name": target_database},
        ).scalar_one_or_none()

        if status is None:
            raise RuntimeError("Die bestätigte PostgreSQL-Ziel-Datenbank existiert nicht.")

        if not status:
            raise RuntimeError(
                "Die PostgreSQL-Ziel-Datenbank ist bereits "
                "für neue Verbindungen gesperrt. "
                "Der Wartungszustand ist ungeklärt."
            )

        if session_inspection_connection is not None:
            inspection_database = inspection_connection.execute(
                text("SELECT current_database()")
            ).scalar_one()
            if inspection_database != target_database:
                raise ValueError(
                    "Die Sitzungsprüfverbindung muss zur "
                    "bestätigten PostgreSQL-Ziel-Datenbank gehören."
                )
            sessions_before = inspect_postgresql_sessions(
                inspection_connection,
                excluded_pids=(excluded_pid,) if excluded_pid else (),
            ).other_session_count
        else:
            sessions_before = _count_database_sessions(inspection_connection, target_database)

        if sessions_before:
            raise RuntimeError(
                "Die PostgreSQL-Ziel-Datenbank wird noch "
                f"von {sessions_before} Sitzung(en) verwendet. "
                "Die Wartungsisolierung wurde nicht aktiviert."
            )

        operation_connection.execute(
            text(
                "ALTER DATABASE "
                + operation_connection.dialect.identifier_preparer.quote_identifier(target_database)
                + " WITH ALLOW_CONNECTIONS false"
            )
        )

        # Ab hier muss jede Ausnahme die Verbindungssperre aufheben.
        try:
            if session_inspection_connection is not None:
                sessions_after = inspect_postgresql_sessions(
                    inspection_connection,
                    excluded_pids=(excluded_pid,) if excluded_pid else (),
                ).other_session_count
            else:
                sessions_after = _count_database_sessions(inspection_connection, target_database)

            if sessions_after:
                raise RuntimeError(
                    "Nach Aktivierung der Verbindungssperre "
                    f"bestehen noch {sessions_after} Sitzung(en). "
                    "Die Wartungsisolierung wird abgebrochen."
                )

            yield
        finally:
            try:
                operation_connection.execute(
                    text(
                        "ALTER DATABASE "
                        + operation_connection.dialect.identifier_preparer.quote_identifier(target_database)
                        + " WITH ALLOW_CONNECTIONS true"
                    )
                )
            except Exception:
                if migration_owner_connection is None or admin_connection is None:
                    raise RuntimeError(
                        "Die Wartungssperre konnte nicht aufgehoben werden. "
                        f"{target_database} kann weiterhin für neue "
                        "Verbindungen gesperrt sein; bitte den Datenbankstatus "
                        "administrativ prüfen."
                    ) from None
                try:
                    admin_connection.execute(
                        text(
                            "ALTER DATABASE "
                            + admin_connection.dialect.identifier_preparer.quote_identifier(target_database)
                            + " WITH ALLOW_CONNECTIONS true"
                        )
                    )
                except Exception:
                    raise RuntimeError(
                        "Die Wartungssperre konnte weder mit der "
                        "Migrationsrolle noch mit der Administrationsrolle "
                        f"aufgehoben werden. {target_database} kann "
                        "weiterhin für neue Verbindungen gesperrt sein; "
                        "bitte den Datenbankstatus administrativ prüfen."
                    ) from None

    if admin_connection is not None:
        # Die Sperre gehört dem Aufrufer.
        with isolate():
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
                    "Eine andere administrative PostgreSQL-Wartung ist bereits aktiv."
                )

            try:
                with isolate():
                    yield
            finally:
                connection.execute(
                    text("SELECT pg_advisory_unlock(:lock_key)"),
                    {"lock_key": MIGRATION_LOCK_KEY},
                )
    finally:
        admin_engine.dispose()
