"""Prüft PostgreSQL-Tabellensperren für administrative Sicherungen."""

from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url


def test_share_lock_blocks_writes_but_allows_reads() -> None:
    """SHARE-Sperre blockiert INSERT, erlaubt aber SELECT."""
    database_url = os.environ.get("SIMPLEOB_POSTGRES_TEST_URL")

    if not database_url:
        pytest.skip("SIMPLEOB_POSTGRES_TEST_URL ist nicht gesetzt.")

    url = make_url(database_url)

    if (
        url.get_backend_name() != "postgresql"
        or url.database != "simpleob_migration_test"
    ):
        pytest.fail(
            "Der Test darf ausschließlich "
            "'simpleob_migration_test' verwenden."
        )

    engine = create_engine(database_url)

    try:
        with engine.connect() as setup:
            setup.execute(
                text(
                    "CREATE TEMP TABLE simpleob_lock_probe "
                    "(id INTEGER)"
                )
            )
            setup.rollback()

        # Eine reguläre Tabelle ist notwendig, weil temporäre
        # Tabellen nicht zwischen Sitzungen sichtbar sind.
        with engine.begin() as setup:
            setup.execute(
                text(
                    "CREATE TABLE simpleob_lock_probe "
                    "(id INTEGER)"
                )
            )

        try:
            with engine.connect() as locker:
                with locker.begin():
                    locker.execute(
                        text(
                            "LOCK TABLE simpleob_lock_probe "
                            "IN SHARE MODE"
                        )
                    )

                    with engine.connect() as reader:
                        result = reader.execute(
                            text(
                                "SELECT COUNT(*) "
                                "FROM simpleob_lock_probe"
                            )
                        ).scalar_one()

                        assert result == 0

                    with engine.connect() as writer:
                        writer.execute(
                            text("SET lock_timeout = '300ms'")
                        )

                        with pytest.raises(
                            Exception,
                            match="lock timeout",
                        ):
                            writer.execute(
                                text(
                                    "INSERT INTO simpleob_lock_probe "
                                    "(id) VALUES (1)"
                                )
                            )

                        writer.rollback()

        finally:
            with engine.begin() as cleanup:
                cleanup.execute(
                    text("DROP TABLE IF EXISTS simpleob_lock_probe")
                )

    finally:
        engine.dispose()


def test_pg_dump_works_during_share_lock(
    tmp_path,
) -> None:
    """pg_dump funktioniert bei bestehender SHARE-Tabellensperre."""
    import os
    import subprocess
    from uuid import uuid4

    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import make_url

    database_url = os.environ.get("SIMPLEOB_POSTGRES_TEST_URL")

    if not database_url:
        pytest.skip("SIMPLEOB_POSTGRES_TEST_URL ist nicht gesetzt.")

    url = make_url(database_url)

    if (
        url.get_backend_name() != "postgresql"
        or url.database != "simpleob_migration_test"
        or url.password is not None
    ):
        pytest.fail(
            "Der Test ist ausschließlich für die passwortlose "
            "PostgreSQL-Testdatenbank 'simpleob_migration_test' zugelassen."
        )

    table_name = f"simpleob_lock_probe_{uuid4().hex}"
    backup_path = tmp_path / "share_lock_backup.dump"

    engine = create_engine(database_url)

    try:
        with engine.begin() as setup:
            setup.execute(
                text(
                    f'CREATE TABLE "{table_name}" (id INTEGER)'
                )
            )

        try:
            with engine.connect() as locker:
                with locker.begin():
                    locker.execute(
                        text(
                            f'LOCK TABLE "{table_name}" IN SHARE MODE'
                        )
                    )

                    result = subprocess.run(
                        [
                            "pg_dump",
                            "--format=custom",
                            "--no-password",
                            "--host",
                            url.host or "localhost",
                            "--port",
                            str(url.port or 5432),
                            "--username",
                            url.username or "",
                            "--dbname",
                            url.database,
                            "--file",
                            str(backup_path),
                        ],
                        capture_output=True,
                        text=True,
                        timeout=30,
                        check=False,
                    )

                    assert result.returncode == 0, result.stderr
                    assert backup_path.is_file()
                    assert backup_path.stat().st_size > 0

        finally:
            with engine.begin() as cleanup:
                cleanup.execute(
                    text(f'DROP TABLE IF EXISTS "{table_name}"')
                )

    finally:
        engine.dispose()


def test_sequence_can_advance_during_table_share_lock() -> None:
    """Prüft, ob nextval trotz SHARE-Sperre der Tabelle möglich ist."""
    import os
    from uuid import uuid4

    import pytest
    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import make_url

    database_url = os.environ.get("SIMPLEOB_POSTGRES_TEST_URL")

    if not database_url:
        pytest.skip("SIMPLEOB_POSTGRES_TEST_URL ist nicht gesetzt.")

    url = make_url(database_url)

    if (
        url.get_backend_name() != "postgresql"
        or url.database != "simpleob_migration_test"
        or url.password is not None
    ):
        pytest.fail("Nur die passwortlose PostgreSQL-Testdatenbank ist erlaubt.")

    table_name = f"simpleob_sequence_probe_{uuid4().hex}"
    engine = create_engine(database_url)

    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    f'CREATE TABLE "{table_name}" '
                    '(id integer GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY)'
                )
            )

        try:
            with engine.connect() as locker:
                with locker.begin():
                    locker.execute(
                        text(f'LOCK TABLE "{table_name}" IN SHARE MODE')
                    )

                    with engine.connect() as other:
                        sequence_name = other.execute(
                            text(
                                "SELECT pg_get_serial_sequence("
                                ":table_name, 'id')"
                            ),
                            {"table_name": table_name},
                        ).scalar_one()

                        assert sequence_name is not None

                        other.execute(text("SET lock_timeout = '300ms'"))

                        value = other.execute(
                            text("SELECT nextval(CAST(:name AS regclass))"),
                            {"name": sequence_name},
                        ).scalar_one()

                        assert value == 1

        finally:
            with engine.begin() as connection:
                connection.execute(
                    text(f'DROP TABLE IF EXISTS "{table_name}"')
                )

    finally:
        engine.dispose()
