"""Tests für die konfigurierbare Datenbank."""

import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
from sqlalchemy import inspect

from simpleob.core.config import ApplicationConfig
from simpleob.database import database as database_module
from simpleob.database.database import Database


def create_config(
    tmp_path: Path,
) -> ApplicationConfig:
    """Erzeugt eine isolierte Testkonfiguration."""

    return ApplicationConfig(
        data_dir=tmp_path,
        database_file=(
            tmp_path
            / "openbilanz.db"
        ),
        taxonomy_dir=(
            tmp_path
            / "taxonomy"
        ),
        config_file=(
            tmp_path
            / "config.toml"
        ),
    )


@pytest.mark.parametrize(
    "module_name",
    ["simpleob.database.database", "simpleob.qt_main"],
)
def test_import_with_invalid_toml_reaches_runtime_error_handling(
    tmp_path: Path,
    module_name: str,
) -> None:
    config_file = tmp_path / "config.toml"
    original = b"[database\nurl = 'sqlite:///broken.db'\n"
    config_file.write_bytes(original)

    script = textwrap.dedent(
        """
        import importlib
        import sys
        from pathlib import Path
        from unittest.mock import patch

        import simpleob.core.config as config_module

        config_path = Path(sys.argv[2])
        defaults = config_module.ApplicationConfig(
            data_dir=config_path.parent,
            database_file=config_path.parent / "openbilanz.db",
            taxonomy_dir=config_path.parent / "taxonomy",
            config_file=config_path,
        )
        config_module.default_config = lambda: defaults

        if sys.argv[1] == "simpleob.database.database":
            database_module = importlib.import_module(sys.argv[1])
            assert database_module._default_database is None
            try:
                config_module.load_config()
            except config_module.ConfigurationSyntaxError as error:
                assert error.path == config_path
            else:
                raise AssertionError("The damaged TOML was not rejected")
        else:
            qt_main = importlib.import_module(sys.argv[1])
            database_module = importlib.import_module(
                "simpleob.database.database"
            )
            assert database_module._default_database is None
            messages = []
            with patch.object(
                qt_main.QMessageBox,
                "critical",
                side_effect=lambda *args: messages.append(args),
            ):
                assert qt_main._load_startup_configuration() is None
            assert len(messages) == 1
            assert str(config_path) in messages[0][2]
            assert database_module._default_database is None

        assert config_path.read_bytes() == b"[database\\nurl = 'sqlite:///broken.db'\\n"
        assert not defaults.database_file.exists()
        """
    )
    environment = os.environ.copy()
    environment["QT_QPA_PLATFORM"] = "offscreen"
    result = subprocess.run(
        [sys.executable, "-c", script, module_name, str(config_file)],
        check=False,
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parents[2],
        env=environment,
        timeout=30,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert config_file.read_bytes() == original
    assert not (tmp_path / "openbilanz.db").exists()


@pytest.mark.parametrize("function_name", ["create_database", "create_session"])
def test_compatibility_functions_initialize_default_database_lazily(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    function_name: str,
) -> None:
    config = create_config(tmp_path)
    calls: list[str] = []
    session = object()

    class FakeDatabase:
        def __init__(self, received_config: ApplicationConfig) -> None:
            assert received_config is config

        def create_database(self) -> None:
            calls.append("create_database")

        def create_session(self) -> object:
            calls.append("create_session")
            return session

    monkeypatch.setattr(database_module, "_default_database", None)
    monkeypatch.setattr(database_module, "Database", FakeDatabase)
    monkeypatch.setattr(database_module, "load_config", lambda: config)

    result = getattr(database_module, function_name)()

    assert database_module._default_database is not None
    assert calls == [function_name]
    if function_name == "create_session":
        assert result is session


def test_legacy_engine_attribute_is_resolved_lazily(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = create_config(tmp_path)
    expected_engine = object()

    class FakeDatabase:
        def __init__(self, received_config: ApplicationConfig) -> None:
            assert received_config is config
            self.engine = expected_engine

    monkeypatch.setattr(database_module, "_default_database", None)
    monkeypatch.setattr(database_module, "Database", FakeDatabase)
    monkeypatch.setattr(database_module, "load_config", lambda: config)

    assert database_module._default_database is None
    namespace = {}
    exec("from simpleob.database.database import engine", namespace)
    assert namespace["engine"] is expected_engine
    assert database_module._default_database is not None


def test_database_uses_configured_database_file(
    tmp_path: Path,
) -> None:
    config = create_config(
        tmp_path
    )

    database = Database(
        config
    )

    try:
        assert str(
            database.engine.url
        ) == config.database_url
    finally:
        database.dispose()


def test_database_creates_schema(
    tmp_path: Path,
) -> None:
    config = create_config(
        tmp_path
    )

    database = Database(
        config
    )

    try:
        database.create_database()

        tables = inspect(
            database.engine
        ).get_table_names()

        assert "mandanten" in tables
        assert "wirtschaftsjahre" in tables
        assert "buchungen" in tables
        assert "buchungszeilen" in tables
    finally:
        database.dispose()


def test_database_creates_session(
    tmp_path: Path,
) -> None:
    config = create_config(
        tmp_path
    )

    database = Database(
        config
    )

    try:
        database.create_database()

        session = database.create_session()

        try:
            assert session.bind is database.engine
        finally:
            session.close()
    finally:
        database.dispose()


def test_database_uses_postgresql_configuration(
    tmp_path: Path,
) -> None:
    config = ApplicationConfig(
        data_dir=tmp_path,
        database_file=tmp_path / "openbilanz.db",
        taxonomy_dir=tmp_path / "taxonomy",
        config_file=tmp_path / "config.toml",
        database_url_override=(
            "postgresql+psycopg://"
            "simpleob@localhost:5432/simpleob"
        ),
    )

    database = Database(config)

    try:
        assert database.engine.dialect.name == "postgresql"
        assert database.engine.url.drivername == (
            "postgresql+psycopg"
        )
    finally:
        database.dispose()
