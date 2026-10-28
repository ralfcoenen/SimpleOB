"""Tests des zusätzlichen Verwaltungsdialogs ohne Änderungen am Login."""

from unittest.mock import patch

import pytest
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from simpleob.core.config import ApplicationConfig
from simpleob.ui_qt.database_configuration_dialog import DatabaseConfigurationDialog
from simpleob.ui_qt.postgresql_user_dialog import PostgreSQLUserDialog


@pytest.fixture
def config(tmp_path):
    app = QApplication.instance() or QApplication([])
    yield ApplicationConfig(
        data_dir=tmp_path,
        database_file=tmp_path / "test.db",
        taxonomy_dir=tmp_path,
        config_file=tmp_path / "config.toml",
        database_url_override="postgresql+psycopg://old_user@localhost:5432/books",
    )
    assert app is not None


@pytest.mark.parametrize("new_database", [True, False])
def test_success_uses_separate_service(config, new_database):
    dialog = PostgreSQLUserDialog(config=config, new_database=new_database)
    dialog._username.setText("new_user")
    dialog._password.setText("secret")
    dialog._repeat.setText("secret")
    dialog._admin_password.setText("admin")
    with (
        patch(
            "simpleob.ui_qt.postgresql_user_dialog.QMessageBox.question",
            return_value=QMessageBox.StandardButton.Yes,
        ),
        patch("simpleob.ui_qt.postgresql_user_dialog.QMessageBox.information"),
        patch("simpleob.ui_qt.postgresql_user_dialog.PostgreSQLUserService") as service,
    ):
        dialog._create_user()
        call = service.return_value.create_user.call_args.kwargs
        assert call["new_database"] is new_database
        assert (
            call["application_config"].database_url
            == "postgresql+psycopg://new_user@localhost:5432/books"
        )
        assert call["application_credentials"].password == "secret"
    assert dialog.result() == QDialog.DialogCode.Accepted
    assert not dialog._admin_password.text()
    assert not dialog._password.text()
    assert "old_user" in config.database_url


def test_password_mismatch_does_not_call_service(config):
    dialog = PostgreSQLUserDialog(config=config, new_database=False)
    dialog._password.setText("secret")
    with (
        patch("simpleob.ui_qt.postgresql_user_dialog.QMessageBox.warning"),
        patch("simpleob.ui_qt.postgresql_user_dialog.PostgreSQLUserService") as service,
    ):
        dialog._create_user()
        service.assert_not_called()


def test_cancel_confirmation_does_not_call_service(config):
    dialog = PostgreSQLUserDialog(config=config, new_database=False)
    dialog._password.setText("secret")
    dialog._repeat.setText("secret")
    with (
        patch(
            "simpleob.ui_qt.postgresql_user_dialog.QMessageBox.question",
            return_value=QMessageBox.StandardButton.No,
        ),
        patch("simpleob.ui_qt.postgresql_user_dialog.PostgreSQLUserService") as service,
    ):
        dialog._create_user()
        service.assert_not_called()


def test_management_does_not_change_checked_login(config):
    dialog = DatabaseConfigurationDialog(config=config)
    dialog._checked_database_url = config.database_url
    with patch(
        "simpleob.ui_qt.postgresql_user_dialog.PostgreSQLUserDialog"
    ) as management:
        dialog._open_user_management(False)
        management.return_value.exec.assert_called_once()
    assert dialog._checked_database_url == config.database_url
    assert dialog._user_edit.text() == "old_user"
    dialog._backend_box.setCurrentIndex(0)
    assert all(not button.isEnabled() for button in dialog._user_management_buttons)


def test_reject_clears_passwords(config):
    dialog = PostgreSQLUserDialog(config=config, new_database=False)
    dialog._password.setText("secret")
    dialog._repeat.setText("secret")
    dialog._admin_password.setText("admin")
    dialog.reject()
    assert not dialog._password.text()
    assert not dialog._repeat.text()
    assert not dialog._admin_password.text()
