"""Tests für den PySide6-Datenbankkonfigurationsdialog."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from PySide6.QtWidgets import QApplication, QDialog

from openbilanz.core.config import ApplicationConfig
from openbilanz.ui_qt.database_configuration_dialog import (
    DatabaseConfigurationDialog,
)


@pytest.fixture
def app():
    application = QApplication.instance()
    if application is None:
        application = QApplication([])
    return application


@pytest.fixture
def config(tmp_path: Path) -> ApplicationConfig:
    return ApplicationConfig(
        data_dir=tmp_path,
        database_file=tmp_path / "simpleob.db",
        taxonomy_dir=tmp_path / "taxonomy",
        config_file=tmp_path / "config.toml",
    )


def test_sqlite_is_selected_by_default(
    app,
    config: ApplicationConfig,
) -> None:
    dialog = DatabaseConfigurationDialog(config=config)

    assert dialog._backend_box.currentData() == "sqlite"
    assert not dialog._host_edit.isEnabled()
    assert dialog._selected_url() is None


def test_postgresql_url_is_constructed(
    app,
    config: ApplicationConfig,
) -> None:
    dialog = DatabaseConfigurationDialog(config=config)

    dialog._backend_box.setCurrentIndex(1)
    dialog._host_edit.setText("localhost")
    dialog._port_edit.setText("5432")
    dialog._user_edit.setText("testuser")
    dialog._database_edit.setText("testdatabase")

    assert dialog._selected_url() == (
        "postgresql+psycopg://"
        "testuser@localhost:5432/testdatabase"
    )


def test_invalid_postgresql_port_is_rejected(
    app,
    config: ApplicationConfig,
) -> None:
    dialog = DatabaseConfigurationDialog(config=config)

    dialog._backend_box.setCurrentIndex(1)
    dialog._host_edit.setText("localhost")
    dialog._port_edit.setText("invalid")
    dialog._user_edit.setText("testuser")
    dialog._database_edit.setText("testdatabase")

    with pytest.raises(ValueError, match="Port"):
        dialog._selected_url()


def test_postgresql_connection_is_checked(
    app,
    config: ApplicationConfig,
) -> None:
    dialog = DatabaseConfigurationDialog(config=config)

    dialog._backend_box.setCurrentIndex(1)
    dialog._host_edit.setText("localhost")
    dialog._port_edit.setText("5432")
    dialog._user_edit.setText("testuser")
    dialog._database_edit.setText("testdatabase")

    with patch(
        "openbilanz.ui_qt.database_configuration_dialog."
        "DatabaseMigrationService"
    ) as migration_service:
        database_url = dialog._check_connection()

    assert database_url == (
        "postgresql+psycopg://"
        "testuser@localhost:5432/testdatabase"
    )

    migration_service.return_value.check_ready_for_start.assert_called_once()


def test_accept_sqlite_configuration(
    app,
    config: ApplicationConfig,
) -> None:
    dialog = DatabaseConfigurationDialog(config=config)

    dialog._accept_configuration()

    assert dialog.result() == QDialog.DialogCode.Accepted
    assert dialog.selected_database_url is None
