"""Tests für die Datenbankauswahl beim Programmstart."""

from dataclasses import replace
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QDialog, QMessageBox

from simpleob import qt_main
from simpleob.core.config import (
    ApplicationConfig,
    ConfigurationSyntaxError,
    InvalidDatabaseConfigurationError,
    load_config,
)
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


@pytest.mark.parametrize("sqlite_exists", [False, True])
def test_missing_configuration_requires_database_choice_and_reports_sqlite(
    monkeypatch,
    config,
    sqlite_exists,
):
    if sqlite_exists:
        config.database_file.write_bytes(b"existing SQLite bytes")
    monkeypatch.setattr(qt_main, "_load_application_config", lambda: config)

    loaded = qt_main._load_startup_configuration()

    assert loaded is not None
    selected_config, notice = loaded
    assert selected_config is config
    assert notice is not None
    assert str(config.database_file) in notice
    assert ("bereits vorhanden" in notice) is sqlite_exists
    assert config.config_file.exists() is False
    assert config.database_file.exists() is sqlite_exists
    if sqlite_exists:
        assert config.database_file.read_bytes() == b"existing SQLite bytes"


def test_configuration_load_error_is_reported_before_database_access(
    monkeypatch,
    config,
):
    error = ConfigurationSyntaxError(config.config_file, "TOML-Syntaxfehler")
    monkeypatch.setattr(
        qt_main,
        "_load_application_config",
        lambda: (_ for _ in ()).throw(error),
    )
    critical = MagicMock()
    monkeypatch.setattr(qt_main.QMessageBox, "critical", critical)

    assert qt_main._load_startup_configuration() is None

    critical.assert_called_once()
    assert str(config.config_file) in critical.call_args.args[2]
    assert "ändert die Datei nicht" in critical.call_args.args[2]


def test_cancelling_missing_configuration_does_not_check_or_save_database(
    monkeypatch,
    config,
):
    dialog = MagicMock()
    dialog.exec.return_value = QDialog.DialogCode.Rejected
    monkeypatch.setattr(
        qt_main,
        "DatabaseConfigurationDialog",
        lambda **kwargs: dialog,
    )
    migration = MagicMock()
    monkeypatch.setattr(
        qt_main,
        "DatabaseMigrationService",
        lambda **kwargs: migration,
    )
    save = MagicMock()
    monkeypatch.setattr(qt_main, "save_database_configuration", save)
    monkeypatch.setattr(
        qt_main,
        "_request_postgresql_credentials",
        lambda candidate: pytest.fail("No connection before a choice"),
    )

    result = qt_main._prepare_database_connection(
        config,
        configuration_notice="Config missing",
    )

    assert result is None
    migration.assert_not_called()
    save.assert_not_called()
    assert not config.config_file.exists()
    assert not config.database_file.exists()


def test_invalid_database_url_recovery_preserves_other_settings(
    monkeypatch,
    tmp_path: Path,
):
    config_file = tmp_path / "config.toml"
    database_file = tmp_path / "existing.sqlite"
    taxonomy_dir = tmp_path / "taxonomies"
    data_dir = tmp_path / "application-data"
    config_file.write_text(
        "[application]\n"
        f'data_dir = "{data_dir}"\n\n'
        "[database]\n"
        f'file = "{database_file}"\n'
        'url = "mysql://localhost/wrong"\n\n'
        "[taxonomy]\n"
        f'root = "{taxonomy_dir}"\n',
        encoding="utf-8",
    )
    with pytest.raises(InvalidDatabaseConfigurationError) as exc_info:
        load_config(config_file)
    recovery_config = exc_info.value.recovery_config

    selected_url = "postgresql+psycopg://operator@localhost:5432/books"
    credentials = PostgreSQLCredentials("temporary-password")

    class RecoveryDialog:
        def __init__(self, *, config, configuration_notice):
            assert config is recovery_config
            assert "ungültig" in configuration_notice
            self.selected_database_url = selected_url
            self.checked_credentials = credentials
            self.candidate_prepared = True

        def exec(self):
            return QDialog.DialogCode.Accepted

    migration = MagicMock()
    monkeypatch.setattr(
        qt_main,
        "DatabaseConfigurationDialog",
        RecoveryDialog,
    )
    monkeypatch.setattr(
        qt_main,
        "DatabaseMigrationService",
        lambda **kwargs: migration,
    )
    monkeypatch.setattr(
        qt_main,
        "_request_postgresql_credentials",
        lambda candidate: pytest.fail("Recovery dialog supplies checked access"),
    )

    result = qt_main._prepare_database_connection(
        recovery_config,
        configuration_notice="Datenbankeintrag ungültig",
    )

    assert result == (
        recovery_config.__class__(
            data_dir=data_dir,
            database_file=database_file,
            taxonomy_dir=taxonomy_dir,
            config_file=config_file,
            database_url_override=selected_url,
            eric_lib_dir=recovery_config.eric_lib_dir,
            eric_data_supplier=recovery_config.eric_data_supplier,
            eric_certificate_path=recovery_config.eric_certificate_path,
        ),
        credentials,
    )
    reloaded = load_config(config_file)
    assert reloaded.database_url == selected_url
    assert reloaded.data_dir == data_dir
    assert reloaded.database_file == database_file
    assert reloaded.taxonomy_dir == taxonomy_dir


def test_cancelling_invalid_database_recovery_preserves_configuration(
    monkeypatch,
    tmp_path: Path,
):
    config_file = tmp_path / "config.toml"
    original = (
        '[application]\ndata_dir = "/tmp/preserved-data"\n'
        '\n[database]\nfile = "/tmp/preserved.db"\n'
        'url = "mysql://localhost/test"\n'
    )
    config_file.write_text(original, encoding="utf-8")
    with pytest.raises(InvalidDatabaseConfigurationError) as exc_info:
        load_config(config_file)
    recovery_config = exc_info.value.recovery_config

    class CancelRecoveryDialog:
        def __init__(self, *, config, configuration_notice):
            assert config is recovery_config
            assert "ungültig" in configuration_notice

        def exec(self):
            return QDialog.DialogCode.Rejected

    migration = MagicMock()
    save = MagicMock()
    monkeypatch.setattr(
        qt_main,
        "DatabaseConfigurationDialog",
        CancelRecoveryDialog,
    )
    monkeypatch.setattr(
        qt_main,
        "DatabaseMigrationService",
        lambda **kwargs: migration,
    )
    monkeypatch.setattr(qt_main, "save_database_configuration", save)

    result = qt_main._prepare_database_connection(
        recovery_config,
        configuration_notice="Datenbankeintrag ungültig",
    )

    assert result is None
    migration.assert_not_called()
    save.assert_not_called()
    assert config_file.read_text(encoding="utf-8") == original


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
    received_credentials = []

    monkeypatch.setattr(
        qt_main,
        "_request_postgresql_credentials",
        lambda candidate: credentials,
    )

    def prepare_candidate(application_config, candidate_credentials):
        assert application_config is config
        assert candidate_credentials is credentials
        received_credentials.append(credentials)
        return "ready"

    monkeypatch.setattr(
        qt_main,
        "prepare_postgresql_candidate",
        prepare_candidate,
    )

    result = qt_main._prepare_database_connection(config)

    assert result == (config, credentials)
    assert received_credentials == [credentials]


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

    monkeypatch.setattr(
        qt_main,
        "_request_postgresql_credentials",
        lambda candidate: None,
    )

    result = qt_main._prepare_database_connection(config)

    assert result is None


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
        candidate_prepared = True

        def __init__(self, *, config, configuration_notice=None):
            pass

        def exec(self):
            return QDialog.DialogCode.Accepted

    monkeypatch.setattr(qt_main, "DatabaseMigrationService", FakeMigrationService)
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

    assert checked_urls == []
    assert received_credentials == []
    assert saved_urls == [postgres_url]

    assert result is not None
    selected_config, selected_credentials = result

    assert selected_config.database_url == postgres_url
    assert selected_credentials is credentials


def test_prepared_postgresql_candidate_is_saved_then_rechecked_on_next_start(
    monkeypatch, config
):
    postgres_url = "postgresql+psycopg://operator@localhost/books"
    credentials = PostgreSQLCredentials("runtime-only")

    class PreparedDialog:
        selected_database_url = postgres_url
        checked_credentials = credentials
        candidate_prepared = True

        def __init__(self, **_kwargs):
            pass

        def exec(self):
            return QDialog.DialogCode.Accepted

    monkeypatch.setattr(qt_main, "DatabaseConfigurationDialog", PreparedDialog)
    first = qt_main._prepare_database_connection(
        config,
        configuration_notice="Datenbankauswahl erforderlich",
    )
    assert first is not None
    selected_config, selected_credentials = first
    assert selected_config.database_url == postgres_url
    assert selected_credentials is credentials

    reloaded = load_config(config.config_file, defaults=config)
    assert reloaded.database_url == postgres_url
    second_start_checks = []
    monkeypatch.setattr(
        qt_main,
        "_request_postgresql_credentials",
        lambda _candidate: credentials,
    )
    monkeypatch.setattr(
        qt_main,
        "prepare_postgresql_candidate",
        lambda candidate, access: second_start_checks.append(
            (candidate.database_url, access)
        )
        or "ready",
    )

    second = qt_main._prepare_database_connection(reloaded)

    assert second == (reloaded, credentials)
    assert second_start_checks == [(postgres_url, credentials)]
    assert "runtime-only" not in config.config_file.read_text(encoding="utf-8")


def test_save_failure_after_candidate_preparation_preserves_old_database(
    monkeypatch, config
):
    postgres_url = "postgresql+psycopg://operator@localhost/books"
    credentials = PostgreSQLCredentials("runtime-only")
    original = f'[database]\nfile = "{config.database_file.as_posix()}"\n'
    config.config_file.write_text(original, encoding="utf-8")

    class PreparedDialog:
        selected_database_url = postgres_url
        checked_credentials = credentials
        candidate_prepared = True

        def __init__(self, **_kwargs):
            pass

        def exec(self):
            return QDialog.DialogCode.Accepted

    monkeypatch.setattr(qt_main, "DatabaseConfigurationDialog", PreparedDialog)
    monkeypatch.setattr(qt_main.QMessageBox, "warning", lambda *_args: None)
    from simpleob.core import config as config_module

    monkeypatch.setattr(
        config_module.os,
        "replace",
        lambda *_: (_ for _ in ()).throw(OSError("replace failed")),
    )

    result = qt_main._prepare_database_connection(
        config, configuration_notice="Datenbankauswahl erforderlich"
    )

    assert result is None
    assert config.config_file.read_text(encoding="utf-8") == original
    assert "postgresql" not in config.config_file.read_text(encoding="utf-8")
    assert "runtime-only" not in config.config_file.read_text(encoding="utf-8")
    reloaded = load_config(config.config_file, defaults=config)
    assert reloaded.database_url.startswith("sqlite:")


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

    def prepare_candidate(candidate, credentials):
        received_credentials.append(credentials)
        if credentials is wrong_credentials:
            raise InvalidPasswordError("password authentication failed")
        return "ready"

    def answer_question(
        parent,
        title,
        message,
        buttons,
        default_button,
    ):
        questions.append((title, message))
        return QMessageBox.StandardButton.Yes

    monkeypatch.setattr(qt_main, "prepare_postgresql_candidate", prepare_candidate)
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


@pytest.mark.parametrize("outcome", ["ready", "cancel", "change", "failed_recheck"])
def test_outdated_postgresql_requires_upgrade_and_runtime_recheck(monkeypatch, config, outcome):
    config = replace(config, database_url_override="postgresql+psycopg://operator@localhost/books")
    runtime = PostgreSQLCredentials("runtime-secret")
    action = "ready" if outcome in {"ready", "failed_recheck"} else outcome
    if outcome == "failed_recheck":
        action = "change"
    monkeypatch.setattr(qt_main, "prepare_postgresql_candidate", lambda *_: action)
    monkeypatch.setattr(qt_main, "_request_postgresql_credentials", lambda config: runtime)
    monkeypatch.setattr(qt_main.QMessageBox, "question", lambda *args: QMessageBox.StandardButton.No)
    dialog = MagicMock()
    dialog.exec.return_value = QDialog.DialogCode.Rejected
    monkeypatch.setattr(qt_main, "DatabaseConfigurationDialog", lambda **kwargs: dialog)
    result = qt_main._prepare_database_connection(config)
    assert result == ((config, runtime) if outcome == "ready" else None)
