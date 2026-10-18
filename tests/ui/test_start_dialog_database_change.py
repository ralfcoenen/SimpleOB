"""Tests für den Datenbankwechsel im PySide6-Startdialog."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QApplication, QDialog

from simpleob.core.config import ApplicationConfig
from simpleob.ui_qt import start_dialog as module
from simpleob.ui_qt.start_dialog import StartDialog


POSTGRES_URL = (
    "postgresql+psycopg://"
    "testuser@localhost:5432/testdatabase"
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


@pytest.fixture
def dialog(app, config):
    repository = MagicMock()
    repository.list_companies.return_value = ()

    return StartDialog(
        repository=repository,
        config=config,
    )


def _mock_configuration_dialog(
    monkeypatch,
    *,
    result,
    selected_url=None,
):
    class FakeConfigurationDialog:
        selected_database_url = selected_url

        def __init__(self, *, config):
            self.config = config

        def exec(self):
            return result

    monkeypatch.setattr(
        module,
        "DatabaseConfigurationDialog",
        FakeConfigurationDialog,
    )


def test_cancelled_selection_does_not_save(
    monkeypatch,
    dialog,
):
    save = MagicMock()
    reject = MagicMock()

    monkeypatch.setattr(
        module,
        "save_database_configuration",
        save,
    )
    monkeypatch.setattr(dialog, "reject", reject)

    _mock_configuration_dialog(
        monkeypatch,
        result=QDialog.DialogCode.Rejected,
    )

    dialog._change_database()

    save.assert_not_called()
    reject.assert_not_called()


def test_unchanged_database_does_not_save(
    monkeypatch,
    dialog,
):
    save = MagicMock()
    reject = MagicMock()

    monkeypatch.setattr(
        module,
        "save_database_configuration",
        save,
    )
    monkeypatch.setattr(dialog, "reject", reject)

    _mock_configuration_dialog(
        monkeypatch,
        result=QDialog.DialogCode.Accepted,
        selected_url=None,
    )

    dialog._change_database()

    save.assert_not_called()
    reject.assert_not_called()


def test_successful_change_saves_and_closes(
    monkeypatch,
    dialog,
    config,
):
    save = MagicMock()
    reject = MagicMock()
    information = MagicMock()

    monkeypatch.setattr(
        module,
        "save_database_configuration",
        save,
    )
    monkeypatch.setattr(
        module.QMessageBox,
        "information",
        information,
    )
    monkeypatch.setattr(dialog, "reject", reject)

    _mock_configuration_dialog(
        monkeypatch,
        result=QDialog.DialogCode.Accepted,
        selected_url=POSTGRES_URL,
    )

    dialog._change_database()

    save.assert_called_once_with(
        config,
        POSTGRES_URL,
    )
    information.assert_called_once()
    reject.assert_called_once()


def test_save_error_keeps_start_dialog_open(
    monkeypatch,
    dialog,
):
    reject = MagicMock()
    warning = MagicMock()

    def failing_save(config, url):
        raise OSError("Schreibzugriff verweigert")

    monkeypatch.setattr(
        module,
        "save_database_configuration",
        failing_save,
    )
    monkeypatch.setattr(
        module.QMessageBox,
        "warning",
        warning,
    )
    monkeypatch.setattr(dialog, "reject", reject)

    _mock_configuration_dialog(
        monkeypatch,
        result=QDialog.DialogCode.Accepted,
        selected_url=POSTGRES_URL,
    )

    dialog._change_database()

    warning.assert_called_once()
    assert "Schreibzugriff verweigert" in (
        warning.call_args.args[2]
    )
    reject.assert_not_called()
