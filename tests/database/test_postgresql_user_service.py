"""Isolierte Tests der zusätzlichen PostgreSQL-Benutzerverwaltung."""

from dataclasses import replace
from unittest.mock import MagicMock, patch

import pytest

from simpleob.core.config import ApplicationConfig
from simpleob.database.connection_credentials import PostgreSQLCredentials
from simpleob.database.postgresql_user_service import PostgreSQLUserService


@pytest.fixture
def config(tmp_path):
    return ApplicationConfig(
        data_dir=tmp_path,
        database_file=tmp_path / "test.db",
        taxonomy_dir=tmp_path,
        config_file=tmp_path / "config.toml",
        database_url_override="postgresql+psycopg://new_user@localhost:5432/books",
    )


def arguments(config):
    return dict(
        application_config=config,
        admin_credentials=PostgreSQLCredentials("admin-secret"),
        application_credentials=PostgreSQLCredentials("user-secret"),
        confirmed=True,
    )


@pytest.mark.parametrize(
    "url",
    [
        "sqlite:///test.db",
        "postgresql+psycopg://new_user@localhost:5432/postgres",
        "postgresql+psycopg://postgres@localhost:5432/books",
        "postgresql+psycopg://new_user:secret@localhost:5432/books",
        "postgresql+psycopg://" + "a" * 64 + "@localhost:5432/books",
    ],
)
def test_invalid_target_does_not_connect(config, url):
    with patch("simpleob.database.postgresql_user_service.create_engine") as engine:
        with pytest.raises(ValueError):
            PostgreSQLUserService().create_user(
                **arguments(replace(config, database_url_override=url)),
                new_database=True,
            )
        engine.assert_not_called()


def test_confirmation_and_nonempty_password_required(config):
    for changes in (
        {"confirmed": False},
        {"application_credentials": PostgreSQLCredentials("")},
    ):
        with pytest.raises(ValueError):
            PostgreSQLUserService().create_user(
                **(arguments(config) | changes), new_database=False
            )


def test_existing_role_is_not_changed(config):
    engine = MagicMock()
    connection = engine.connect.return_value.__enter__.return_value
    connection.execute.return_value.scalar_one_or_none.return_value = 1
    with (
        patch(
            "simpleob.database.postgresql_user_service.create_engine",
            return_value=engine,
        ),
        patch("simpleob.database.postgresql_user_service.postgresql_migration_lock"),
    ):
        with pytest.raises(ValueError, match="Benutzer.*existiert"):
            PostgreSQLUserService().create_user(**arguments(config), new_database=False)
    connection.exec_driver_sql.assert_not_called()
    engine.dispose.assert_called_once()


def test_password_is_encrypted_before_role_sql():
    connection = MagicMock()
    pgconn = connection.connection.driver_connection.pgconn
    pgconn.encrypt_password.return_value = b"SCRAM-SHA-256$verifier"
    PostgreSQLUserService._create_role(
        connection, 'user"name', PostgreSQLCredentials("clear-secret")
    )
    pgconn.encrypt_password.assert_called_once_with(
        b"clear-secret", b'user"name', b"scram-sha-256"
    )
    statement = connection.connection.driver_connection.cursor.return_value.__enter__.return_value.execute.call_args.args[
        0
    ]
    assert "clear-secret" not in str(statement)
    assert "SCRAM-SHA-256" in str(statement)


def test_existing_database_does_not_call_initializer(config):
    service = PostgreSQLUserService()
    engine = MagicMock()
    connection = engine.connect.return_value.__enter__.return_value
    connection.execute.return_value.scalar_one_or_none.side_effect = [None, 1]
    with (
        patch(
            "simpleob.database.postgresql_user_service.create_engine",
            return_value=engine,
        ),
        patch("simpleob.database.postgresql_user_service.postgresql_migration_lock"),
        patch.object(service, "_grant_existing_access"),
        patch.object(service, "_verify_access"),
        patch(
            "simpleob.database.postgresql_user_service.PostgreSQLInitializationService"
        ) as initializer,
    ):
        service.create_user(**arguments(config), new_database=False)
        initializer.assert_not_called()


def test_existing_access_grants_are_transactional_and_keep_owners(config):
    service = PostgreSQLUserService()
    engine = MagicMock()
    connection = engine.begin.return_value.__enter__.return_value
    connection.exec_driver_sql.return_value.scalar_one.return_value = "public"
    connection.exec_driver_sql.return_value.scalars.return_value.all.return_value = [
        "old_owner"
    ]
    connection.dialect.identifier_preparer.quote_identifier.side_effect = lambda s: (
        '"' + s.replace('"', '""') + '"'
    )
    from simpleob.database.database import Base

    with (
        patch(
            "simpleob.database.postgresql_user_service.create_engine",
            return_value=engine,
        ),
        patch("simpleob.database.postgresql_user_service.DatabaseMigrationService"),
        patch("simpleob.database.postgresql_user_service.inspect") as inspector,
        patch.object(service, "_create_role") as create_role,
    ):
        inspector.return_value.get_table_names.return_value = list(
            Base.metadata.tables
        ) + ["alembic_version"]
        service._grant_existing_access(
            config, PostgreSQLCredentials("admin"), PostgreSQLCredentials("user")
        )
        create_role.assert_called_once()
    statements = [call.args[0] for call in connection.exec_driver_sql.call_args_list]
    assert any(
        'GRANT CONNECT ON DATABASE "books" TO "new_user"' == s for s in statements
    )
    assert any('ON TABLE public."buchungen"' in s for s in statements)
    assert any("ON ALL SEQUENCES" in s for s in statements)
    assert any('ALTER DEFAULT PRIVILEGES FOR ROLE "old_owner"' in s for s in statements)
    assert not any("OWNER TO" in s or "ALTER TABLE" in s for s in statements)
    engine.begin.assert_called_once()


def test_unknown_tables_prevent_role_and_grant_creation(config):
    service = PostgreSQLUserService()
    engine = MagicMock()
    connection = engine.begin.return_value.__enter__.return_value
    connection.exec_driver_sql.return_value.scalar_one.return_value = "public"
    with (
        patch(
            "simpleob.database.postgresql_user_service.create_engine",
            return_value=engine,
        ),
        patch("simpleob.database.postgresql_user_service.DatabaseMigrationService"),
        patch("simpleob.database.postgresql_user_service.inspect") as inspector,
        patch.object(service, "_create_role") as create_role,
    ):
        inspector.return_value.get_table_names.return_value = ["unrelated_table"]
        with pytest.raises(ValueError, match="ausschließlich"):
            service._grant_existing_access(
                config, PostgreSQLCredentials("admin"), PostgreSQLCredentials("user")
            )
        create_role.assert_not_called()


def test_new_database_uses_existing_initializer(config):
    service = PostgreSQLUserService()
    engine = MagicMock()
    connection = engine.connect.return_value.__enter__.return_value
    connection.execute.return_value.scalar_one_or_none.return_value = None
    with (
        patch(
            "simpleob.database.postgresql_user_service.create_engine",
            return_value=engine,
        ),
        patch("simpleob.database.postgresql_user_service.postgresql_migration_lock"),
        patch.object(service, "_create_role"),
        patch.object(service, "_verify_access"),
        patch(
            "simpleob.database.postgresql_user_service.PostgreSQLInitializationService"
        ) as initializer,
    ):
        service.create_user(**arguments(config), new_database=True)
        initializer.return_value.initialize_database.assert_called_once()
        assert (
            initializer.return_value.initialize_database.call_args.kwargs[
                "admin_username"
            ]
            == "postgres"
        )


def test_partial_failure_is_reported_without_password(config):
    service = PostgreSQLUserService()
    engine = MagicMock()
    connection = engine.connect.return_value.__enter__.return_value
    connection.execute.return_value.scalar_one_or_none.return_value = None
    with (
        patch(
            "simpleob.database.postgresql_user_service.create_engine",
            return_value=engine,
        ),
        patch("simpleob.database.postgresql_user_service.postgresql_migration_lock"),
        patch.object(service, "_create_role"),
        patch(
            "simpleob.database.postgresql_user_service.PostgreSQLInitializationService"
        ) as initializer,
    ):
        failure = RuntimeError("user-secret")
        failure.sqlstate = "42501"
        initializer.return_value.initialize_database.side_effect = failure
        with pytest.raises(RuntimeError, match="möglicherweise bereits angelegt") as error:
            service.create_user(**arguments(config), new_database=True)
        assert "user-secret" not in str(error.value)
        assert "Phase: Initialisieren der neuen Datenbank" in str(error.value)
        assert "Fehlerklasse: RuntimeError" in str(error.value)
        assert "SQLSTATE: 42501" in str(error.value)


def test_failure_before_role_creation_reports_phase_without_details(config):
    engine = MagicMock()
    connection = engine.connect.return_value.__enter__.return_value
    connection.execute.side_effect = RuntimeError("private driver detail")
    with (
        patch(
            "simpleob.database.postgresql_user_service.create_engine",
            return_value=engine,
        ),
        patch("simpleob.database.postgresql_user_service.postgresql_migration_lock"),
    ):
        with pytest.raises(RuntimeError) as error:
            PostgreSQLUserService().create_user(
                **arguments(config), new_database=False
            )
    message = str(error.value)
    assert "Phase: Prüfung von Benutzer und Datenbank" in message
    assert "Fehlerklasse: RuntimeError" in message
    assert "SQLSTATE: nicht verfügbar" in message
    assert "Rolle wurde möglicherweise bereits angelegt" not in message
    assert "private driver detail" not in message
