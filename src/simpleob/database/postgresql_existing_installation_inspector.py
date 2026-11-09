"""Read-only assessment of an existing SimpleOB PostgreSQL installation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, make_url

from simpleob.core.config import ApplicationConfig
from simpleob.database import models
from simpleob.database.connection_credentials import (
    PostgreSQLCredentials,
    database_connect_args,
)
from simpleob.database.migration_service import (
    DatabaseMigrationService,
    PostgreSQLSchemaStatus,
)


class PostgreSQLOwnershipAssessment(str, Enum):
    """High-level compatibility of ownership and runtime grants."""

    UNIFORM_OWNERSHIP = "uniform_ownership"
    SPLIT_ROLES_COMPATIBLE = "split_roles_compatible"
    INCONSISTENT_OWNERSHIP = "inconsistent_ownership"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class PostgreSQLObjectOwner:
    name: str
    kind: str
    owner: str
    owning_table: str | None = None


@dataclass(frozen=True, slots=True)
class PostgreSQLDefaultPrivilege:
    owner_role: str
    schema_name: str
    object_type: str
    grantee: str
    privilege: str
    grantable: bool


@dataclass(frozen=True, slots=True)
class PostgreSQLRolePrivileges:
    role: str
    database_connect: bool
    database_create: bool
    database_temporary: bool
    schema_usage: bool
    schema_create: bool
    table_privileges: tuple[tuple[str, str, bool], ...]
    sequence_privileges: tuple[tuple[str, str, bool], ...]


@dataclass(frozen=True, slots=True)
class PostgreSQLExistingInstallationAssessment:
    """Immutable facts and findings for a future administrative dialog."""

    database_name: str
    server_version_num: int
    operating_role: str
    database_owner: str
    schema_name: str
    schema_owner: str
    table_owners: tuple[PostgreSQLObjectOwner, ...]
    sequence_owners: tuple[PostgreSQLObjectOwner, ...]
    alembic_version_owner: str | None
    alembic_version_privileges: tuple[tuple[str, bool], ...]
    role_privileges: tuple[PostgreSQLRolePrivileges, ...]
    default_privileges: tuple[PostgreSQLDefaultPrivilege, ...]
    current_revision: str | None
    head_revision: str
    schema_status: PostgreSQLSchemaStatus
    ownership_assessment: PostgreSQLOwnershipAssessment
    migration_role_candidate: str | None
    blockers: tuple[str, ...]
    notes: tuple[str, ...]


class PostgreSQLExistingInstallationInspector:
    """Inspect ownership and grants without changing database state."""

    _TABLE_PRIVILEGES = ("SELECT", "INSERT", "UPDATE", "DELETE")
    _SEQUENCE_PRIVILEGES = ("USAGE", "SELECT")

    def __init__(
        self,
        *,
        application_config: ApplicationConfig,
        credentials: PostgreSQLCredentials | None = None,
    ) -> None:
        self._application_config = application_config
        self._credentials = credentials

    def inspect(self) -> PostgreSQLExistingInstallationAssessment:
        """Connect to the configured database and perform SELECT-only checks."""
        url = make_url(self._application_config.database_url)
        if url.get_backend_name() != "postgresql":
            raise ValueError("Die Bestandsprüfung ist nur für PostgreSQL vorgesehen.")
        connect_url = url.set(password=None) if self._credentials is not None else url
        engine = create_engine(
            connect_url,
            connect_args=database_connect_args(
                connect_url.render_as_string(hide_password=True),
                self._credentials,
            ),
        )
        try:
            with engine.connect() as connection:
                return self.inspect_on_connection(connection)
        finally:
            engine.dispose()

    def inspect_on_connection(
        self, connection: Connection
    ) -> PostgreSQLExistingInstallationAssessment:
        """Inspect an existing PostgreSQL connection without writes or locks."""
        if connection.dialect.name != "postgresql":
            raise ValueError("Die Bestandsprüfung ist nur für PostgreSQL vorgesehen.")

        database = connection.execute(
            text(
                "SELECT current_database() AS database_name, "
                "current_user AS operating_role, "
                "current_setting('server_version_num')::integer AS server_version_num, "
                "pg_get_userbyid(d.datdba) AS database_owner, "
                "has_database_privilege(current_user, d.datname, 'CONNECT') AS can_connect, "
                "has_database_privilege(current_user, d.datname, 'CREATE') AS can_create_database_objects, "
                "has_database_privilege(current_user, d.datname, 'TEMP') AS can_create_temporary_objects "
                "FROM pg_database AS d WHERE d.datname = current_database()"
            )
        ).one()
        schema = connection.execute(
            text(
                "SELECT n.nspname AS schema_name, "
                "pg_get_userbyid(n.nspowner) AS schema_owner "
                "FROM pg_namespace AS n WHERE n.nspname = 'public'"
            )
        ).one_or_none()
        if schema is None:
            return self._unknown_without_schema(database)

        relation_rows = connection.execute(
            text(
                "SELECT c.relname AS object_name, c.relkind AS relation_kind, "
                "pg_get_userbyid(c.relowner) AS object_owner, "
                "tbl.relname AS owning_table "
                "FROM pg_class AS c "
                "JOIN pg_namespace AS n ON n.oid = c.relnamespace "
                "LEFT JOIN pg_depend AS dep ON dep.objid = c.oid "
                "AND dep.classid = 'pg_class'::regclass "
                "AND dep.refclassid = 'pg_class'::regclass "
                "AND dep.deptype IN ('a', 'i') "
                "LEFT JOIN pg_class AS tbl ON tbl.oid = dep.refobjid "
                "WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p', 'S') "
                "ORDER BY c.relkind, c.relname"
            )
        ).all()

        expected_tables = set(models.Base.metadata.tables) | {"alembic_version"}
        table_owners = tuple(
            PostgreSQLObjectOwner(row.object_name, "table", row.object_owner)
            for row in relation_rows
            if row.relation_kind in {"r", "p"} and row.object_name in expected_tables
        )
        sequence_owners = tuple(
            PostgreSQLObjectOwner(
                row.object_name,
                "sequence",
                row.object_owner,
                row.owning_table,
            )
            for row in relation_rows
            if row.relation_kind == "S"
            and row.owning_table in models.Base.metadata.tables
        )
        alembic_owner = next(
            (item.owner for item in table_owners if item.name == "alembic_version"),
            None,
        )

        migration_inspection = DatabaseMigrationService(
            application_config=self._application_config,
            credentials=self._credentials,
        ).inspect_postgresql_schema_on_connection(connection)

        default_privileges = self._read_default_privileges(connection)
        candidate_roles = {
            database.database_owner,
            schema.schema_owner,
            database.operating_role,
            *(item.owner for item in table_owners),
            *(item.owner for item in sequence_owners),
        }
        role_privileges = tuple(
            self._read_role_privileges(
                connection,
                role,
                database.database_name,
                schema.schema_name,
                table_owners,
                sequence_owners,
            )
            for role in sorted(candidate_roles)
            if role
        )
        alembic_privileges = (
            tuple(
                (privilege, allowed)
                for privilege, allowed in self._read_object_privileges(
                    connection,
                    database.operating_role,
                    'public."alembic_version"',
                    "table",
                    self._TABLE_PRIVILEGES,
                )
            )
            if alembic_owner
            else ()
        )

        classification, migration_role, blockers, notes = self._classify(
            database=database,
            schema_owner=schema.schema_owner,
            server_version_num=database.server_version_num,
            table_owners=table_owners,
            sequence_owners=sequence_owners,
            expected_tables=expected_tables,
            default_privileges=default_privileges,
            role_privileges=role_privileges,
            schema_status=migration_inspection.status,
        )
        return PostgreSQLExistingInstallationAssessment(
            database_name=database.database_name,
            server_version_num=database.server_version_num,
            operating_role=database.operating_role,
            database_owner=database.database_owner,
            schema_name=schema.schema_name,
            schema_owner=schema.schema_owner,
            table_owners=table_owners,
            sequence_owners=sequence_owners,
            alembic_version_owner=alembic_owner,
            alembic_version_privileges=alembic_privileges,
            role_privileges=role_privileges,
            default_privileges=default_privileges,
            current_revision=migration_inspection.current_revision,
            head_revision=migration_inspection.head_revision,
            schema_status=migration_inspection.status,
            ownership_assessment=classification,
            migration_role_candidate=migration_role,
            blockers=blockers,
            notes=notes,
        )

    @staticmethod
    def _read_default_privileges(
        connection: Connection,
    ) -> tuple[PostgreSQLDefaultPrivilege, ...]:
        rows = connection.execute(
            text(
                "SELECT pg_get_userbyid(d.defaclrole) AS owner_role, "
                "COALESCE(n.nspname, '*') AS schema_name, "
                "d.defaclobjtype::text AS object_type, "
                "CASE WHEN acl.grantee = 0 THEN 'PUBLIC' ELSE grantee.rolname END AS grantee, "
                "acl.privilege_type::text AS privilege, acl.is_grantable "
                "FROM pg_default_acl AS d "
                "CROSS JOIN LATERAL aclexplode(d.defaclacl) AS acl "
                "LEFT JOIN pg_namespace AS n ON n.oid = d.defaclnamespace "
                "LEFT JOIN pg_roles AS grantee ON grantee.oid = acl.grantee "
                "WHERE d.defaclnamespace = 0 OR n.nspname = 'public' "
                "ORDER BY owner_role, schema_name, object_type, grantee, privilege"
            )
        ).all()
        return tuple(
            PostgreSQLDefaultPrivilege(
                row.owner_role,
                row.schema_name,
                row.object_type,
                row.grantee,
                row.privilege,
                row.is_grantable,
            )
            for row in rows
        )

    def _read_role_privileges(
        self,
        connection: Connection,
        role: str,
        database_name: str,
        schema_name: str,
        table_owners: tuple[PostgreSQLObjectOwner, ...],
        sequence_owners: tuple[PostgreSQLObjectOwner, ...],
    ) -> PostgreSQLRolePrivileges:
        database = connection.execute(
            text(
                "SELECT has_database_privilege(:role, :database, 'CONNECT') AS connect, "
                "has_database_privilege(:role, :database, 'CREATE') AS create, "
                "has_database_privilege(:role, :database, 'TEMP') AS temporary"
            ),
            {"role": role, "database": database_name},
        ).one()
        schema = connection.execute(
            text(
                "SELECT has_schema_privilege(:role, :schema, 'USAGE') AS usage, "
                "has_schema_privilege(:role, :schema, 'CREATE') AS create"
            ),
            {"role": role, "schema": schema_name},
        ).one()
        table_privileges = tuple(
            (relation.name, privilege, allowed)
            for relation in table_owners
            for privilege, allowed in self._read_object_privileges(
                connection,
                role,
                f'public."{relation.name.replace(chr(34), chr(34) * 2)}"',
                "table",
                self._TABLE_PRIVILEGES,
            )
        )
        sequence_privileges = tuple(
            (relation.name, privilege, allowed)
            for relation in sequence_owners
            for privilege, allowed in self._read_object_privileges(
                connection,
                role,
                f'public."{relation.name.replace(chr(34), chr(34) * 2)}"',
                "sequence",
                self._SEQUENCE_PRIVILEGES,
            )
        )
        return PostgreSQLRolePrivileges(
            role=role,
            database_connect=database.connect,
            database_create=database.create,
            database_temporary=database.temporary,
            schema_usage=schema.usage,
            schema_create=schema.create,
            table_privileges=table_privileges,
            sequence_privileges=sequence_privileges,
        )

    @staticmethod
    def _read_object_privileges(
        connection: Connection,
        role: str,
        object_name: str,
        object_kind: str,
        privileges: tuple[str, ...],
    ) -> tuple[tuple[str, bool], ...]:
        function = (
            "has_table_privilege"
            if object_kind == "table"
            else "has_sequence_privilege"
        )
        return tuple(
            (
                privilege,
                bool(
                    connection.execute(
                        text(f"SELECT {function}(:role, :object_name, :privilege)"),
                        {
                            "role": role,
                            "object_name": object_name,
                            "privilege": privilege,
                        },
                    ).scalar_one()
                ),
            )
            for privilege in privileges
        )

    @staticmethod
    def _classify(
        *,
        database,
        schema_owner: str,
        server_version_num: int,
        table_owners: tuple[PostgreSQLObjectOwner, ...],
        sequence_owners: tuple[PostgreSQLObjectOwner, ...],
        expected_tables: set[str],
        default_privileges: tuple[PostgreSQLDefaultPrivilege, ...],
        role_privileges: tuple[PostgreSQLRolePrivileges, ...],
        schema_status: PostgreSQLSchemaStatus,
    ) -> tuple[
        PostgreSQLOwnershipAssessment,
        str | None,
        tuple[str, ...],
        tuple[str, ...],
    ]:
        blockers: list[str] = []
        notes: list[str] = []
        actual_tables = {item.name for item in table_owners}
        missing_tables = sorted(expected_tables - actual_tables)
        if missing_tables:
            blockers.append("SimpleOB-Tabellen fehlen: " + ", ".join(missing_tables))
        if schema_status == PostgreSQLSchemaStatus.UNKNOWN:
            blockers.append("Der Alembic-Revisionsstand ist unbekannt.")
        elif schema_status == PostgreSQLSchemaStatus.EMPTY:
            blockers.append(
                "Das Schema ist leer und enthält keine installierte SimpleOB-Struktur."
            )
        if missing_tables or schema_status in {
            PostgreSQLSchemaStatus.UNKNOWN,
            PostgreSQLSchemaStatus.EMPTY,
        }:
            return (
                PostgreSQLOwnershipAssessment.UNKNOWN,
                None,
                tuple(blockers),
                tuple(notes),
            )

        object_owners = {item.owner for item in (*table_owners, *sequence_owners)}
        if len(object_owners) != 1:
            blockers.append(
                "SimpleOB-Tabellen oder Sequenzen haben unterschiedliche Eigentümer."
            )
            return (
                PostgreSQLOwnershipAssessment.INCONSISTENT_OWNERSHIP,
                None,
                tuple(blockers),
                tuple(notes),
            )
        migration_role = next(iter(object_owners))
        if database.database_owner != migration_role:
            blockers.append(
                "Datenbank- und Schemaobjekte haben unterschiedliche Eigentümer."
            )
        pg_database_owner_schema = (
            schema_owner == "pg_database_owner" and server_version_num >= 150000
        )
        if schema_owner != migration_role and not pg_database_owner_schema:
            blockers.append(
                "Das public-Schema gehört weder der Migrationsrolle noch pg_database_owner."
            )
        if blockers:
            return (
                PostgreSQLOwnershipAssessment.INCONSISTENT_OWNERSHIP,
                migration_role,
                tuple(blockers),
                tuple(notes),
            )

        runtime = next(
            (item for item in role_privileges if item.role == database.operating_role),
            None,
        )
        if runtime is None or not runtime.database_connect or not runtime.schema_usage:
            blockers.append(
                "Der Anwendungsrolle fehlen CONNECT- oder Schema-USAGE-Rechte."
            )
        elif database.operating_role == migration_role:
            notes.append(
                "Die aktuelle Anwendungsrolle ist zugleich Eigentümerin; die Rollen sind noch nicht getrennt."
            )
            return (
                PostgreSQLOwnershipAssessment.UNIFORM_OWNERSHIP,
                migration_role,
                tuple(blockers),
                tuple(notes),
            )

        missing_runtime = [
            (name, privilege)
            for name, privilege, allowed in (
                runtime.table_privileges if runtime else ()
            )
            if not allowed and (name != "alembic_version" or privilege == "SELECT")
        ]
        if missing_runtime:
            blockers.append("Der Anwendungsrolle fehlen erforderliche Tabellenrechte.")
        missing_sequences = [
            (name, privilege)
            for name, privilege, allowed in (
                runtime.sequence_privileges if runtime else ()
            )
            if not allowed
        ]
        if missing_sequences:
            details = ", ".join(
                f"{name} ({privilege})" for name, privilege in missing_sequences
            )
            blockers.append(
                "Der Anwendungsrolle fehlen erforderliche Sequenzrechte: " + details
            )
        if runtime and (runtime.database_create or runtime.schema_create):
            blockers.append(
                "Die Anwendungsrolle besitzt nicht erforderliche Datenbank- oder Schemaerstellungsrechte."
            )

        required_table_defaults = set(
            PostgreSQLExistingInstallationInspector._TABLE_PRIVILEGES
        )
        required_sequence_defaults = {"USAGE", "SELECT"}
        table_defaults = {
            item.privilege
            for item in default_privileges
            if item.owner_role == migration_role
            and item.schema_name in {"public", "*"}
            and item.object_type == "r"
            and item.grantee == database.operating_role
        }
        sequence_defaults = {
            item.privilege
            for item in default_privileges
            if item.owner_role == migration_role
            and item.schema_name in {"public", "*"}
            and item.object_type == "S"
            and item.grantee == database.operating_role
        }
        if not required_table_defaults.issubset(table_defaults):
            blockers.append(
                "Default Privileges für künftige SimpleOB-Tabellen fehlen oder sind unvollständig."
            )
        if not required_sequence_defaults.issubset(sequence_defaults):
            blockers.append(
                "Default Privileges für künftige SimpleOB-Sequenzen fehlen oder sind unvollständig."
            )
        if schema_status == PostgreSQLSchemaStatus.OUTDATED:
            notes.append(
                "Das Alembic-Schema ist bekannt, aber nicht auf dem aktuellen Projekt-Head."
            )
        return (
            PostgreSQLOwnershipAssessment.INCONSISTENT_OWNERSHIP
            if blockers
            else PostgreSQLOwnershipAssessment.SPLIT_ROLES_COMPATIBLE,
            migration_role,
            tuple(blockers),
            tuple(notes),
        )

    @staticmethod
    def _unknown_without_schema(database):
        return PostgreSQLExistingInstallationAssessment(
            database_name=database.database_name,
            server_version_num=database.server_version_num,
            operating_role=database.operating_role,
            database_owner=database.database_owner,
            schema_name="public",
            schema_owner="",
            table_owners=(),
            sequence_owners=(),
            alembic_version_owner=None,
            alembic_version_privileges=(),
            role_privileges=(),
            default_privileges=(),
            current_revision=None,
            head_revision="",
            schema_status=PostgreSQLSchemaStatus.UNKNOWN,
            ownership_assessment=PostgreSQLOwnershipAssessment.UNKNOWN,
            migration_role_candidate=None,
            blockers=("Das erwartete PostgreSQL-Schema public wurde nicht gefunden.",),
            notes=(),
        )
