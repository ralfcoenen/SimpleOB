"""Tests für die Datenbankauswahl beim Programmstart."""

from dataclasses import replace
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QDialog, QMessageBox

from simpleob import qt_main
from simpleob.core.config import ApplicationConfig
from simpleob.database.connection_credentials import (
    PostgreSQLCredentials,
)


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
    received_credentials = []

    def create_migration_service(
        *,
        application_config,
        credentials=None,
    ):
        assert application_config is config
        received_credentials.append(credentials)
        return migration

    monkeypatch.setattr(
        qt_main,
        "DatabaseMigrationService",
        create_migration_service,
    )

    def unexpected_password_request(_config):
        raise AssertionError(
            "SQLite darf keine Passwortabfrage auslösen."
        )

    monkeypatch.setattr(
        qt_main,
        "_request_postgresql_credentials",
        unexpected_password_request,
    )

    # Die Hilfsfunktion wird auch bei SQLite aufgerufen,
    # muss dort aber ohne Dialog None zurückgeben.
    monkeypatch.setattr(
        qt_main,
        "_request_postgresql_credentials",
        lambda candidate: None,
    )

    result = qt_main._prepare_database_connection(config)

    assert result == (config, None)
    assert received_credentials == [None]
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

    credentials = PostgreSQLCredentials(
        password="test-secret"
    )
    migration = MagicMock()
    received_credentials = []

    monkeypatch.setattr(
        qt_main,
        "_request_postgresql_credentials",
        lambda candidate: credentials,
    )

    def create_migration_service(
        *,
        application_config,
        credentials=None,
    ):
        assert application_config is config
        received_credentials.append(credentials)
        return migration

    monkeypatch.setattr(
        qt_main,
        "DatabaseMigrationService",
        create_migration_service,
    )

    result = qt_main._prepare_database_connection(config)

    assert result == (config, credentials)
    assert received_credentials == [credentials]
    migration.check_ready_for_start.assert_called_once()
    migration.upgrade_to_head.assert_not_called()


def test_postgresql_password_dialog_cancelled(
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
        "_request_postgresql_credentials",
        lambda candidate: None,
    )
    monkeypatch.setattr(
        qt_main,
        "DatabaseMigrationService",
        lambda **kwargs: migration,
    )

    result = qt_main._prepare_database_connection(config)

    assert result is None
    migration.check_ready_for_start.assert_not_called()
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
        lambda **kwargs: migration,
    )
    monkeypatch.setattr(
        qt_main,
        "_request_postgresql_credentials",
        lambda candidate: None,
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

    credentials = PostgreSQLCredentials(
        password="test-secret"
    )

    checked_urls = []
    received_credentials = []
    saved_urls = []

    class FakeMigrationService:
        def __init__(
            self,
            *,
            application_config,
            credentials=None,
        ):
            self.config = application_config
            self.credentials = credentials

        def upgrade_to_head(self):
            raise RuntimeError("SQLite nicht erreichbar")

        def check_ready_for_start(self):
            checked_urls.append(
                self.config.database_url
            )
            received_credentials.append(
                self.credentials
            )

    class FakeDialog:
        selected_database_url = postgres_url
        checked_credentials = credentials

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
        qt_main,
        "_request_postgresql_credentials",
        lambda candidate: None,
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

    result = qt_main._prepare_database_connection(config)

    assert checked_urls == [postgres_url]
    assert received_credentials == [credentials]
    assert saved_urls == [postgres_url]

    assert result is not None
    selected_config, selected_credentials = result

    assert selected_config.database_url == postgres_url
    assert selected_credentials is credentials


def test_postgresql_wrong_password_can_be_retried(
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

    wrong_credentials = PostgreSQLCredentials(
        password="wrong-password"
    )
    correct_credentials = PostgreSQLCredentials(
        password="correct-password"
    )

    requested_credentials = iter(
        (wrong_credentials, correct_credentials)
    )
    received_credentials = []
    questions = []

    monkeypatch.setattr(
        qt_main,
        "_request_postgresql_credentials",
        lambda candidate: next(requested_credentials),
    )

    class InvalidPasswordError(Exception):
        sqlstate = "28P01"

    class FakeMigrationService:
        def __init__(
            self,
            *,
            application_config,
            credentials=None,
        ):
            self.credentials = credentials

        def check_ready_for_start(self):
            received_credentials.append(
                self.credentials
            )

            if self.credentials is wrong_credentials:
                raise InvalidPasswordError(
                    "password authentication failed"
                )

        def upgrade_to_head(self):
            raise AssertionError(
                "PostgreSQL darf keine automatische "
                "Migration ausführen."
            )

    def answer_question(
        parent,
        title,
        message,
        buttons,
        default_button,
    ):
        questions.append((title, message))
        return QMessageBox.StandardButton.Yes

    monkeypatch.setattr(
        qt_main,
        "DatabaseMigrationService",
        FakeMigrationService,
    )
    monkeypatch.setattr(
        qt_main.QMessageBox,
        "question",
        answer_question,
    )

    result = qt_main._prepare_database_connection(
        config
    )

    assert result == (config, correct_credentials)
    assert received_credentials == [
        wrong_credentials,
        correct_credentials,
    ]

    assert len(questions) == 1
    assert questions[0][0] == (
        "SimpleOB – PostgreSQL-Anmeldung"
    )
    assert "Passwort erneut eingeben" in questions[0][1]


def test_postgresql_password_error_without_sqlstate_is_recognized():
    """Erkennt den real beobachteten psycopg-Verbindungsfehler."""

    from sqlalchemy.exc import OperationalError

    class FakePsycopgError(Exception):
        sqlstate = None

    original = FakePsycopgError(
        'connection failed: connection to server at '
        '"127.0.0.1", port 5432 failed: '
        'FATAL: password authentication failed '
        'for user "simpleob_auth_test"'
    )

    error = OperationalError(
        statement=None,
        params=None,
        orig=original,
    )

    assert qt_main._is_postgresql_authentication_error(
        error
    ) is True
