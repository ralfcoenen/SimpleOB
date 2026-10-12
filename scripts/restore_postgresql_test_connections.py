#!/usr/bin/env python3
"""Stellt die Erreichbarkeit der PostgreSQL-Testdatenbank wieder her."""

from __future__ import annotations

import os
import sys

import psycopg


DATABASE_NAME = "simpleob_migration_test"


def main() -> int:
    print(f"PostgreSQL-Verbindungsfreigabe: {DATABASE_NAME}")

    confirmation = input(
        "Verbindungen für diese Testdatenbank freigeben? "
        "Zur Bestätigung FREIGEBEN eingeben: "
    )

    if confirmation != "FREIGEBEN":
        print("Abgebrochen. Keine Änderung vorgenommen.")
        return 1

    try:
        with psycopg.connect(
            dbname="postgres",
            host=os.environ.get("PGHOST", "localhost"),
            port=os.environ.get("PGPORT", "5432"),
            user=os.environ.get("PGUSER") or os.environ.get("USER"),
            autocommit=True,
            connect_timeout=5,
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT datallowconn FROM pg_database "
                    "WHERE datname = %s",
                    (DATABASE_NAME,),
                )
                row = cursor.fetchone()

                if row is None:
                    raise RuntimeError(
                        "Die Testdatenbank existiert nicht."
                    )

                if row[0]:
                    print(
                        "Die Testdatenbank erlaubt bereits "
                        "neue Verbindungen."
                    )
                    return 0

                cursor.execute(
                    'ALTER DATABASE "simpleob_migration_test" '
                    "WITH ALLOW_CONNECTIONS true"
                )

                cursor.execute(
                    "SELECT datallowconn FROM pg_database "
                    "WHERE datname = %s",
                    (DATABASE_NAME,),
                )
                result = cursor.fetchone()

                if result is None or result[0] is not True:
                    raise RuntimeError(
                        "Die Verbindungsfreigabe konnte "
                        "nicht bestätigt werden."
                    )

        print("Erfolgreich: Neue Verbindungen sind wieder erlaubt.")
        return 0

    except (psycopg.Error, OSError, RuntimeError) as exc:
        print(f"Fehler: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
