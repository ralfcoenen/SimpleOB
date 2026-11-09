import stat
from pathlib import Path

import pytest

from simpleob.database.connection_credentials import (
    PostgreSQLCredentials,
    database_connect_args,
    postgresql_tool_environment,
)


def test_postgresql_credentials_are_passed_separately():
    credentials = PostgreSQLCredentials(
        password="test-secret"
    )

    result = database_connect_args(
        "postgresql+psycopg://testuser@localhost:5432/testdb",
        credentials,
    )

    assert result == {"password": "test-secret"}
    assert "test-secret" not in repr(credentials)


def test_postgresql_without_credentials_remains_unchanged():
    result = database_connect_args(
        "postgresql+psycopg://testuser@localhost:5432/testdb"
    )

    assert result == {}


def test_sqlite_does_not_receive_postgresql_credentials():
    result = database_connect_args(
        "sqlite:///test.db",
        PostgreSQLCredentials(password="test-secret"),
    )

    assert result == {}


def test_postgresql_tool_environment_uses_private_passfile(
    monkeypatch,
):
    monkeypatch.setenv("PGPASSWORD", "ambient-password")
    monkeypatch.setenv("PGPASSFILE", "/tmp/unrelated-passfile")
    monkeypatch.setenv("PGSERVICE", "unrelated-service")
    monkeypatch.setenv("PGSERVICEFILE", "/tmp/unrelated-service.conf")
    credentials = PostgreSQLCredentials("secret:with\\separator")
    passfile_path: Path

    with postgresql_tool_environment(
        "postgresql+psycopg://testuser@localhost:5432/testdb",
        credentials,
    ) as environment:
        passfile_path = Path(environment["PGPASSFILE"])
        assert passfile_path.is_file()
        assert stat.S_IMODE(passfile_path.stat().st_mode) == 0o600
        assert not passfile_path.resolve().is_relative_to(Path.cwd().resolve())
        assert passfile_path.read_text(encoding="utf-8") == (
            r"localhost:5432:testdb:testuser:secret\:with\\separator" + "\n"
        )
        assert "PGPASSWORD" not in environment
        assert "PGSERVICE" not in environment
        assert "PGSERVICEFILE" not in environment
        assert environment["PGPASSFILE"] == str(passfile_path)

    assert not passfile_path.exists()


def test_postgresql_tool_environment_removes_passfile_on_error():
    passfile_path: Path

    with pytest.raises(RuntimeError, match="test failure"):
        with postgresql_tool_environment(
            "postgresql+psycopg://testuser@localhost:5432/testdb",
            PostgreSQLCredentials("secret"),
        ) as environment:
            passfile_path = Path(environment["PGPASSFILE"])
            raise RuntimeError("test failure")

    assert not passfile_path.exists()


def test_postgresql_tool_environment_without_credentials_keeps_legacy_sources(
    monkeypatch,
):
    monkeypatch.setenv("PGPASSWORD", "discarded-password")
    monkeypatch.setenv("PGPASSFILE", "/tmp/legacy-passfile")

    with postgresql_tool_environment(
        "postgresql+psycopg://testuser@localhost:5432/testdb",
        None,
    ) as environment:
        assert "PGPASSWORD" not in environment
        assert environment["PGPASSFILE"] == "/tmp/legacy-passfile"
