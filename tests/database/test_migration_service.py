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


BASELINE_REVISION = "7392d6cc6892"


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


def _backup_file(
    database_file: Path,
) -> Path:
    return database_file.with_name(
        f"{database_file.stem}"
        "-before-migration"
        f"{database_file.suffix}"
    )


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
    assert not _backup_file(database_file).exists()


def test_alembic_database_is_backed_up_and_upgraded_to_head(
    tmp_path: Path,
) -> None:
    database_file = tmp_path / "managed.db"

    alembic_config = _alembic_config(
        database_file
    )

    command.upgrade(
        alembic_config,
        BASELINE_REVISION,
    )

    assert _current_revision(database_file) == (
        BASELINE_REVISION
    )

    DatabaseMigrationService(
        application_config=_application_config(
            database_file
        )
    ).upgrade_to_head()

    backup_file = _backup_file(database_file)

    assert backup_file.is_file()
    assert _current_revision(backup_file) == (
        BASELINE_REVISION
    )
    assert _current_revision(database_file) == (
        LEGACY_SCHEMA_REVISION
    )


def test_database_already_at_head_is_not_backed_up(
    tmp_path: Path,
) -> None:
    database_file = tmp_path / "current.db"

    alembic_config = _alembic_config(
        database_file
    )

    command.upgrade(
        alembic_config,
        "head",
    )

    assert _current_revision(database_file) == (
        LEGACY_SCHEMA_REVISION
    )

    DatabaseMigrationService(
        application_config=_application_config(
            database_file
        )
    ).upgrade_to_head()

    assert _current_revision(database_file) == (
        LEGACY_SCHEMA_REVISION
    )
    assert not _backup_file(database_file).exists()


def test_legacy_database_is_backed_up_before_stamp(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_file = tmp_path / "legacy.db"

    with sqlite3.connect(database_file) as connection:
        connection.execute(
            """
            CREATE TABLE legacy_test (
                id INTEGER PRIMARY KEY,
                wert TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO legacy_test (wert)
            VALUES ('vor Migration')
            """
        )
        connection.commit()

    service = DatabaseMigrationService(
        application_config=_application_config(
            database_file
        )
    )

    monkeypatch.setattr(
        service,
        "_matches_legacy_schema",
        lambda **_: True,
    )

    calls: list[tuple[str, str]] = []

    def fake_stamp(
        config: Config,
        revision: str,
    ) -> None:
        calls.append(
            ("stamp", revision)
        )

    def fake_upgrade(
        config: Config,
        revision: str,
    ) -> None:
        calls.append(
            ("upgrade", revision)
        )

    monkeypatch.setattr(
        command,
        "stamp",
        fake_stamp,
    )
    monkeypatch.setattr(
        command,
        "upgrade",
        fake_upgrade,
    )

    service.upgrade_to_head()

    backup_file = _backup_file(database_file)

    assert backup_file.is_file()

    with sqlite3.connect(backup_file) as connection:
        value = connection.execute(
            "SELECT wert FROM legacy_test"
        ).fetchone()[0]

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

    assert value == "vor Migration"
    assert "alembic_version" not in tables

    assert calls == [
        ("stamp", LEGACY_SCHEMA_REVISION),
        ("upgrade", "head"),
    ]

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
    assert not _backup_file(database_file).exists()
