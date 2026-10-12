"""Tests für die Datenbankauswahl beim Programmstart."""

from dataclasses import replace
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QDialog, QMessageBox

from openbilanz.core.config import ApplicationConfig
from openbilanz import qt_main


@pytest.fixture
def config(tmp_path: Path) -> ApplicationConfig:
    return ApplicationConfig(
        data_dir=tmp_path,
        database_file=tmp_path / "simpleob.db",
        taxonomy_dir=tmp_path / "taxonomy",
        config_file=tmp_path / "config.toml",
    )


def test_sqlite_start_uses_migration(
    monkeypatch,
    config,
):
    migration = MagicMock()

    monkeypatch.setattr(
        qt_main,
        "DatabaseMigrationService",
        lambda application_config: migration,
    )

    result = qt_main._prepare_database_connection(
        config
    )

    assert result == config
    migration.upgrade_to_head.assert_called_once()
    migration.check_ready_for_start.assert_not_called()


def test_postgresql_start_uses_read_only_check(
    monkeypatch,
    config,
):
    config = replace(
        config,
        database_url_override=(
            "postgresql+psycopg://"
            "testuser@localhost/testdb"
        ),
    )

    migration = MagicMock()

    monkeypatch.setattr(
        qt_main,
        "DatabaseMigrationService",
        lambda application_config: migration,
    )

    result = qt_main._prepare_database_connection(
        config
    )

    assert result == config
    migration.check_ready_for_start.assert_called_once()
    migration.upgrade_to_head.assert_not_called()


def test_failed_connection_can_be_cancelled(
    monkeypatch,
    config,
):
    migration = MagicMock()
    migration.upgrade_to_head.side_effect = RuntimeError(
        "Verbindung fehlgeschlagen"
    )

    monkeypatch.setattr(
        qt_main,
        "DatabaseMigrationService",
        lambda application_config: migration,
    )

    monkeypatch.setattr(
        qt_main.QMessageBox,
        "question",
        lambda *args, **kwargs: (
            QMessageBox.StandardButton.No
        ),
    )

    assert (
        qt_main._prepare_database_connection(config)
        is None
    )


def test_corrected_connection_is_saved_after_check(
    monkeypatch,
    config,
):
    postgres_url = (
        "postgresql+psycopg://"
        "testuser@localhost/testdb"
    )

    checked_urls = []
    saved_urls = []

    class FakeMigrationService:
        def __init__(self, *, application_config):
            self.config = application_config

        def upgrade_to_head(self):
            raise RuntimeError("SQLite nicht erreichbar")

        def check_ready_for_start(self):
            checked_urls.append(
                self.config.database_url
            )

    class FakeDialog:
        selected_database_url = postgres_url

        def __init__(self, *, config):
            pass

        def exec(self):
            return QDialog.DialogCode.Accepted

    monkeypatch.setattr(
        qt_main,
        "DatabaseMigrationService",
        FakeMigrationService,
    )
    monkeypatch.setattr(
        qt_main,
        "DatabaseConfigurationDialog",
        FakeDialog,
    )
    monkeypatch.setattr(
        qt_main.QMessageBox,
        "question",
        lambda *args, **kwargs: (
            QMessageBox.StandardButton.Yes
        ),
    )
    monkeypatch.setattr(
        qt_main,
        "save_database_configuration",
        lambda config, url: saved_urls.append(url),
    )

    result = qt_main._prepare_database_connection(
        config
    )

    assert checked_urls == [postgres_url]
    assert saved_urls == [postgres_url]
    assert result.database_url == postgres_url
