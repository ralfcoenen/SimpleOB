"""Confirmed conversion of a uniformly owned PostgreSQL installation."""

from __future__ import annotations

from dataclasses import dataclass, replace

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

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
from simpleob.database.postgresql_existing_installation_inspector import (
    PostgreSQLExistingInstallationAssessment,
    PostgreSQLExistingInstallationInspector,
    PostgreSQLOwnershipAssessment,
)
from simpleob.database.postgresql_runtime_privileges import (
    enforce_read_only_alembic_version,
    grant_application_table_privileges,
)
from simpleob.database.postgresql_user_service import PostgreSQLUserService


@dataclass(frozen=True, slots=True)
class PostgreSQLRoleSeparationResult:
    database_name: str
    migration_role: str
    operating_role: str
    database_url: str
    operating_role_created: bool
    changed: bool


class PostgreSQLRoleSeparationService:
    """Create runtime grants while leaving all existing objects owned in place."""

    def separate_roles(
        self,
        *,
        application_config: ApplicationConfig,
        owner_credentials: PostgreSQLCredentials,
        operating_username: str,
        operating_credentials: PostgreSQLCredentials,
        create_operating_role: bool,
        admin_username: str | None = None,
        admin_credentials: PostgreSQLCredentials | None = None,
        confirmed: bool,
    ) -> PostgreSQLRoleSeparationResult:
        url = make_url(application_config.database_url)
        if (
            url.drivername != "postgresql+psycopg"
            or url.password is not None
            or not url.host
            or url.port is None
            or not url.database
            or not url.username
        ):
            raise ValueError(
                "Eine vollständige PostgreSQL-URL ohne Passwort ist erforderlich."
            )
        if url.database in {"postgres", "template0", "template1"}:
            raise ValueError(
                "Eine PostgreSQL-Systemdatenbank kann nicht umgestellt werden."
            )
        if not confirmed:
            raise ValueError("Die Rollenaufteilung muss ausdrücklich bestätigt werden.")
        if not isinstance(owner_credentials, PostgreSQLCredentials):
            raise ValueError("Die Zugangsdaten der bisherigen Eigentümerrolle fehlen.")
        if not isinstance(operating_credentials, PostgreSQLCredentials):
            raise ValueError("Die Zugangsdaten der Betriebsrolle fehlen.")
        if (
            not operating_username
            or operating_username != operating_username.strip()
            or operating_username.startswith("pg_")
            or len(operating_username.encode()) > 63
            or "\x00" in operating_username
            or not operating_credentials.password
            or "\x00" in operating_credentials.password
        ):
            raise ValueError("Die Betriebsrolle oder ihr Passwort ist ungültig.")

        owner_role = url.username
        inspector = PostgreSQLExistingInstallationInspector(
            application_config=application_config,
            credentials=owner_credentials,
        )
        # Mandatory fresh assessment before any role or ACL change.
        assessment = inspector.inspect()
        if (
            assessment.ownership_assessment
            == PostgreSQLOwnershipAssessment.SPLIT_ROLES_COMPATIBLE
        ):
            if assessment.operating_role != operating_username:
                raise RuntimeError(
                    "Die Datenbank ist bereits für getrennte Rollen eingerichtet. "
                    "Es wurden keine Änderungen vorgenommen."
                )
            return PostgreSQLRoleSeparationResult(
                database_name=assessment.database_name,
                migration_role=assessment.migration_role_candidate or owner_role,
                operating_role=assessment.operating_role,
                database_url=url.render_as_string(hide_password=True),
                operating_role_created=False,
                changed=False,
            )
        self._require_uniform_owner_assessment(assessment, owner_role)
        if operating_username == owner_role:
            raise ValueError("Betriebs- und Migrationsrolle müssen verschieden sein.")
        self._verify_exact_simpleob_schema(url, owner_credentials, assessment)
        self._reject_public_create_grants(url, owner_credentials)

        if create_operating_role:
            if not admin_username or admin_username.strip() != admin_username:
                raise ValueError(
                    "Eine administrative PostgreSQL-Rolle ist erforderlich."
                )
            if admin_username == operating_username:
                raise ValueError(
                    "Administrations- und Betriebsrolle müssen verschieden sein."
                )
            if not isinstance(admin_credentials, PostgreSQLCredentials):
                raise ValueError("Die Zugangsdaten der Administrationsrolle fehlen.")
            self._create_operating_role(
                url=url,
                admin_username=admin_username,
                admin_credentials=admin_credentials,
                operating_username=operating_username,
                operating_credentials=operating_credentials,
            )
        else:
            if admin_username is not None or admin_credentials is not None:
                raise ValueError(
                    "Für eine bestehende Betriebsrolle sind keine Administrationsdaten nötig."
                )
            self._validate_existing_operating_role(
                url=url,
                owner_credentials=owner_credentials,
                owner_role=owner_role,
                operating_username=operating_username,
            )

        # Recheck immediately before changing database/schema/object grants.
        fresh_assessment = inspector.inspect()
        self._require_uniform_owner_assessment(fresh_assessment, owner_role)
        self._verify_exact_simpleob_schema(url, owner_credentials, fresh_assessment)

        self._grant_operating_access(
            url=url,
            owner_credentials=owner_credentials,
            owner_role=owner_role,
            operating_username=operating_username,
        )

        operating_url = url.set(username=operating_username)
        operating_config = replace(
            application_config,
            database_url_override=operating_url.render_as_string(hide_password=True),
        )
        DatabaseMigrationService(
            application_config=operating_config,
            credentials=operating_credentials,
        ).check_ready_for_start()
        final_assessment = PostgreSQLExistingInstallationInspector(
            application_config=operating_config,
            credentials=operating_credentials,
        ).inspect()
        if (
            final_assessment.ownership_assessment
            != PostgreSQLOwnershipAssessment.SPLIT_ROLES_COMPATIBLE
            or final_assessment.operating_role != operating_username
            or final_assessment.migration_role_candidate != owner_role
            or final_assessment.schema_status != PostgreSQLSchemaStatus.CURRENT
            or final_assessment.blockers
        ):
            raise RuntimeError(
                "Die Betriebsrolle wurde angelegt und Rechte wurden vergeben, "
                "aber die Abschlussprüfung war nicht erfolgreich. Die "
                "Anwendungskonfiguration wurde nicht umgestellt. Bitte den "
                "Datenbankzustand administrativ prüfen."
            )
        alembic_privileges = dict(final_assessment.alembic_version_privileges)
        if not alembic_privileges.get("SELECT") or any(
            alembic_privileges.get(privilege, False)
            for privilege in ("INSERT", "UPDATE", "DELETE")
        ):
            raise RuntimeError(
                "Die Betriebsrolle besitzt keine ausschließlich lesenden Rechte "
                "auf alembic_version. Die Anwendungskonfiguration wurde nicht "
                "umgestellt."
            )

        return PostgreSQLRoleSeparationResult(
            database_name=url.database,
            migration_role=owner_role,
            operating_role=operating_username,
            database_url=operating_url.render_as_string(hide_password=True),
            operating_role_created=create_operating_role,
            changed=True,
        )

    @staticmethod
    def _require_uniform_owner_assessment(
        assessment: PostgreSQLExistingInstallationAssessment,
        owner_role: str,
    ) -> None:
        if (
            assessment.ownership_assessment
            != PostgreSQLOwnershipAssessment.UNIFORM_OWNERSHIP
            or assessment.operating_role != owner_role
            or assessment.migration_role_candidate != owner_role
            or assessment.database_owner != owner_role
            or assessment.schema_owner not in {owner_role, "pg_database_owner"}
            or assessment.schema_status != PostgreSQLSchemaStatus.CURRENT
            or assessment.blockers
            or any(item.owner != owner_role for item in assessment.table_owners)
            or any(item.owner != owner_role for item in assessment.sequence_owners)
            or not assessment.alembic_version_owner
            or assessment.alembic_version_owner != owner_role
        ):
            details = " ".join(assessment.blockers)
            raise RuntimeError(
                "Die Rollenaufteilung wird nur bei einer aktuellen Installation "
                "mit einheitlicher Eigentümerschaft unterstützt. Es wurden "
                "keine Rechte- oder Eigentumsänderungen vorgenommen. " + details
            )

    @staticmethod
    def _verify_exact_simpleob_schema(url, credentials, assessment) -> None:
        engine = create_engine(
            url,
            hide_parameters=True,
            connect_args=database_connect_args(
                url.render_as_string(hide_password=True), credentials
            ),
        )
        try:
            with engine.connect() as connection:
                actual_tables = set(
                    inspect(connection).get_table_names(schema="public")
                )
                expected_tables = set(models.Base.metadata.tables) | {"alembic_version"}
                actual_sequences = set(
                    inspect(connection).get_sequence_names(schema="public")
                )
                assessed_sequences = {item.name for item in assessment.sequence_owners}
                if actual_tables != expected_tables:
                    raise RuntimeError(
                        "Das public-Schema enthält zusätzliche oder fehlende Tabellen; "
                        "die Rollenaufteilung wird sicherheitshalber abgebrochen."
                    )
                if actual_sequences != assessed_sequences:
                    raise RuntimeError(
                        "Das public-Schema enthält nicht eindeutig zuordenbare Sequenzen; "
                        "die Rollenaufteilung wird sicherheitshalber abgebrochen."
                    )
        finally:
            engine.dispose()

    @staticmethod
    def _reject_public_create_grants(url, credentials) -> None:
        engine = create_engine(
            url,
            hide_parameters=True,
            connect_args=database_connect_args(
                url.render_as_string(hide_password=True), credentials
            ),
        )
        try:
            with engine.connect() as connection:
                granted_to_public = connection.execute(
                    text(
                        "SELECT EXISTS ("
                        "SELECT 1 FROM pg_namespace AS n "
                        "CROSS JOIN LATERAL aclexplode("
                        "COALESCE(n.nspacl, acldefault('n', n.nspowner))"
                        ") AS acl "
                        "WHERE n.nspname = 'public' AND acl.grantee = 0 "
                        "AND acl.privilege_type = 'CREATE'"
                        ")"
                    )
                ).scalar_one()
                if granted_to_public:
                    raise RuntimeError(
                        "Das public-Schema gewährt CREATE an PUBLIC. Diese "
                        "globale Berechtigung wird von diesem Vorgang nicht "
                        "verändert; die Rollenaufteilung ist daher nicht sicher möglich."
                    )
        finally:
            engine.dispose()

    @staticmethod
    def _create_operating_role(
        *,
        url,
        admin_username,
        admin_credentials,
        operating_username,
        operating_credentials,
    ) -> None:
        admin_url = url.set(
            username=admin_username,
            password=None,
        )
        engine = create_engine(
            admin_url,
            isolation_level="AUTOCOMMIT",
            hide_parameters=True,
            connect_args=database_connect_args(
                admin_url.render_as_string(hide_password=True), admin_credentials
            ),
        )
        try:
            with engine.connect() as connection:
                flags = connection.execute(
                    text(
                        "SELECT rolsuper, rolcreaterole FROM pg_roles "
                        "WHERE rolname = current_user"
                    )
                ).one_or_none()
                if flags is None or (not flags.rolsuper and not flags.rolcreaterole):
                    raise RuntimeError(
                        "Die Administrationsrolle benötigt CREATEROLE oder SUPERUSER."
                    )
                exists = connection.execute(
                    text("SELECT 1 FROM pg_roles WHERE rolname = :role"),
                    {"role": operating_username},
                ).scalar_one_or_none()
                if exists is not None:
                    raise ValueError(
                        "Die angegebene Betriebsrolle existiert bereits. "
                        "Wählen Sie die Verwendung einer vorhandenen Rolle."
                    )
                PostgreSQLUserService._create_role(
                    connection,
                    operating_username,
                    operating_credentials,
                )
        finally:
            engine.dispose()

    @staticmethod
    def _validate_existing_operating_role(
        *, url, owner_credentials, owner_role, operating_username
    ) -> None:
        engine = create_engine(
            url,
            hide_parameters=True,
            connect_args=database_connect_args(
                url.render_as_string(hide_password=True), owner_credentials
            ),
        )
        try:
            with engine.connect() as connection:
                role = connection.execute(
                    text(
                        "SELECT rolcanlogin, rolsuper, rolcreatedb, rolcreaterole, "
                        "rolreplication, rolbypassrls FROM pg_roles WHERE rolname = :role"
                    ),
                    {"role": operating_username},
                ).one_or_none()
                if role is None:
                    raise ValueError("Die ausgewählte Betriebsrolle existiert nicht.")
                if not role.rolcanlogin or any(
                    (
                        role.rolsuper,
                        role.rolcreatedb,
                        role.rolcreaterole,
                        role.rolreplication,
                        role.rolbypassrls,
                    )
                ):
                    raise ValueError(
                        "Die vorhandene Betriebsrolle ist nicht ausreichend beschränkt."
                    )
                is_migration_member = connection.execute(
                    text(
                        "SELECT pg_has_role(CAST(:operating AS name), "
                        "CAST(:migration AS name), 'MEMBER')"
                    ),
                    {"operating": operating_username, "migration": owner_role},
                ).scalar_one()
                owns_schema_objects = connection.execute(
                    text(
                        "SELECT EXISTS (SELECT 1 FROM pg_class AS c "
                        "JOIN pg_namespace AS n ON n.oid = c.relnamespace "
                        "WHERE n.nspname = 'public' AND c.relowner = "
                        "(SELECT oid FROM pg_roles WHERE rolname = :role))"
                    ),
                    {"role": operating_username},
                ).scalar_one()
                database_create = connection.execute(
                    text(
                        "SELECT has_database_privilege(:role, current_database(), 'CREATE')"
                    ),
                    {"role": operating_username},
                ).scalar_one()
                schema_create = connection.execute(
                    text("SELECT has_schema_privilege(:role, 'public', 'CREATE')"),
                    {"role": operating_username},
                ).scalar_one()
                if (
                    is_migration_member
                    or owns_schema_objects
                    or database_create
                    or schema_create
                ):
                    raise ValueError(
                        "Die vorhandene Betriebsrolle besitzt Eigentümer-, "
                        "Migrations- oder Schemaänderungsrechte."
                    )
                alembic_dml = connection.execute(
                    text(
                        "SELECT has_table_privilege(:role, 'public.alembic_version', 'INSERT') "
                        "OR has_table_privilege(:role, 'public.alembic_version', 'UPDATE') "
                        "OR has_table_privilege(:role, 'public.alembic_version', 'DELETE')"
                    ),
                    {"role": operating_username},
                ).scalar_one()
                if alembic_dml:
                    raise ValueError(
                        "Die vorhandene Betriebsrolle besitzt bereits "
                        "Änderungsrechte auf alembic_version und ist dafür nicht geeignet."
                    )
        finally:
            engine.dispose()

    @staticmethod
    def _grant_operating_access(
        *, url, owner_credentials, owner_role, operating_username
    ) -> None:
        engine = create_engine(
            url,
            hide_parameters=True,
            connect_args=database_connect_args(
                url.render_as_string(hide_password=True), owner_credentials
            ),
        )
        try:
            with engine.begin() as connection:
                actual_database, actual_role = connection.execute(
                    text("SELECT current_database(), current_user")
                ).one()
                if actual_database != url.database or actual_role != owner_role:
                    raise RuntimeError(
                        "Die Rechtevergabe verwendet nicht die erwartete "
                        "Datenbank- und Eigentümerrolle."
                    )
                quote = connection.dialect.identifier_preparer.quote_identifier
                role = quote(operating_username)
                database = quote(url.database)
                connection.exec_driver_sql(
                    f"GRANT CONNECT ON DATABASE {database} TO {role}"
                )
                connection.exec_driver_sql(f"GRANT USAGE ON SCHEMA public TO {role}")
                connection.exec_driver_sql(
                    f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {role}"
                )
                grant_application_table_privileges(
                    connection,
                    operating_role=operating_username,
                    table_names=models.Base.metadata.tables,
                )
                enforce_read_only_alembic_version(
                    connection,
                    operating_role=operating_username,
                )
                default_privileges = (
                    f"ALTER DEFAULT PRIVILEGES FOR ROLE {quote(owner_role)} "
                    f"IN SCHEMA public"
                )
                connection.exec_driver_sql(
                    f"{default_privileges} GRANT SELECT, INSERT, UPDATE, DELETE "
                    f"ON TABLES TO {role}"
                )
                connection.exec_driver_sql(
                    f"{default_privileges} GRANT USAGE, SELECT ON SEQUENCES TO {role}"
                )
        finally:
            engine.dispose()
