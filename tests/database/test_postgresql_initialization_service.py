from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from simpleob.core.config import ApplicationConfig
from simpleob.database.connection_credentials import PostgreSQLCredentials
from simpleob.database.postgresql_initialization_service import (
    PostgreSQLInitializationService,
)


def _config(tmp_path):
    return ApplicationConfig(
        data_dir=tmp_path,
        database_file=tmp_path / "unused.db",
        taxonomy_dir=tmp_path,
        config_file=tmp_path / "config.toml",
        database_url_override=(
            "postgresql+psycopg://simpleob_app@localhost:5432/simpleob_new"
        ),
    )


def _role(name, *, superuser=False, createdb=False, createrole=False, login=True):
    return SimpleNamespace(
        rolname=name,
        rolsuper=superuser,
        rolcreatedb=createdb,
        rolcreaterole=createrole,
        rolcanlogin=login,
    )


class _Result:
    def __init__(self, *, rows=(), scalar=None):
        self._rows = rows
        self._scalar = scalar

    def all(self):
        return self._rows

    def scalar_one(self):
        return self._scalar


def test_role_validation_requires_limited_separate_roles():
    connection = MagicMock()
    connection.execute.side_effect = [
        _Result(
            rows=(
                _role("operator"),
                _role("migrator"),
                _role("admin", createdb=True),
            )
        ),
        _Result(scalar=True),  # Admin can temporarily assume migrator.
        _Result(scalar=False),  # Operator is not a migrator member.
    ]
    connection.exec_driver_sql.return_value.scalar_one.return_value = 160000

    PostgreSQLInitializationService._validate_roles_and_admin(
        connection, "admin", "migrator", "operator"
    )

    assert connection.execute.call_count == 3


def test_roles_can_use_and_revoke_temporary_migration_createdb():
    connection = MagicMock()
    connection.execute.side_effect = [
        _Result(
            rows=(
                _role("operator"),
                _role("migrator", createdb=True),
                _role("admin", createrole=True),
            )
        ),
        _Result(scalar=False),  # Admin has no role-membership path.
        _Result(scalar=False),  # Operator is not a migrator member.
    ]
    connection.exec_driver_sql.return_value.scalar_one.return_value = 160000

    admin_can_create_as_owner = (
        PostgreSQLInitializationService._validate_roles_and_admin(
            connection, "admin", "migrator", "operator"
        )
    )

    assert not admin_can_create_as_owner


def test_missing_migration_role_is_rejected_before_privilege_checks():
    connection = MagicMock()
    connection.execute.return_value = _Result(
        rows=(_role("operator"), _role("admin", createdb=True))
    )

    with pytest.raises(RuntimeError, match="müssen vor der Datenbankanlage existieren"):
        PostgreSQLInitializationService._validate_roles_and_admin(
            connection, "admin", "migrator", "operator"
        )
    connection.exec_driver_sql.assert_not_called()


def test_missing_admin_database_privilege_is_rejected():
    connection = MagicMock()
    connection.execute.side_effect = [
        _Result(rows=(_role("operator"), _role("migrator"), _role("admin"))),
        _Result(scalar=False),  # No membership to assume the migration role.
        _Result(scalar=False),  # Operating role is not a migration-role member.
    ]
    connection.exec_driver_sql.return_value.scalar_one.return_value = 160000

    with pytest.raises(RuntimeError, match="Für die Datenbankanlage benötigt"):
        PostgreSQLInitializationService._validate_roles_and_admin(
            connection, "admin", "migrator", "operator"
        )


@pytest.mark.parametrize(
    ("migration", "operating", "message"),
    [
        (_role("migrator", createdb=True), _role("operator"), "Migrationsrolle"),
        (_role("migrator"), _role("operator", createrole=True), "Betriebsrolle"),
        (_role("migrator", login=False), _role("operator"), "Anmeldungen"),
    ],
)
def test_role_validation_rejects_elevated_or_non_login_roles(
    migration, operating, message
):
    connection = MagicMock()
    connection.execute.return_value = _Result(
        rows=(migration, operating, _role("admin", createdb=True))
    )

    with pytest.raises(RuntimeError, match=message):
        PostgreSQLInitializationService._validate_roles_and_admin(
            connection, "admin", "migrator", "operator"
        )


def test_new_database_configuration_installs_limited_grants():
    connection = MagicMock()
    connection.dialect.identifier_preparer.quote_identifier.side_effect = lambda value: (
        f'"{value}"'
    )

    PostgreSQLInitializationService._configure_new_database(
        connection, "migrator", "operator", "books"
    )

    statements = [call.args[0] for call in connection.exec_driver_sql.call_args_list]
    assert "REVOKE CREATE ON SCHEMA public FROM PUBLIC" in statements
    assert 'REVOKE TEMPORARY ON DATABASE "books" FROM PUBLIC' in statements
    assert 'GRANT USAGE ON SCHEMA public TO "operator"' in statements
    assert 'GRANT CONNECT ON DATABASE "books" TO "operator"' in statements
    assert any(
        'ALTER DEFAULT PRIVILEGES FOR ROLE "migrator"' in statement
        and "ON TABLES" in statement
        for statement in statements
    )
    assert any(
        'ALTER DEFAULT PRIVILEGES FOR ROLE "migrator"' in statement
        and "ON SEQUENCES" in statement
        for statement in statements
    )
    assert not any(
        'GRANT CREATE ON SCHEMA public TO "operator"' in s for s in statements
    )


def test_existing_database_is_rejected_before_any_ddl(tmp_path):
    service = PostgreSQLInitializationService()
    config = _config(tmp_path)
    engine = MagicMock()
    connection = engine.connect.return_value.__enter__.return_value
    connection.execute.return_value.scalar_one_or_none.return_value = 1
    connection.exec_driver_sql.return_value.scalar_one.return_value = 160000

    with (
        patch(
            "simpleob.database.postgresql_initialization_service.create_engine",
            return_value=engine,
        ),
        patch(
            "simpleob.database.postgresql_initialization_service.postgresql_migration_lock"
        ),
        patch.object(service, "_validate_roles_and_admin"),
        patch.object(
            service, "_template_public_owner", return_value="pg_database_owner"
        ),
    ):
        with pytest.raises(RuntimeError, match="existiert bereits"):
            service.initialize_database(
                application_config=config,
                admin_username="admin",
                admin_credentials=PostgreSQLCredentials("admin-secret"),
                migration_username="simpleob_migrator",
                migration_credentials=PostgreSQLCredentials("migration-secret"),
                application_credentials=PostgreSQLCredentials("app-secret"),
                confirmed=True,
            )

    assert not any(
        call.args[0].startswith("CREATE DATABASE")
        for call in connection.exec_driver_sql.call_args_list
    )
    engine.dispose.assert_called_once()
