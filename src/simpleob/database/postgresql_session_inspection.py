"""Schreibgeschützte Prüfung aktiver PostgreSQL-Datenbanksitzungen."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.engine import Connection


@dataclass(frozen=True, slots=True)
class PostgreSQLSessionInspection:
    """Ergebnis der Prüfung anderer Datenbanksitzungen."""

    other_session_count: int
    active_session_count: int
    idle_session_count: int
    unknown_state_count: int

    @property
    def has_other_sessions(self) -> bool:
        return self.other_session_count > 0


def inspect_postgresql_sessions(
    connection: Connection,
    *,
    excluded_pids: tuple[int, ...] = (),
) -> PostgreSQLSessionInspection:
    """Ermittelt andere Sitzungen derselben PostgreSQL-Datenbank.

    Die eigene Sitzung wird ausgeschlossen. Es erfolgen ausschließlich
    lesende SQL-Abfragen.

    Die Prüfung verändert weder die Verbindung noch ihren
    Transaktionszustand durch explizites Commit oder Rollback.
    """

    if connection.dialect.name != "postgresql":
        raise ValueError("Die Sitzungsprüfung ist nur für PostgreSQL vorgesehen.")

    excluded = tuple(int(pid) for pid in excluded_pids)
    exclusion_sql = "".join(f" AND pid <> {pid}" for pid in excluded)
    session_count = connection.execute(
        text(
            f"""
            SELECT COUNT(*)
            FROM pg_stat_activity
            WHERE datid = (
                    SELECT oid FROM pg_database WHERE datname = current_database()
                  )
              AND pid <> pg_backend_pid()
              {exclusion_sql}
            """
        )
    ).scalar_one()
    total = int(session_count)

    return PostgreSQLSessionInspection(
        other_session_count=total,
        # Session state is protected statistics data. Keep the compatibility
        # fields, but classify counted sessions as unknown without reading it.
        active_session_count=0,
        idle_session_count=0,
        unknown_state_count=total,
    )
