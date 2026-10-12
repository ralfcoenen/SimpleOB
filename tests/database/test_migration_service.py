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
    PostgreSQLSchemaStatus,
)


BASELINE_REVISION = "7392d6cc6892"
HEAD_REVISION = "3d5f3f742f56"


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
        HEAD_REVISION
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

    assert _current_revision(database_file) == (
        HEAD_REVISION
    )

    backup_file = _backup_file(database_file)

    assert backup_file.is_file()
    assert _current_revision(backup_file) == (
        BASELINE_REVISION
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
        HEAD_REVISION
    )

    DatabaseMigrationService(
        application_config=_application_config(
            database_file
        )
    ).upgrade_to_head()

    assert _current_revision(database_file) == (
        HEAD_REVISION
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


def test_postgresql_start_check_rejects_sqlite(
    tmp_path: Path,
) -> None:
    service = DatabaseMigrationService(
        application_config=_application_config(
            tmp_path / "test.db"
        )
    )

    with pytest.raises(
        ValueError,
        match="nur für PostgreSQL",
    ):
        service.check_ready_for_start()


def test_postgresql_start_check_rejects_empty_database(
    monkeypatch,
    tmp_path: Path,
) -> None:
    from dataclasses import replace
    from unittest.mock import MagicMock

    import openbilanz.database.migration_service as module

    config = replace(
        _application_config(tmp_path / "test.db"),
        database_url_override=(
            "postgresql+psycopg://"
            "ralf@localhost:5432/simpleob_migration_test"
        ),
    )

    engine = MagicMock()
    inspector = MagicMock()
    inspector.get_table_names.return_value = []

    monkeypatch.setattr(
        module,
        "create_engine",
        lambda url: engine,
    )
    monkeypatch.setattr(
        module,
        "inspect",
        lambda engine: inspector,
    )

    service = DatabaseMigrationService(
        application_config=config
    )

    with pytest.raises(
        RuntimeError,
        match="noch nicht",
    ):
        service.check_ready_for_start()

    engine.dispose.assert_called_once()

def test_postgresql_start_check_accepts_current_schema(
    tmp_path: Path,
) -> None:
    import os
    from dataclasses import replace

    from sqlalchemy import create_engine, text

    database_url = os.environ.get(
        "SIMPLEOB_POSTGRES_TEST_URL"
    )

    if not database_url:
        pytest.skip(
            "SIMPLEOB_POSTGRES_TEST_URL ist nicht gesetzt."
        )

    from sqlalchemy.engine import make_url

    parsed_url = make_url(database_url)

    if (
        parsed_url.get_backend_name() != "postgresql"
        or parsed_url.database != "simpleob_migration_test"
    ):
        pytest.fail(
            "Der Test darf ausschließlich die Datenbank "
            "'simpleob_migration_test' verwenden."
        )

    config = replace(
        _application_config(tmp_path / "unused.db"),
        database_url_override=database_url,
    )

    engine = create_engine(database_url)

    try:
        with engine.connect() as connection:
            revision_before = connection.execute(
                text(
                    "SELECT version_num "
                    "FROM alembic_version"
                )
            ).scalar_one()

        DatabaseMigrationService(
            application_config=config
        ).check_ready_for_start()

        with engine.connect() as connection:
            revision_after = connection.execute(
                text(
                    "SELECT version_num "
                    "FROM alembic_version"
                )
            ).scalar_one()

        assert revision_before == HEAD_REVISION
        assert revision_after == revision_before

    finally:
        engine.dispose()

def test_postgresql_inspection_rejects_sqlite(
    tmp_path: Path,
) -> None:
    service = DatabaseMigrationService(
        application_config=_application_config(
            tmp_path / "test.db"
        )
    )

    with pytest.raises(
        ValueError,
        match="nur für PostgreSQL",
    ):
        service.inspect_postgresql_schema()


@pytest.mark.parametrize(
    ("tables", "expected_status"),
    [
        ([], PostgreSQLSchemaStatus.EMPTY),
        (
            ["fremde_tabelle"],
            PostgreSQLSchemaStatus.UNKNOWN,
        ),
    ],
)
def test_postgresql_inspection_without_alembic_version(
    monkeypatch,
    tmp_path: Path,
    tables,
    expected_status,
) -> None:
    from dataclasses import replace
    from unittest.mock import MagicMock

    import openbilanz.database.migration_service as module

    config = replace(
        _application_config(tmp_path / "unused.db"),
        database_url_override=(
            "postgresql+psycopg://"
            "testuser@localhost:5432/simpleob_migration_test"
        ),
    )

    engine = MagicMock()
    connection = engine.connect.return_value.__enter__.return_value
    inspector = MagicMock()
    inspector.get_table_names.return_value = tables

    monkeypatch.setattr(
        module,
        "create_engine",
        lambda url: engine,
    )
    monkeypatch.setattr(
        module,
        "inspect",
        lambda value: inspector,
    )

    service = DatabaseMigrationService(
        application_config=config
    )

    result = service.inspect_postgresql_schema()

    assert result.status == expected_status
    assert result.current_revision is None
    assert result.head_revision == HEAD_REVISION

    engine.dispose.assert_called_once()


def test_postgresql_inspection_current_schema(
    tmp_path: Path,
) -> None:
    """Erkennt die aktuelle Revision ohne Schemaänderung."""
    import os
    from dataclasses import replace

    from sqlalchemy.engine import make_url

    database_url = os.environ.get(
        "SIMPLEOB_POSTGRES_TEST_URL"
    )

    if not database_url:
        pytest.skip(
            "SIMPLEOB_POSTGRES_TEST_URL ist nicht gesetzt."
        )

    parsed_url = make_url(database_url)

    if (
        parsed_url.get_backend_name() != "postgresql"
        or parsed_url.database != "simpleob_migration_test"
    ):
        pytest.fail(
            "Nur simpleob_migration_test ist zugelassen."
        )

    config = replace(
        _application_config(tmp_path / "unused.db"),
        database_url_override=database_url,
    )

    result = DatabaseMigrationService(
        application_config=config
    ).inspect_postgresql_schema()

    assert result.status == PostgreSQLSchemaStatus.CURRENT
    assert result.current_revision == HEAD_REVISION
    assert result.head_revision == HEAD_REVISION


def test_postgresql_inspection_outdated_schema(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """Erkennt eine bekannte ältere Revision."""
    from dataclasses import replace
    from unittest.mock import MagicMock

    import openbilanz.database.migration_service as module

    config = replace(
        _application_config(tmp_path / "unused.db"),
        database_url_override=(
            "postgresql+psycopg://"
            "testuser@localhost:5432/simpleob_migration_test"
        ),
    )

    engine = MagicMock()
    connection = (
        engine.connect.return_value.__enter__.return_value
    )

    inspector = MagicMock()
    inspector.get_table_names.return_value = [
        "alembic_version",
        "mandanten",
    ]

    migration_context = MagicMock()
    migration_context.get_current_revision.return_value = (
        BASELINE_REVISION
    )

    monkeypatch.setattr(
        module,
        "create_engine",
        lambda url: engine,
    )
    monkeypatch.setattr(
        module,
        "inspect",
        lambda value: inspector,
    )
    monkeypatch.setattr(
        module.MigrationContext,
        "configure",
        lambda value: migration_context,
    )

    result = DatabaseMigrationService(
        application_config=config
    ).inspect_postgresql_schema()

    assert result.status == PostgreSQLSchemaStatus.OUTDATED
    assert result.current_revision == BASELINE_REVISION
    assert result.head_revision == HEAD_REVISION

    engine.dispose.assert_called_once()


def test_postgresql_inspection_unknown_revision(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """Verweigert eine unbekannte Alembic-Revision."""
    from dataclasses import replace
    from unittest.mock import MagicMock

    import openbilanz.database.migration_service as module

    config = replace(
        _application_config(tmp_path / "unused.db"),
        database_url_override=(
            "postgresql+psycopg://"
            "testuser@localhost:5432/simpleob_migration_test"
        ),
    )

    engine = MagicMock()
    connection = (
        engine.connect.return_value.__enter__.return_value
    )

    inspector = MagicMock()
    inspector.get_table_names.return_value = [
        "alembic_version",
        "mandanten",
    ]

    migration_context = MagicMock()
    migration_context.get_current_revision.return_value = (
        "unbekannte_revision_123"
    )

    monkeypatch.setattr(
        module,
        "create_engine",
        lambda url: engine,
    )
    monkeypatch.setattr(
        module,
        "inspect",
        lambda value: inspector,
    )
    monkeypatch.setattr(
        module.MigrationContext,
        "configure",
        lambda value: migration_context,
    )

    result = DatabaseMigrationService(
        application_config=config
    ).inspect_postgresql_schema()

    assert result.status == PostgreSQLSchemaStatus.UNKNOWN
    assert result.current_revision == "unbekannte_revision_123"
    assert result.head_revision == HEAD_REVISION

    engine.dispose.assert_called_once()
