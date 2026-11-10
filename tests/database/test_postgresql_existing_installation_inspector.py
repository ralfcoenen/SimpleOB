from __future__ import annotations

import os
import shutil
import socket
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
from alembic import command
from sqlalchemy import create_engine
from sqlalchemy.engine import URL

from simpleob.core.config import ApplicationConfig
from simpleob.database import models
from simpleob.database.connection_credentials import PostgreSQLCredentials
from simpleob.database.migration_service import (
    DatabaseMigrationService,
    PostgreSQLSchemaInspection,
    PostgreSQLSchemaStatus,
)
from simpleob.database.postgresql_existing_installation_inspector import (
    PostgreSQLDefaultPrivilege,
    PostgreSQLExistingInstallationInspector,
    PostgreSQLObjectOwner,
    PostgreSQLOwnershipAssessment,
    PostgreSQLRolePrivileges,
)
from simpleob.database.postgresql_role_separation_service import (
    PostgreSQLRoleSeparationService,
)


def _database(*, operating_role="operator", owner="migrator"):
    return SimpleNamespace(
        database_name="simpleob_books",
        server_version_num=160000,
        operating_role=operating_role,
        database_owner=owner,
    )


def _owners(owner="migrator", *, sequence_owner=None):
    table_owners = tuple(
        PostgreSQLObjectOwner(name, "table", owner)
        for name in sorted(set(models.Base.metadata.tables) | {"alembic_version"})
    )
    sequence_owners = (
        (
            PostgreSQLObjectOwner(
                "mandanten_id_seq", "sequence", sequence_owner, "mandanten"
            ),
        )
        if sequence_owner
        else ()
    )
    return table_owners, sequence_owners


def _role_privileges(
    *,
    role="operator",
    table_allowed=True,
    sequence_allowed=True,
    database_create=False,
    schema_create=False,
    alembic_dml=False,
):
    table_owners, sequence_owners = _owners()
    return PostgreSQLRolePrivileges(
        role=role,
        database_connect=True,
        database_create=database_create,
        database_temporary=False,
        schema_usage=True,
        schema_create=schema_create,
        table_privileges=tuple(
            (
                owner.name,
                privilege,
                (
                    alembic_dml
                    if owner.name == "alembic_version"
                    and privilege in {"INSERT", "UPDATE", "DELETE"}
                    else table_allowed
                ),
            )
            for owner in table_owners
            for privilege in ("SELECT", "INSERT", "UPDATE", "DELETE")
        ),
        sequence_privileges=tuple(
            ("mandanten_id_seq", privilege, sequence_allowed)
            for privilege in ("USAGE", "SELECT", "UPDATE")
        ),
    )


def _defaults(owner="migrator", grantee="operator"):
    return tuple(
        PostgreSQLDefaultPrivilege(owner, "public", "r", grantee, privilege, False)
        for privilege in ("SELECT", "INSERT", "UPDATE", "DELETE")
    ) + tuple(
        PostgreSQLDefaultPrivilege(owner, "public", "S", grantee, privilege, False)
        for privilege in ("USAGE", "SELECT")
    )


def _classify(
    *,
    operating_role="operator",
    owner="migrator",
    database_owner="migrator",
    schema_owner="migrator",
    schema_status=PostgreSQLSchemaStatus.CURRENT,
    role_privileges=None,
    defaults=None,
    sequence_owner=None,
):
    table_owners, sequence_owners = _owners(
        owner, sequence_owner=sequence_owner or owner
    )
    return PostgreSQLExistingInstallationInspector._classify(
        database=_database(operating_role=operating_role, owner=database_owner),
        schema_owner=schema_owner,
        server_version_num=160000,
        table_owners=table_owners,
        sequence_owners=sequence_owners,
        expected_tables=set(models.Base.metadata.tables) | {"alembic_version"},
        default_privileges=tuple(defaults if defaults is not None else _defaults()),
        role_privileges=tuple(
            role_privileges
            if role_privileges is not None
            else (_role_privileges(role=operating_role),)
        ),
        schema_status=schema_status,
    )


def test_uniform_object_ownership_is_reported_as_migration_candidate():
    assessment, migration_role, blockers, notes = _classify(
        operating_role="migrator", owner="migrator", database_owner="migrator"
    )

    assert assessment == PostgreSQLOwnershipAssessment.UNIFORM_OWNERSHIP
    assert migration_role == "migrator"
    assert not blockers
    assert notes


def test_different_table_and_sequence_owners_are_inconsistent():
    assessment, migration_role, blockers, _ = _classify(sequence_owner="other_owner")

    assert assessment == PostgreSQLOwnershipAssessment.INCONSISTENT_OWNERSHIP
    assert migration_role is None
    assert any("unterschiedliche Eigentümer" in item for item in blockers)


def test_separated_roles_require_runtime_and_future_object_privileges():
    assessment, migration_role, blockers, _ = _classify()

    assert assessment == PostgreSQLOwnershipAssessment.SPLIT_ROLES_COMPATIBLE
    assert migration_role == "migrator"
    assert not blockers


def test_writable_alembic_version_blocks_separated_role_compatibility():
    assessment, _, blockers, _ = _classify(
        role_privileges=(_role_privileges(alembic_dml=True),)
    )

    assert assessment == PostgreSQLOwnershipAssessment.INCONSISTENT_OWNERSHIP
    assert any("Änderungsrechte auf alembic_version" in item for item in blockers)


@pytest.mark.parametrize(
    "privileges",
    [
        _role_privileges(table_allowed=False),
        _role_privileges(sequence_allowed=False),
        _role_privileges(database_create=True),
        _role_privileges(schema_create=True),
    ],
)
def test_missing_or_excessive_runtime_rights_are_blockers(privileges):
    assessment, _, blockers, _ = _classify(role_privileges=(privileges,))

    assert assessment == PostgreSQLOwnershipAssessment.INCONSISTENT_OWNERSHIP
    assert blockers


def test_missing_future_default_privileges_are_reported():
    assessment, _, blockers, _ = _classify(defaults=())

    assert assessment == PostgreSQLOwnershipAssessment.INCONSISTENT_OWNERSHIP
    assert any("Default Privileges" in item for item in blockers)


def test_unknown_alembic_revision_yields_unknown_assessment():
    assessment, migration_role, blockers, _ = _classify(
        schema_status=PostgreSQLSchemaStatus.UNKNOWN
    )

    assert assessment == PostgreSQLOwnershipAssessment.UNKNOWN
    assert migration_role is None
    assert any("Revisionsstand" in item for item in blockers)


class _Result:
    def __init__(self, *, one=None, rows=(), scalar=True):
        self._one = one
        self._rows = rows
        self._scalar = scalar

    def one(self):
        return self._one

    def one_or_none(self):
        return self._one

    def all(self):
        return self._rows

    def scalar_one(self):
        return self._scalar


class _ReadOnlyConnection:
    class _Dialect:
        name = "postgresql"

    dialect = _Dialect()

    def __init__(self):
        self.statements = []

    def execute(self, statement, params=None):
        sql = str(statement).strip()
        self.statements.append(sql)
        if "current_database()" in sql:
            return _Result(
                one=SimpleNamespace(
                    database_name="simpleob_books",
                    operating_role="migrator",
                    server_version_num=160000,
                    database_owner="migrator",
                    can_connect=True,
                    can_create_database_objects=False,
                    can_create_temporary_objects=False,
                )
            )
        if "FROM pg_namespace AS n" in sql:
            return _Result(
                one=SimpleNamespace(schema_name="public", schema_owner="migrator")
            )
        if "FROM pg_class AS c" in sql:
            rows = [
                SimpleNamespace(
                    object_name=name,
                    relation_kind="r",
                    object_owner="migrator",
                    owning_table=None,
                )
                for name in sorted(
                    set(models.Base.metadata.tables) | {"alembic_version"}
                )
            ]
            rows.append(
                SimpleNamespace(
                    object_name="mandanten_id_seq",
                    relation_kind="S",
                    object_owner="migrator",
                    owning_table="mandanten",
                )
            )
            return _Result(rows=rows)
        if "FROM pg_default_acl AS d" in sql:
            return _Result(rows=())
        if "has_database_privilege" in sql:
            return _Result(
                one=SimpleNamespace(connect=True, create=False, temporary=False)
            )
        if "has_schema_privilege" in sql:
            return _Result(one=SimpleNamespace(usage=True, create=True))
        if "has_table_privilege" in sql or "has_sequence_privilege" in sql:
            return _Result(scalar=True)
        raise AssertionError(f"Unexpected SQL in read-only inspection: {sql}")


def test_inspection_uses_select_only_queries_and_reports_catalog_facts(monkeypatch):
    class _MigrationService:
        def __init__(self, **_kwargs):
            pass

        def inspect_postgresql_schema_on_connection(self, _connection):
            return PostgreSQLSchemaInspection(
                status=PostgreSQLSchemaStatus.CURRENT,
                current_revision="current_rev",
                head_revision="current_rev",
            )

    monkeypatch.setattr(
        "simpleob.database.postgresql_existing_installation_inspector.DatabaseMigrationService",
        _MigrationService,
    )
    connection = _ReadOnlyConnection()
    inspector = PostgreSQLExistingInstallationInspector(
        application_config=SimpleNamespace(
            database_url="postgresql+psycopg://migrator@localhost/books"
        )
    )

    result = inspector.inspect_on_connection(connection)

    assert connection.statements
    assert all(
        statement.upper().startswith("SELECT") for statement in connection.statements
    )
    assert result.database_owner == "migrator"
    assert result.schema_owner == "migrator"
    assert result.alembic_version_owner == "migrator"
    assert result.current_revision == "current_rev"
    assert result.schema_status == PostgreSQLSchemaStatus.CURRENT
    assert (
        result.ownership_assessment == PostgreSQLOwnershipAssessment.UNIFORM_OWNERSHIP
    )


@pytest.mark.integration
def test_existing_installation_inspection_on_isolated_postgresql_18(tmp_path):
    binary_dir_value = os.environ.get("SIMPLEOB_POSTGRES_BIN")
    if not binary_dir_value:
        pytest.skip("SIMPLEOB_POSTGRES_BIN für isolierten PostgreSQL-Test setzen.")
    binary_dir = Path(binary_dir_value)

    password_file = tmp_path / "cluster-password"
    password_file.write_text("temporary-cluster-secret\n", encoding="ascii")
    password_file.chmod(0o600)

    def run(binary_name: str, *args: str) -> None:
        subprocess.run(
            [str(binary_dir / binary_name), *args],
            check=True,
            capture_output=True,
            text=True,
            timeout=90,
        )

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]

    cluster = str(tmp_path / "cluster")
    started = False
    engines = []
    try:
        run(
            "initdb",
            "-D",
            cluster,
            "-U",
            "postgres",
            "--auth=scram-sha-256",
            f"--pwfile={password_file}",
            "--no-locale",
            "--encoding=UTF8",
        )
        run(
            "pg_ctl",
            "-D",
            cluster,
            "-l",
            str(tmp_path / "server.log"),
            "-o",
            f"-h 127.0.0.1 -p {port} -k ''",
            "-w",
            "start",
        )
        started = True

        bootstrap_url = URL.create(
            "postgresql+psycopg",
            username="postgres",
            password="temporary-cluster-secret",
            host="127.0.0.1",
            port=port,
            database="postgres",
        )
        bootstrap_engine = create_engine(
            bootstrap_url,
            hide_parameters=True,
            isolation_level="AUTOCOMMIT",
        )
        engines.append(bootstrap_engine)
        with bootstrap_engine.begin() as connection:
            connection.exec_driver_sql(
                "CREATE ROLE simpleob_migrator LOGIN "
                "PASSWORD 'temporary-migration-secret'"
            )
            connection.exec_driver_sql(
                "CREATE ROLE simpleob_other_owner LOGIN "
                "PASSWORD 'temporary-other-secret'"
            )
            connection.exec_driver_sql(
                "CREATE DATABASE simpleob_inspector_test OWNER simpleob_migrator"
            )

        migration_url = URL.create(
            "postgresql+psycopg",
            username="simpleob_migrator",
            host="127.0.0.1",
            port=port,
            database="simpleob_inspector_test",
        )
        migration_credentials = PostgreSQLCredentials("temporary-migration-secret")
        migration_config = ApplicationConfig(
            data_dir=tmp_path,
            database_file=tmp_path / "unused.sqlite",
            taxonomy_dir=tmp_path,
            config_file=tmp_path / "config.toml",
            database_url_override=migration_url.render_as_string(hide_password=True),
        )
        migration_service = DatabaseMigrationService(
            application_config=migration_config,
            credentials=migration_credentials,
        )
        migration_engine = create_engine(
            migration_url,
            connect_args={"password": migration_credentials.password},
            hide_parameters=True,
        )
        engines.append(migration_engine)
        with migration_engine.connect() as connection:
            alembic_config = migration_service._create_alembic_config()
            alembic_config.attributes["connection"] = connection
            with connection.begin():
                command.upgrade(alembic_config, "head")

        uniform = PostgreSQLExistingInstallationInspector(
            application_config=migration_config,
            credentials=migration_credentials,
        ).inspect()
        assert uniform.server_version_num >= 180000
        assert uniform.schema_owner == "pg_database_owner"
        assert uniform.database_owner == "simpleob_migrator"
        assert (
            uniform.ownership_assessment
            == PostgreSQLOwnershipAssessment.UNIFORM_OWNERSHIP
        )
        assert uniform.migration_role_candidate == "simpleob_migrator"
        assert uniform.current_revision == uniform.head_revision
        assert uniform.schema_status == PostgreSQLSchemaStatus.CURRENT
        assert uniform.alembic_version_owner == "simpleob_migrator"

        operator_url = migration_url.set(username="simpleob_operator")
        operator_credentials = PostgreSQLCredentials("temporary-operator-secret")
        separation = PostgreSQLRoleSeparationService().separate_roles(
            application_config=migration_config,
            owner_credentials=migration_credentials,
            operating_username="simpleob_operator",
            operating_credentials=operator_credentials,
            create_operating_role=True,
            admin_username="postgres",
            admin_credentials=PostgreSQLCredentials("temporary-cluster-secret"),
            confirmed=True,
        )
        assert separation.changed
        assert separation.operating_role_created
        assert separation.migration_role == "simpleob_migrator"
        operator_config = ApplicationConfig(
            data_dir=tmp_path,
            database_file=tmp_path / "unused.sqlite",
            taxonomy_dir=tmp_path,
            config_file=tmp_path / "config.toml",
            database_url_override=operator_url.render_as_string(hide_password=True),
        )
        split = PostgreSQLExistingInstallationInspector(
            application_config=operator_config,
            credentials=operator_credentials,
        ).inspect()
        assert (
            split.ownership_assessment
            == PostgreSQLOwnershipAssessment.SPLIT_ROLES_COMPATIBLE
        ), f"blockers={split.blockers!r}; notes={split.notes!r}"
        assert split.migration_role_candidate == "simpleob_migrator"
        assert split.operating_role == "simpleob_operator"
        assert split.alembic_version_privileges == (
            ("SELECT", True),
            ("INSERT", False),
            ("UPDATE", False),
            ("DELETE", False),
        )
        assert any(
            item.owner_role == "simpleob_migrator"
            and item.grantee == "simpleob_operator"
            and item.object_type == "r"
            and item.privilege == "INSERT"
            for item in split.default_privileges
        )
        assert any(
            item.owner_role == "simpleob_migrator"
            and item.grantee == "simpleob_operator"
            and item.object_type == "S"
            and item.privilege == "USAGE"
            for item in split.default_privileges
        )
        operating_privileges = next(
            item for item in split.role_privileges if item.role == "simpleob_operator"
        )
        assert not operating_privileges.schema_create
        assert not operating_privileges.database_create
        assert all(
            allowed
            for table, privilege, allowed in operating_privileges.table_privileges
            if table != "alembic_version" or privilege == "SELECT"
        )
        assert all(
            not allowed
            for table, privilege, allowed in operating_privileges.table_privileges
            if table == "alembic_version" and privilege != "SELECT"
        )
        assert all(
            allowed for _, _, allowed in operating_privileges.sequence_privileges
        )

        object_admin_engine = create_engine(
            bootstrap_url.set(database="simpleob_inspector_test"),
            hide_parameters=True,
        )
        engines.append(object_admin_engine)

        # Effective grants from PUBLIC must also make the split-role
        # assessment fail, even when the direct role ACL is read-only.
        with object_admin_engine.begin() as connection:
            connection.exec_driver_sql(
                "GRANT UPDATE ON TABLE public.alembic_version TO PUBLIC"
            )
        public_write = PostgreSQLExistingInstallationInspector(
            application_config=operator_config,
            credentials=operator_credentials,
        ).inspect()
        assert (
            public_write.ownership_assessment
            == PostgreSQLOwnershipAssessment.INCONSISTENT_OWNERSHIP
        )
        assert any(
            "Änderungsrechte auf alembic_version" in item
            for item in public_write.blockers
        )
        with object_admin_engine.begin() as connection:
            connection.exec_driver_sql(
                "REVOKE UPDATE ON TABLE public.alembic_version FROM PUBLIC"
            )

        # Role-membership grants are effective too and must not be treated as
        # a compatible runtime role.
        with bootstrap_engine.begin() as connection:
            connection.exec_driver_sql("CREATE ROLE simpleob_version_writer NOLOGIN")
        with object_admin_engine.begin() as connection:
            connection.exec_driver_sql(
                "GRANT UPDATE ON TABLE public.alembic_version "
                "TO simpleob_version_writer"
            )
        with bootstrap_engine.begin() as connection:
            connection.exec_driver_sql(
                "GRANT simpleob_version_writer TO simpleob_operator"
            )
        inherited_write = PostgreSQLExistingInstallationInspector(
            application_config=operator_config,
            credentials=operator_credentials,
        ).inspect()
        assert (
            inherited_write.ownership_assessment
            == PostgreSQLOwnershipAssessment.INCONSISTENT_OWNERSHIP
        )
        assert any(
            "Änderungsrechte auf alembic_version" in item
            for item in inherited_write.blockers
        )
        with bootstrap_engine.begin() as connection:
            connection.exec_driver_sql(
                "REVOKE simpleob_version_writer FROM simpleob_operator"
            )
        with object_admin_engine.begin() as connection:
            connection.exec_driver_sql(
                "REVOKE UPDATE ON TABLE public.alembic_version "
                "FROM simpleob_version_writer"
            )
        with bootstrap_engine.begin() as connection:
            connection.exec_driver_sql("DROP ROLE simpleob_version_writer")

        with object_admin_engine.begin() as connection:
            connection.exec_driver_sql(
                "ALTER TABLE public.mandanten OWNER TO simpleob_other_owner"
            )
        mixed = PostgreSQLExistingInstallationInspector(
            application_config=operator_config,
            credentials=operator_credentials,
        ).inspect()
        assert (
            mixed.ownership_assessment
            == PostgreSQLOwnershipAssessment.INCONSISTENT_OWNERSHIP
        )
        assert mixed.migration_role_candidate is None
        assert any("unterschiedliche Eigentümer" in item for item in mixed.blockers)
        with pytest.raises(RuntimeError, match="einheitlicher Eigentümerschaft"):
            PostgreSQLRoleSeparationService().separate_roles(
                application_config=migration_config,
                owner_credentials=migration_credentials,
                operating_username="simpleob_app_rejected",
                operating_credentials=PostgreSQLCredentials("rejected-secret"),
                create_operating_role=True,
                admin_username="postgres",
                admin_credentials=PostgreSQLCredentials("temporary-cluster-secret"),
                confirmed=True,
            )
        with bootstrap_engine.connect() as connection:
            assert (
                connection.exec_driver_sql(
                    "SELECT 1 FROM pg_roles WHERE rolname = 'simpleob_app_rejected'"
                ).scalar_one_or_none()
                is None
            )
    finally:
        for engine in engines:
            engine.dispose()
        try:
            if started:
                run("pg_ctl", "-D", cluster, "-m", "fast", "-w", "stop")
        finally:
            shutil.rmtree(cluster, ignore_errors=True)
            password_file.unlink(missing_ok=True)
            (tmp_path / "server.log").unlink(missing_ok=True)
