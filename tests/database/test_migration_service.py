"""Tests für den produktiven Alembic-Migrationsdienst."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

from openbilanz.core.config import ApplicationConfig
from openbilanz.database.migration_service import (
    LEGACY_SCHEMA_REVISION,
    DatabaseMigrationService,
)


def _application_config(
    database_file: Path,
) -> ApplicationConfig:
    return ApplicationConfig(
        data_dir=database_file.parent,
        database_file=database_file,
        taxonomy_dir=database_file.parent / "taxonomy",
        config_file=database_file.parent / "config.toml",
    )


def _alembic_config(
    database_file: Path,
) -> Config:
    project_root = Path(__file__).resolve().parents[2]

    config = Config(
        str(project_root / "alembic.ini")
    )

    config.set_main_option(
        "script_location",
        str(project_root / "migrations"),
    )

    config.attributes["database_url"] = (
        f"sqlite:///{database_file}"
    )

    return config


def _current_revision(
    database_file: Path,
) -> str | None:
    with sqlite3.connect(database_file) as connection:
        row = connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone()

    if row is None:
        return None

    return row[0]


def test_new_database_is_upgraded_to_head(
    tmp_path: Path,
) -> None:
    database_file = tmp_path / "new.db"

    DatabaseMigrationService(
        application_config=_application_config(
            database_file
        )
    ).upgrade_to_head()

    assert database_file.is_file()
    assert _current_revision(database_file) == (
        LEGACY_SCHEMA_REVISION
    )


def test_alembic_database_is_upgraded_to_head(
    tmp_path: Path,
) -> None:
    database_file = tmp_path / "managed.db"

    alembic_config = _alembic_config(
        database_file
    )

    command.upgrade(
        alembic_config,
        "7392d6cc6892",
    )

    assert _current_revision(database_file) == (
        "7392d6cc6892"
    )

    DatabaseMigrationService(
        application_config=_application_config(
            database_file
        )
    ).upgrade_to_head()

    assert _current_revision(database_file) == (
        LEGACY_SCHEMA_REVISION
    )


def test_unknown_unversioned_database_is_rejected(
    tmp_path: Path,
) -> None:
    database_file = tmp_path / "unknown.db"

    with sqlite3.connect(database_file) as connection:
        connection.execute(
            """
            CREATE TABLE fremde_tabelle (
                id INTEGER PRIMARY KEY,
                wert TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO fremde_tabelle (wert)
            VALUES ('unverändert')
            """
        )
        connection.commit()

    service = DatabaseMigrationService(
        application_config=_application_config(
            database_file
        )
    )

    with pytest.raises(
        RuntimeError,
        match="entspricht nicht dem bekannten Legacy-Schema",
    ):
        service.upgrade_to_head()

    with sqlite3.connect(database_file) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                """
            )
        }

        value = connection.execute(
            "SELECT wert FROM fremde_tabelle"
        ).fetchone()[0]

    assert "alembic_version" not in tables
    assert "fremde_tabelle" in tables
    assert value == "unverändert"
