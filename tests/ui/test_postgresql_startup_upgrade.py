"""Benutzerfreigabe und kurzlebige Zugänge beim Startupgrade."""

from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from PySide6.QtWidgets import QDialog, QMessageBox

from simpleob.core.config import ApplicationConfig
from simpleob.database.connection_credentials import PostgreSQLCredentials
from simpleob.database.migration_service import (
    PostgreSQLSchemaInspection,
    PostgreSQLSchemaStatus,
)
from simpleob.ui_qt import postgresql_startup_upgrade as ui


@pytest.fixture
def setup(monkeypatch, tmp_path):
    config = ApplicationConfig(
        data_dir=tmp_path,
        database_file=tmp_path / "unused.db",
        taxonomy_dir=tmp_path,
        config_file=tmp_path / "config.toml",
        database_url_override="postgresql+psycopg://operator@localhost/books",
    )
    buttons = []
    state = SimpleNamespace(choice="upgrade", warnings=[])

    class Box:
        ButtonRole = QMessageBox.ButtonRole
        StandardButton = QMessageBox.StandardButton

        def setWindowTitle(self, value):
            pass

        def setText(self, value):
            state.text = value

        def setInformativeText(self, value):
            pass

        def addButton(self, label, *args):
            button = object()
            buttons.append((str(label), button))
            return button

        def exec(self):
            pass

        def clickedButton(self):
            prefix = {
                "upgrade": "Administratives",
                "change": "Datenbankverbindung",
            }.get(state.choice)
            return next(
                (
                    button
                    for label, button in buttons
                    if prefix and label.startswith(prefix)
                ),
                None,
            )

        @staticmethod
        def warning(*args):
            state.warnings.append(args[-1])

    monkeypatch.setattr(ui, "QMessageBox", Box)
    answers = iter([("books", True), ("migrator", True), ("admin", True)])
    monkeypatch.setattr(ui.QInputDialog, "getText", lambda *args: next(answers))
    password_dialog = Mock()
    password_dialog.exec.return_value = QDialog.DialogCode.Accepted
    password_dialog.password = "temporary-secret"
    monkeypatch.setattr(
        ui, "PostgreSQLPasswordDialog", lambda **kwargs: password_dialog
    )
    monkeypatch.setattr(
        ui.QFileDialog,
        "getSaveFileName",
        lambda *args: (str(tmp_path / "backup.dump"), ""),
    )
    admin = Mock()
    monkeypatch.setattr(ui, "PostgreSQLAdministrationService", admin)
    inspection = PostgreSQLSchemaInspection(
        PostgreSQLSchemaStatus.OUTDATED, "old", "head"
    )
    return config, state, buttons, admin, inspection


def test_confirmed_upgrade_uses_runtime_and_temporary_admin_credentials(setup):
    config, state, _, admin, inspection = setup
    runtime = PostgreSQLCredentials("runtime-secret")
    assert ui.offer_postgresql_upgrade(config, runtime, inspection) == "ready"
    assert "books" in state.text and "old" in state.text and "head" in state.text
    assert admin.call_args.kwargs["operating_credentials"] is runtime
    assert admin.call_args.kwargs["migration_username"] == "migrator"
    approval = admin.return_value.execute_migration.call_args.kwargs["approval"]
    assert approval.confirmed_database_name == "books"
    assert approval.migration_confirmed and approval.maintenance_confirmed
    assert not config.config_file.exists()


@pytest.mark.parametrize("choice", ["cancel", "change"])
def test_cancel_or_change_does_not_start_upgrade(setup, choice):
    config, state, _, admin, inspection = setup
    state.choice = choice
    assert (
        ui.offer_postgresql_upgrade(config, PostgreSQLCredentials("pw"), inspection)
        == choice
    )
    admin.assert_not_called()


def test_unknown_revision_has_no_upgrade_button(setup):
    config, _, buttons, admin, inspection = setup
    inspection = replace(inspection, status=PostgreSQLSchemaStatus.UNKNOWN)
    assert (
        ui.offer_postgresql_upgrade(config, PostgreSQLCredentials("pw"), inspection)
        == "cancel"
    )
    assert not any(label.startswith("Administratives") for label, _ in buttons)
    admin.assert_not_called()


def test_exact_database_confirmation_is_required(setup, monkeypatch):
    config, _, _, admin, inspection = setup
    monkeypatch.setattr(ui.QInputDialog, "getText", lambda *args: ("wrong", True))
    assert (
        ui.offer_postgresql_upgrade(config, PostgreSQLCredentials("pw"), inspection)
        == "change"
    )
    admin.assert_not_called()


def test_upgrade_failure_does_not_expose_credentials(setup):
    config, state, _, admin, inspection = setup
    admin.return_value.execute_migration.side_effect = RuntimeError("temporary-secret")
    assert (
        ui.offer_postgresql_upgrade(config, PostgreSQLCredentials("pw"), inspection)
        == "change"
    )
    assert state.warnings and "temporary-secret" not in state.warnings[-1]
