"""Tests für den PySide6-Datenbankkonfigurationsdialog."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from simpleob.core.config import ApplicationConfig
from simpleob.database.connection_credentials import PostgreSQLCredentials
from simpleob.database.migration_service import PostgreSQLSchemaStatus
from simpleob.database.postgresql_existing_installation_inspector import (
    PostgreSQLOwnershipAssessment,
)
from simpleob.database.postgresql_role_separation_service import (
    PostgreSQLRoleSeparationResult,
)
from simpleob.ui_qt.database_configuration_dialog import (
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


@pytest.mark.parametrize("confirm", [False, True])
def test_recovery_dialog_requires_confirmation_for_sqlite_selection(
    app,
    config: ApplicationConfig,
    monkeypatch,
    confirm: bool,
) -> None:
    config.database_file.write_bytes(b"pre-existing SQLite database")
    dialog = DatabaseConfigurationDialog(
        config=config,
        configuration_notice=(
            "Configuration is missing. SQLite file is already present."
        ),
    )
    assert dialog._configuration_notice_label is not None
    assert "already present" in dialog._configuration_notice_label.text()

    events = []
    monkeypatch.setattr(
        dialog,
        "_check_connection",
        lambda: events.append("check") or None,
    )
    monkeypatch.setattr(
        "simpleob.ui_qt.database_configuration_dialog.QMessageBox.question",
        lambda *args, **kwargs: (
            events.append("confirm")
            or (
                QMessageBox.StandardButton.Yes
                if confirm
                else QMessageBox.StandardButton.No
            )
        ),
    )

    dialog._accept_configuration()

    assert dialog.result() == (
        QDialog.DialogCode.Accepted if confirm else QDialog.DialogCode.Rejected
    )
    assert dialog.selected_database_url is None
    assert events == (["confirm", "check"] if confirm else ["confirm"])
    assert config.database_file.read_bytes() == b"pre-existing SQLite database"
    assert not config.config_file.exists()


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

    credentials = PostgreSQLCredentials("test-password")
    with (
        patch.object(
            dialog, "_request_credentials", return_value=credentials
        ) as request_credentials,
        patch(
            "simpleob.ui_qt.database_configuration_dialog."
            "DatabaseMigrationService"
        ) as migration_service,
    ):
        database_url = dialog._check_connection()

    assert database_url == (
        "postgresql+psycopg://"
        "testuser@localhost:5432/testdatabase"
    )

    migration_service.return_value.check_ready_for_start.assert_called_once()
    request_credentials.assert_called_once_with(database_url)
    assert migration_service.call_args.kwargs["credentials"] is credentials


def test_initialization_uses_separate_runtime_and_migration_roles(
    app, config: ApplicationConfig
) -> None:
    dialog = DatabaseConfigurationDialog(config=config)
    dialog._backend_box.setCurrentIndex(1)
    dialog._host_edit.setText("localhost")
    dialog._port_edit.setText("5432")
    dialog._user_edit.setText("simpleob_app")
    dialog._migration_user_edit.setText("simpleob_migrator")
    dialog._database_edit.setText("simpleob_new")
    credentials = [
        PostgreSQLCredentials("admin-secret"),
        PostgreSQLCredentials("migration-secret"),
        PostgreSQLCredentials("app-secret"),
    ]
    with (
        patch(
            "simpleob.ui_qt.database_configuration_dialog.QMessageBox.question",
            return_value=QMessageBox.StandardButton.Yes,
        ),
        patch(
            "simpleob.ui_qt.database_configuration_dialog.QMessageBox.information"
        ),
        patch.object(dialog, "_request_admin_username", return_value=("dbadmin", True)),
        patch.object(dialog, "_request_credentials", side_effect=credentials),
        patch(
            "simpleob.ui_qt.database_configuration_dialog.PostgreSQLInitializationService"
        ) as initializer,
    ):
        dialog._initialize_postgresql_database()

    call = initializer.return_value.initialize_database.call_args.kwargs
    assert call["admin_username"] == "dbadmin"
    assert call["migration_username"] == "simpleob_migrator"
    assert call["migration_credentials"] is credentials[1]
    assert call["application_credentials"] is credentials[2]
    assert dialog._checked_database_url.endswith("simpleob_app@localhost:5432/simpleob_new")
    assert dialog.checked_credentials is credentials[2]


def test_accept_sqlite_configuration(
    app,
    config: ApplicationConfig,
) -> None:
    dialog = DatabaseConfigurationDialog(config=config)

    dialog._accept_configuration()

    assert dialog.result() == QDialog.DialogCode.Accepted
    assert dialog.selected_database_url is None


def _uniform_assessment():
    return SimpleNamespace(
        ownership_assessment=PostgreSQLOwnershipAssessment.UNIFORM_OWNERSHIP,
        operating_role="legacy_owner",
        migration_role_candidate="legacy_owner",
        database_owner="legacy_owner",
        database_name="books",
        schema_status=PostgreSQLSchemaStatus.CURRENT,
        blockers=(),
    )


def _prepare_role_separation_dialog(dialog):
    dialog._backend_box.setCurrentIndex(1)
    dialog._host_edit.setText("localhost")
    dialog._port_edit.setText("5432")
    dialog._user_edit.setText("legacy_owner")
    dialog._database_edit.setText("books")


def test_role_separation_failure_does_not_change_selected_configuration(
    app, config: ApplicationConfig
):
    config = ApplicationConfig(
        data_dir=config.data_dir,
        database_file=config.database_file,
        taxonomy_dir=config.taxonomy_dir,
        config_file=config.config_file,
        database_url_override=(
            "postgresql+psycopg://legacy_owner@localhost:5432/books"
        ),
    )
    dialog = DatabaseConfigurationDialog(config=config)
    _prepare_role_separation_dialog(dialog)
    credentials = [
        PostgreSQLCredentials("owner-password"),
        PostgreSQLCredentials("operating-password"),
        PostgreSQLCredentials("admin-password"),
    ]
    with (
        patch(
            "simpleob.ui_qt.database_configuration_dialog.PostgreSQLExistingInstallationInspector"
        ) as inspector,
        patch(
            "simpleob.ui_qt.database_configuration_dialog.QInputDialog.getItem",
            return_value=("Neue Betriebsrolle anlegen", True),
        ),
        patch(
            "simpleob.ui_qt.database_configuration_dialog.QInputDialog.getText",
            return_value=("simpleob_app", True),
        ),
        patch(
            "simpleob.ui_qt.database_configuration_dialog.QMessageBox.question",
            return_value=QMessageBox.StandardButton.Yes,
        ),
        patch("simpleob.ui_qt.database_configuration_dialog.QMessageBox.warning"),
        patch.object(dialog, "_request_admin_username", return_value=("db_admin", True)),
        patch.object(dialog, "_request_credentials", side_effect=credentials),
        patch(
            "simpleob.ui_qt.database_configuration_dialog.PostgreSQLRoleSeparationService"
        ) as service,
    ):
        inspector.return_value.inspect.return_value = _uniform_assessment()
        service.return_value.separate_roles.side_effect = RuntimeError("grant failed")

        dialog._separate_postgresql_roles()

    assert dialog._user_edit.text() == "legacy_owner"
    assert dialog._checked_database_url is None
    assert dialog.checked_credentials is None
    assert dialog.selected_database_url is None


def test_role_separation_switches_dialog_only_after_service_verification(
    app, config: ApplicationConfig
):
    config = ApplicationConfig(
        data_dir=config.data_dir,
        database_file=config.database_file,
        taxonomy_dir=config.taxonomy_dir,
        config_file=config.config_file,
        database_url_override=(
            "postgresql+psycopg://legacy_owner@localhost:5432/books"
        ),
    )
    dialog = DatabaseConfigurationDialog(config=config)
    _prepare_role_separation_dialog(dialog)
    credentials = [
        PostgreSQLCredentials("owner-password"),
        PostgreSQLCredentials("operating-password"),
        PostgreSQLCredentials("admin-password"),
    ]
    result_url = "postgresql+psycopg://simpleob_app@localhost:5432/books"
    with (
        patch(
            "simpleob.ui_qt.database_configuration_dialog.PostgreSQLExistingInstallationInspector"
        ) as inspector,
        patch(
            "simpleob.ui_qt.database_configuration_dialog.QInputDialog.getItem",
            return_value=("Neue Betriebsrolle anlegen", True),
        ),
        patch(
            "simpleob.ui_qt.database_configuration_dialog.QInputDialog.getText",
            return_value=("simpleob_app", True),
        ),
        patch(
            "simpleob.ui_qt.database_configuration_dialog.QMessageBox.question",
            return_value=QMessageBox.StandardButton.Yes,
        ),
        patch("simpleob.ui_qt.database_configuration_dialog.QMessageBox.information"),
        patch("simpleob.ui_qt.database_configuration_dialog.QMessageBox.warning"),
        patch.object(dialog, "_request_admin_username", return_value=("db_admin", True)),
        patch.object(dialog, "_request_credentials", side_effect=credentials),
        patch(
            "simpleob.ui_qt.database_configuration_dialog.PostgreSQLRoleSeparationService"
        ) as service,
    ):
        inspector.return_value.inspect.return_value = _uniform_assessment()
        service.return_value.separate_roles.return_value = PostgreSQLRoleSeparationResult(
            database_name="books",
            migration_role="legacy_owner",
            operating_role="simpleob_app",
            database_url=result_url,
            operating_role_created=True,
            changed=True,
        )

        dialog._separate_postgresql_roles()

    assert dialog._user_edit.text() == "simpleob_app"
    assert dialog._checked_database_url == result_url
    assert dialog.checked_credentials is credentials[1]


@pytest.mark.parametrize("status", [PostgreSQLSchemaStatus.OUTDATED, PostgreSQLSchemaStatus.UNKNOWN])
def test_old_connection_can_be_selected_only_for_known_revision(app, config, status):
    dialog = DatabaseConfigurationDialog(config=config)
    url = "postgresql+psycopg://operator@localhost/books"
    credentials = PostgreSQLCredentials("runtime-secret")
    with (
        patch.object(dialog, "_selected_url", return_value=url),
        patch.object(dialog, "_request_credentials", return_value=credentials),
        patch("simpleob.ui_qt.database_configuration_dialog.DatabaseMigrationService") as service,
    ):
        service.return_value.check_ready_for_start.side_effect = RuntimeError("outdated")
        service.return_value.inspect_postgresql_schema.return_value = SimpleNamespace(status=status)
        if status == PostgreSQLSchemaStatus.OUTDATED:
            assert dialog._check_connection() == url
            assert dialog.checked_credentials is credentials
        else:
            with pytest.raises(RuntimeError):
                dialog._check_connection()
            assert dialog.checked_credentials is None
        service.return_value.upgrade_to_head.assert_not_called()
