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
) -> PostgreSQLSessionInspection:
    """Ermittelt andere Sitzungen derselben PostgreSQL-Datenbank.

    Die eigene Sitzung wird ausgeschlossen. Es erfolgen ausschließlich
    lesende SQL-Abfragen.

    Die Prüfung verändert weder die Verbindung noch ihren
    Transaktionszustand durch explizites Commit oder Rollback.
    """

    if connection.dialect.name != "postgresql":
        raise ValueError(
            "Die Sitzungsprüfung ist nur für PostgreSQL vorgesehen."
        )

    rows = connection.execute(
        text(
            """
            SELECT state, COUNT(*) AS session_count
            FROM pg_stat_activity
            WHERE datname = current_database()
              AND pid <> pg_backend_pid()
            GROUP BY state
            """
        )
    ).all()

    active = 0
    idle = 0
    unknown = 0

    for state, count in rows:
        count = int(count)

        if state == "active":
            active += count
        elif state == "idle":
            idle += count
        else:
            unknown += count

    return PostgreSQLSessionInspection(
        other_session_count=active + idle + unknown,
        active_session_count=active,
        idle_session_count=idle,
        unknown_state_count=unknown,
    )
