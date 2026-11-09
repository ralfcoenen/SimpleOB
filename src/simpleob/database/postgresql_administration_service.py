"""Administrative Prüfungen für PostgreSQL-Datenbanken."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, make_url

from simpleob.core.config import ApplicationConfig
from simpleob.database import models
from simpleob.database.connection_credentials import (
    PostgreSQLCredentials,
    database_connect_args,
)
from simpleob.database.migration_service import (
    _ADMIN_POSTGRESQL_UPGRADE_AUTHORIZATION,
    DatabaseMigrationService,
    PostgreSQLSchemaInspection,
    PostgreSQLSchemaStatus,
)
from simpleob.database.postgresql_backup_service import (
    PostgreSQLBackupService,
)
from simpleob.database.postgresql_existing_installation_inspector import (
    PostgreSQLExistingInstallationInspector,
    PostgreSQLOwnershipAssessment,
)
from simpleob.database.postgresql_maintenance_isolation import (
    postgresql_maintenance_isolation,
)
from simpleob.database.postgresql_migration_lock import (
    postgresql_migration_lock,
)
from simpleob.database.postgresql_migration_safety import (
    PostgreSQLMigrationAction,
    PostgreSQLMigrationApproval,
    validate_postgresql_migration,
)
from simpleob.database.postgresql_restore_verification import (
    PostgreSQLRestoreVerificationService,
)
from simpleob.database.postgresql_session_inspection import (
    inspect_postgresql_sessions,
)


@dataclass(frozen=True, slots=True)
class PostgreSQLMigrationDryRunResult:
    """Ergebnis eines administrativen Probelaufs."""

    action: PostgreSQLMigrationAction
    backup_path: Path | None
    backup_size: int
    restored_table_count: int


class PostgreSQLAdministrationService:
    """Prüft PostgreSQL unter einer exklusiven Migrationssperre."""

    def __init__(
        self,
        *,
        application_config: ApplicationConfig,
        credentials: PostgreSQLCredentials | None = None,
        operating_username: str | None = None,
        operating_credentials: PostgreSQLCredentials | None = None,
        migration_username: str | None = None,
        migration_credentials: PostgreSQLCredentials | None = None,
        admin_username: str | None = None,
        admin_credentials: PostgreSQLCredentials | None = None,
    ) -> None:
        self._application_config = application_config
        configured_username = make_url(application_config.database_url).username
        self._credentials = credentials
        self._operating_username = operating_username or configured_username
        self._operating_credentials = operating_credentials or credentials
        self._migration_username = migration_username or configured_username
        self._migration_credentials = migration_credentials or credentials
        self._admin_username = admin_username or configured_username
        self._admin_credentials = admin_credentials or credentials
        self._explicit_split_roles = any(
            value is not None
            for value in (
                operating_username,
                operating_credentials,
                migration_username,
                migration_credentials,
                admin_username,
                admin_credentials,
            )
        )
        self._operating_config = self._config_for_role(
            application_config,
            self._operating_username,
        )
        self._migration_config = self._config_for_role(
            application_config,
            self._migration_username,
        )
        self._admin_config = self._config_for_role(
            application_config,
            self._admin_username,
        )
        self._migration_service = DatabaseMigrationService(
            application_config=self._migration_config,
            credentials=self._migration_credentials,
        )

    @staticmethod
    def _config_for_role(
        application_config: ApplicationConfig,
        username: str | None,
    ) -> ApplicationConfig:
        current_url = make_url(application_config.database_url)
        if not username or current_url.username == username:
            return application_config
        url = current_url.set(
            username=username,
            password=None,
        )
        return replace(
            application_config,
            database_url_override=url.render_as_string(hide_password=True),
        )

    def _create_engine(
        self,
        database_url: str | URL,
        *,
        role: str = "operating",
        isolation_level: str | None = None,
    ):
        url = make_url(database_url)
        username = getattr(self, f"_{role}_username")
        credentials = getattr(self, f"_{role}_credentials")
        if username:
            url = url.set(username=username)
        if credentials is not None:
            url = url.set(password=None)
        options = {
            "connect_args": database_connect_args(
                url.render_as_string(hide_password=True),
                credentials,
            )
        }
        if isolation_level is not None:
            options["isolation_level"] = isolation_level
        return create_engine(url, **options)

    @staticmethod
    def _require_confirmed_database(
        url: URL,
        operation: str,
        approval: PostgreSQLMigrationApproval,
    ) -> str:
        target_database = approval.confirmed_database_name
        if url.get_backend_name() != "postgresql":
            raise ValueError(f"{operation} ist nur für PostgreSQL vorgesehen.")
        if (
            not target_database
            or url.database != target_database
            or target_database in {"postgres", "template0", "template1"}
            or url.password is not None
        ):
            raise ValueError(
                f"{operation} erfordert eine ausdrücklich bestätigte "
                "SimpleOB-Zieldatenbank ohne Passwort in der URL."
            )
        return target_database

    def _validate_split_upgrade_roles(
        self,
        *,
        url: URL,
        admin_connection,
        migration_connection,
        operating_assessment,
    ) -> None:
        """Verifiziert Rollen, Eigentümerschaft und Rechte vor dem Upgrade."""
        if not all(
            (
                self._operating_username,
                self._migration_username,
                self._admin_username,
                isinstance(self._operating_credentials, PostgreSQLCredentials),
                isinstance(self._migration_credentials, PostgreSQLCredentials),
                isinstance(self._admin_credentials, PostgreSQLCredentials),
            )
        ):
            raise RuntimeError(
                "Für ein Upgrade mit getrennten Rollen müssen Betriebs-, "
                "Migrations- und Administrationszugang ausdrücklich bereitstehen."
            )
        if len(
            {
                self._operating_username,
                self._migration_username,
                self._admin_username,
            }
        ) < 2:
            raise RuntimeError(
                "Betriebs- und Migrationsrolle müssen getrennte Rollen sein."
            )

        admin_flags = admin_connection.execute(
            text(
                "SELECT r.rolsuper, r.rolcreatedb, "
                "pg_has_role(current_user, 'pg_read_all_stats', 'USAGE') "
                "AS can_read_all_stats FROM pg_roles AS r "
                "WHERE r.rolname = current_user"
            )
        ).one_or_none()
        if admin_flags is None or (
            not admin_flags.rolsuper and not admin_flags.rolcreatedb
        ):
            raise RuntimeError(
                "Die Administrationsrolle benötigt CREATEDB oder SUPERUSER, "
                "um die Wiederherstellungsprobe anzulegen und zu bereinigen."
            )
        if not admin_flags.rolsuper and not admin_flags.can_read_all_stats:
            raise RuntimeError(
                "Die Administrationsrolle benötigt SUPERUSER oder Mitgliedschaft "
                "in pg_read_all_stats, damit konkurrierende Sitzungen vollständig "
                "erkannt werden."
            )

        actual_database, actual_role, database_owner = migration_connection.execute(
            text(
                "SELECT current_database(), current_user, "
                "pg_get_userbyid(datdba) FROM pg_database "
                "WHERE datname = current_database()"
            )
        ).one()
        if (
            actual_database != url.database
            or actual_role != self._migration_username
            or database_owner != self._migration_username
        ):
            raise RuntimeError(
                "Die Migrationsverbindung ist nicht mit der Eigentümerrolle "
                "der Testdatenbank verbunden."
            )
        can_create_in_schema = migration_connection.execute(
            text("SELECT has_schema_privilege(current_user, 'public', 'CREATE')")
        ).scalar_one()
        if not can_create_in_schema:
            raise RuntimeError(
                "Die Migrationsrolle darf im public-Schema keine Objekte anlegen."
            )

        assessment = operating_assessment
        missing_table_blockers = tuple(
            blocker
            for blocker in assessment.blockers
            if blocker.startswith("SimpleOB-Tabellen fehlen:")
        )
        ownership_candidate_matches = (
            assessment.migration_role_candidate == self._migration_username
            or (
                assessment.schema_status == PostgreSQLSchemaStatus.OUTDATED
                and assessment.migration_role_candidate is None
                and bool(missing_table_blockers)
            )
        )
        if (
            assessment.operating_role != self._operating_username
            or not ownership_candidate_matches
            or assessment.database_owner != self._migration_username
            or assessment.schema_status
            not in (
                PostgreSQLSchemaStatus.CURRENT,
                PostgreSQLSchemaStatus.OUTDATED,
            )
            or any(
                blocker not in missing_table_blockers for blocker in assessment.blockers
            )
            or not assessment.alembic_version_privileges
        ):
            raise RuntimeError(
                "Die Bestandsprüfung bestätigt keine passende Eigentümerschaft "
                "oder Rollenaufteilung. Das Upgrade wurde nicht gestartet. "
                + " ".join(assessment.blockers)
            )
        if assessment.schema_owner not in {
            self._migration_username,
            "pg_database_owner",
        }:
            raise RuntimeError(
                "Das public-Schema gehört weder der Migrationsrolle noch "
                "pg_database_owner."
            )
        if not assessment.alembic_version_owner == self._migration_username:
            raise RuntimeError(
                "Die Migrationsrolle ist nicht Eigentümerin von alembic_version."
            )
        self._verify_migration_object_ownership(
            migration_connection,
            migration_role=self._migration_username,
        )
        runtime = next(
            (
                item
                for item in assessment.role_privileges
                if item.role == self._operating_username
            ),
            None,
        )
        if (
            runtime is None
            or not runtime.database_connect
            or not runtime.schema_usage
            or runtime.database_create
            or runtime.schema_create
            or any(
                not allowed
                for table, privilege, allowed in runtime.table_privileges
                if table != "alembic_version" or privilege == "SELECT"
            )
            or any(not allowed for _, _, allowed in runtime.sequence_privileges)
        ):
            raise RuntimeError(
                "Die Betriebsrolle besitzt nicht die erforderlichen, "
                "beschränkten Zugriffsrechte für das vorhandene Schema."
            )
        required_table_defaults = {"SELECT", "INSERT", "UPDATE", "DELETE"}
        required_sequence_defaults = {"USAGE", "SELECT"}
        table_defaults = {
            item.privilege
            for item in assessment.default_privileges
            if item.owner_role == self._migration_username
            and item.schema_name in {"public", "*"}
            and item.object_type == "r"
            and item.grantee == self._operating_username
        }
        sequence_defaults = {
            item.privilege
            for item in assessment.default_privileges
            if item.owner_role == self._migration_username
            and item.schema_name in {"public", "*"}
            and item.object_type == "S"
            and item.grantee == self._operating_username
        }
        if not required_table_defaults.issubset(table_defaults) or not (
            required_sequence_defaults.issubset(sequence_defaults)
        ):
            raise RuntimeError(
                "Default Privileges für von Alembic neu angelegte Tabellen "
                "oder Sequenzen fehlen."
            )
        alembic_privileges = dict(assessment.alembic_version_privileges)
        if not alembic_privileges.get("SELECT") or any(
            alembic_privileges.get(privilege, False)
            for privilege in ("INSERT", "UPDATE", "DELETE")
        ):
            raise RuntimeError(
                "Die Betriebsrolle muss alembic_version lesen, darf sie aber "
                "nicht ändern können."
            )

    def _verify_migration_object_ownership(
        self,
        connection,
        *,
        migration_role: str,
    ) -> None:
        rows = connection.execute(
            text(
                "SELECT c.relname, c.relkind, pg_get_userbyid(c.relowner) AS owner, "
                "tbl.relname AS owning_table FROM pg_class AS c "
                "JOIN pg_namespace AS n ON n.oid = c.relnamespace "
                "LEFT JOIN pg_depend AS dep ON dep.objid = c.oid "
                "AND dep.classid = 'pg_class'::regclass "
                "AND dep.refclassid = 'pg_class'::regclass "
                "AND dep.deptype IN ('a', 'i') "
                "LEFT JOIN pg_class AS tbl ON tbl.oid = dep.refobjid "
                "WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p', 'S')"
            )
        ).all()
        known_tables = set(models.Base.metadata.tables) | {"alembic_version"}
        unexpected_tables = sorted(
            row.relname
            for row in rows
            if row.relkind in {"r", "p"} and row.relname not in known_tables
        )
        if unexpected_tables:
            raise RuntimeError(
                "Das public-Schema enthält nicht zu SimpleOB gehörende oder "
                "unbekannte Tabellen; Upgrade abgebrochen: "
                + ", ".join(unexpected_tables)
            )
        invalid_objects = sorted(
            row.relname
            for row in rows
            if row.owner != migration_role
            or (row.relkind == "S" and row.owning_table not in known_tables)
        )
        if invalid_objects:
            raise RuntimeError(
                "Nicht alle Upgradeobjekte gehören der Migrationsrolle: "
                + ", ".join(invalid_objects)
            )

    def _validate_admin_capabilities(
        self,
        *,
        admin_connection,
        session_connection,
        target_database: str,
    ) -> None:
        (
            admin_database,
            admin_role,
            is_superuser,
            can_create_database,
            can_read_stats,
        ) = admin_connection.execute(
            text(
                "SELECT current_database(), current_user, r.rolsuper, "
                "r.rolcreatedb, pg_has_role(current_user, "
                "'pg_read_all_stats', 'USAGE') "
                "FROM pg_roles AS r WHERE r.rolname = current_user"
            )
        ).one()
        if admin_database != "postgres" or admin_role != self._admin_username:
            raise RuntimeError(
                "Die Administrationsverbindung verwendet nicht die erwartete "
                "Rolle auf der Datenbank postgres."
            )
        if not is_superuser and not can_create_database:
            raise RuntimeError(
                "Die Administrationsrolle benötigt CREATEDB oder SUPERUSER, "
                "um die Wiederherstellungsprobe anzulegen und zu bereinigen."
            )
        if not is_superuser and not can_read_stats:
            raise RuntimeError(
                "Die Administrationsrolle benötigt SUPERUSER oder Mitgliedschaft "
                "in pg_read_all_stats, damit aktive Sitzungen vollständig erkannt werden."
            )
        session_database, session_role = session_connection.execute(
            text("SELECT current_database(), current_user")
        ).one()
        if (
            session_database != target_database
            or session_role != self._admin_username
        ):
            raise RuntimeError(
                "Die Sitzungsprüfung verwendet nicht die Administrationsrolle "
                f"auf {target_database}."
            )

    def inspect_schema(
        self,
    ) -> PostgreSQLSchemaInspection:
        """Prüft das Schema unter einer administrativen PostgreSQL-Sperre.

        Die exklusive Sperre wird über die Datenbank 'postgres'
        gehalten. Die Schemaprüfung erfolgt über die eigentliche
        Anwendungsdatenbank.

        Andere Sitzungen und unbekannte Schemazustände
        führen zum Abbruch. Es erfolgt keine Migration.
        """
        database_url = self._application_config.database_url
        url = make_url(database_url)

        if url.get_backend_name() != "postgresql":
            raise ValueError(
                "Die administrative Schemaprüfung ist nur für PostgreSQL vorgesehen."
            )

        admin_engine = self._create_engine(url.set(database="postgres"), role="admin")
        database_engine = self._create_engine(database_url, role="operating")

        try:
            with admin_engine.connect() as admin_connection:
                with postgresql_migration_lock(admin_connection):
                    with database_engine.connect() as connection:
                        sessions = inspect_postgresql_sessions(connection)

                        if sessions.has_other_sessions:
                            raise RuntimeError(
                                "Die PostgreSQL-Datenbank wird noch "
                                "von anderen Sitzungen verwendet "
                                f"({sessions.other_session_count}). "
                                "Bitte alle anderen Datenbankverbindungen "
                                "vor der administrativen Wartung beenden."
                            )

                        inspection = self._migration_service.inspect_postgresql_schema_on_connection(
                            connection
                        )

                        if inspection.status == PostgreSQLSchemaStatus.UNKNOWN:
                            raise RuntimeError(
                                "Der PostgreSQL-Schemazustand ist unbekannt. "
                                "Eine administrative Migration "
                                "ist nicht zulässig."
                            )

                        return inspection
        finally:
            database_engine.dispose()
            admin_engine.dispose()

    def prepare_migration(
        self,
        *,
        approval: PostgreSQLMigrationApproval,
    ) -> PostgreSQLMigrationAction:
        """Prüft die Voraussetzungen einer administrativen Migration.

        Die Prüfungen erfolgen unter einer exklusiven
        PostgreSQL-Migrationssperre.

        Es werden keine Migrationen ausgeführt. Die zurückgegebene
        Aktion ist keine dauerhaft gültige Freigabe.
        """
        database_url = self._application_config.database_url
        self._require_confirmed_database(
            make_url(database_url), "Die administrative Migrationsvorbereitung", approval
        )

        if make_url(database_url).get_backend_name() != "postgresql":
            raise ValueError(
                "Die administrative Migrationsvorbereitung "
                "ist nur für PostgreSQL vorgesehen."
            )

        admin_engine = self._create_engine(
            make_url(database_url).set(database="postgres"), role="admin"
        )
        database_engine = self._create_engine(database_url, role="operating")

        try:
            with admin_engine.connect() as admin_connection:
                with postgresql_migration_lock(admin_connection):
                    with database_engine.connect() as connection:
                        sessions = inspect_postgresql_sessions(connection)

                        if sessions.has_other_sessions:
                            raise RuntimeError(
                                "Die PostgreSQL-Datenbank wird noch "
                                "von anderen Sitzungen verwendet "
                                f"({sessions.other_session_count}). "
                                "Bitte alle anderen Datenbankverbindungen "
                                "vor der administrativen Wartung beenden."
                            )

                        inspection = self._migration_service.inspect_postgresql_schema_on_connection(
                            connection
                        )

                        return validate_postgresql_migration(
                            inspection=inspection,
                            approval=approval,
                        )
        finally:
            database_engine.dispose()
            admin_engine.dispose()

    def run_migration_dry_run(
        self,
        *,
        approval: PostgreSQLMigrationApproval,
        backup_path: Path,
    ) -> PostgreSQLMigrationDryRunResult:
        """Prüft den administrativen Ablauf ohne Migration."""
        database_url = make_url(self._application_config.database_url)
        target_database = self._require_confirmed_database(
            database_url, "Der administrative Probelauf", approval
        )

        admin_engine = self._create_engine(
            database_url.set(database="postgres"), role="admin"
        )
        database_engine = self._create_engine(
            self._application_config.database_url, role="operating"
        )

        try:
            with admin_engine.connect() as admin_connection:
                with postgresql_migration_lock(admin_connection):
                    with database_engine.connect() as connection:
                        sessions = inspect_postgresql_sessions(connection)

                        if sessions.has_other_sessions:
                            raise RuntimeError(
                                "Der Probelauf wurde abgebrochen: "
                                "Weitere PostgreSQL-Sitzungen sind aktiv."
                            )

                        inspection = self._migration_service.inspect_postgresql_schema_on_connection(
                            connection
                        )

                        # Für OUTDATED wird die frisch zu erzeugende
                        # Sicherung erst nach erfolgreicher Prüfung
                        # als Backup-Nachweis verwendet.
                        if inspection.status == PostgreSQLSchemaStatus.OUTDATED:
                            if not approval.migration_confirmed:
                                raise RuntimeError(
                                    "Die Migration muss ausdrücklich bestätigt werden."
                                )

                            if not approval.maintenance_confirmed:
                                raise RuntimeError(
                                    "Der Wartungsbetrieb muss "
                                    "ausdrücklich bestätigt werden."
                                )

                        else:
                            validate_postgresql_migration(
                                inspection=inspection,
                                approval=approval,
                            )

                        backup_result = PostgreSQLBackupService(
                            application_config=self._operating_config,
                            credentials=self._operating_credentials,
                        ).create_backup(backup_path=backup_path)

                        restore_result = PostgreSQLRestoreVerificationService(
                            application_config=self._admin_config,
                            credentials=self._admin_credentials,
                        ).verify_backup(
                            backup_path=backup_result.backup_path,
                            confirmed_source_database=target_database,
                        )

                        effective_approval = PostgreSQLMigrationApproval(
                            initialize_confirmed=(approval.initialize_confirmed),
                            migration_confirmed=(approval.migration_confirmed),
                            maintenance_confirmed=(approval.maintenance_confirmed),
                            confirmed_database_name=approval.confirmed_database_name,
                            backup_path=backup_result.backup_path,
                        )

                        action = validate_postgresql_migration(
                            inspection=inspection,
                            approval=effective_approval,
                        )

                        return PostgreSQLMigrationDryRunResult(
                            action=action,
                            backup_path=backup_result.backup_path,
                            backup_size=backup_result.backup_size,
                            restored_table_count=(restore_result.restored_table_count),
                        )
        finally:
            database_engine.dispose()
            admin_engine.dispose()

    def verify_maintenance_isolation(
        self,
        *,
        confirmed_database_name: str,
    ) -> None:
        """Prüft die Wartungsisolierung ohne Schemaänderungen.

        Die administrative Sperre wird während der gesamten
        Prüfung auf der Datenbank 'postgres' gehalten.
        """
        url = make_url(self._application_config.database_url)
        approval = PostgreSQLMigrationApproval(
            confirmed_database_name=confirmed_database_name
        )
        target_database = self._require_confirmed_database(
            url, "Die Prüfung der Wartungsisolierung", approval
        )
        admin_engine = self._create_engine(
            url.set(database="postgres"),
            role="admin",
            isolation_level="AUTOCOMMIT",
        )
        owner_admin_engine = self._create_engine(
            url.set(database="postgres", username=self._migration_username),
            role="migration",
            isolation_level="AUTOCOMMIT",
        )
        migration_engine = self._create_engine(
            url.set(username=self._migration_username), role="migration"
        )
        monitor_engine = self._create_engine(
            url.set(username=self._admin_username), role="admin"
        )
        operating_engine = self._create_engine(
            url.set(username=self._operating_username), role="operating"
        )

        try:
            with admin_engine.connect() as admin_connection:
                with postgresql_migration_lock(admin_connection):
                    with owner_admin_engine.connect() as owner_admin_connection:
                        with migration_engine.connect() as migration_connection:
                            with monitor_engine.connect() as monitor_connection:
                                if self._explicit_split_roles:
                                    self._validate_admin_capabilities(
                                        admin_connection=admin_connection,
                                        session_connection=monitor_connection,
                                        target_database=target_database,
                                    )
                                with postgresql_maintenance_isolation(
                                    application_config=self._migration_config,
                                    target_database=target_database,
                                    admin_connection=admin_connection,
                                    migration_connection=migration_connection,
                                    migration_owner_connection=(
                                        owner_admin_connection
                                        if self._explicit_split_roles
                                        else None
                                    ),
                                    session_inspection_connection=monitor_connection,
                                ):
                                    if (
                                        migration_connection.execute(
                                            text("SELECT current_database()")
                                        ).scalar_one()
                                        != target_database
                                    ):
                                        raise RuntimeError(
                                            "Die Migrationsverbindung verweist "
                                            "auf eine unerwartete Datenbank."
                                        )

            # Der Betriebszugang muss nach Freigabe wieder funktionieren.
            with operating_engine.connect() as connection:
                connection.execute(text("SELECT 1")).scalar_one()
        finally:
            operating_engine.dispose()
            monitor_engine.dispose()
            migration_engine.dispose()
            owner_admin_engine.dispose()
            admin_engine.dispose()

    def run_maintenance_dry_run(
        self,
        *,
        approval: PostgreSQLMigrationApproval,
        backup_path: Path,
    ) -> PostgreSQLMigrationDryRunResult:
        """Prüft Rollen, Backup, Restore und Wartung ohne Alembic-Änderung."""
        url = make_url(self._application_config.database_url)
        target_database = self._require_confirmed_database(
            url, "Der Wartungsprobelauf", approval
        )
        admin_engine = self._create_engine(
            url.set(database="postgres", username=self._admin_username),
            role="admin",
            isolation_level="AUTOCOMMIT",
        )
        owner_admin_engine = self._create_engine(
            url.set(database="postgres", username=self._migration_username),
            role="migration",
            isolation_level="AUTOCOMMIT",
        )
        migration_engine = self._create_engine(
            url.set(username=self._migration_username), role="migration"
        )
        monitor_engine = self._create_engine(
            url.set(username=self._admin_username), role="admin"
        )

        try:
            with admin_engine.connect() as admin_connection:
                with postgresql_migration_lock(admin_connection):
                    with owner_admin_engine.connect() as owner_admin_connection:
                        with migration_engine.connect() as migration_connection:
                            with monitor_engine.connect() as monitor_connection:
                                if self._explicit_split_roles:
                                    self._validate_admin_capabilities(
                                        admin_connection=admin_connection,
                                        session_connection=monitor_connection,
                                        target_database=target_database,
                                    )
                                    assessment = (
                                        PostgreSQLExistingInstallationInspector(
                                            application_config=self._operating_config,
                                            credentials=self._operating_credentials,
                                        ).inspect()
                                    )
                                    self._validate_split_upgrade_roles(
                                        url=url,
                                        admin_connection=admin_connection,
                                        migration_connection=migration_connection,
                                        operating_assessment=assessment,
                                    )

                                migration_pid = int(
                                    migration_connection.execute(
                                        text("SELECT pg_backend_pid()")
                                    ).scalar_one()
                                )
                                if inspect_postgresql_sessions(
                                    monitor_connection,
                                    excluded_pids=(migration_pid,),
                                ).has_other_sessions:
                                    raise RuntimeError(
                                        "Der Wartungsprobelauf wurde abgebrochen: "
                                        "Weitere PostgreSQL-Sitzungen sind aktiv."
                                    )

                                inspection = self._migration_service.inspect_postgresql_schema_on_connection(
                                    migration_connection
                                )
                                if inspection.status == PostgreSQLSchemaStatus.OUTDATED:
                                    if not approval.migration_confirmed:
                                        raise RuntimeError(
                                            "Die Migration muss ausdrücklich bestätigt werden."
                                        )
                                    if not approval.maintenance_confirmed:
                                        raise RuntimeError(
                                            "Der Wartungsbetrieb muss ausdrücklich bestätigt werden."
                                        )
                                else:
                                    validate_postgresql_migration(
                                        inspection=inspection,
                                        approval=approval,
                                    )

                                backup_result = PostgreSQLBackupService(
                                    application_config=self._operating_config,
                                    credentials=self._operating_credentials,
                                ).create_backup(backup_path=backup_path)
                                restore_result = PostgreSQLRestoreVerificationService(
                                    application_config=self._admin_config,
                                    credentials=self._admin_credentials,
                                ).verify_backup(
                                    backup_path=backup_result.backup_path,
                                    confirmed_source_database=target_database,
                                )
                                effective_approval = PostgreSQLMigrationApproval(
                                    initialize_confirmed=approval.initialize_confirmed,
                                    migration_confirmed=approval.migration_confirmed,
                                    maintenance_confirmed=approval.maintenance_confirmed,
                                    confirmed_database_name=approval.confirmed_database_name,
                                    backup_path=backup_result.backup_path,
                                )
                                action = validate_postgresql_migration(
                                    inspection=inspection,
                                    approval=effective_approval,
                                )

                                migration_connection.rollback()
                                with postgresql_maintenance_isolation(
                                    application_config=self._migration_config,
                                    target_database=target_database,
                                    admin_connection=admin_connection,
                                    migration_connection=migration_connection,
                                    migration_owner_connection=(
                                        owner_admin_connection
                                        if self._explicit_split_roles
                                        else None
                                    ),
                                    session_inspection_connection=monitor_connection,
                                ):
                                    current_inspection = self._migration_service.inspect_postgresql_schema_on_connection(
                                        migration_connection
                                    )
                                    if current_inspection != inspection:
                                        raise RuntimeError(
                                            "Der PostgreSQL-Schemazustand hat sich "
                                            "während der Vorbereitung verändert."
                                        )
                                    migration_connection.rollback()

                                return PostgreSQLMigrationDryRunResult(
                                    action=action,
                                    backup_path=backup_result.backup_path,
                                    backup_size=backup_result.backup_size,
                                    restored_table_count=restore_result.restored_table_count,
                                )
        finally:
            monitor_engine.dispose()
            migration_engine.dispose()
            owner_admin_engine.dispose()
            admin_engine.dispose()

    def _execute_migration_on_connection(
        self, migration_connection, target_database: str
    ) -> None:
        """Ruft den internen Alembic-Pfad nach den Adminprüfungen auf."""
        migration_connection.rollback()

        try:
            with migration_connection.begin():
                self._migration_service._upgrade_postgresql_on_connection(
                    migration_connection,
                    target_database=target_database,
                    authorization=_ADMIN_POSTGRESQL_UPGRADE_AUTHORIZATION,
                )
        except Exception:
            migration_connection.rollback()
            raise

    def execute_migration(
        self,
        *,
        approval: PostgreSQLMigrationApproval,
        backup_path: Path,
    ) -> PostgreSQLMigrationDryRunResult:
        """Führt eine ausdrücklich freigegebene PostgreSQL-Migration aus."""
        url = make_url(self._application_config.database_url)
        target_database = self._require_confirmed_database(
            url, "Die administrative Migration", approval
        )
        if not all(
            (self._operating_username, self._migration_username, self._admin_username)
        ):
            raise ValueError("Die PostgreSQL-Rollen sind nicht vollständig angegeben.")

        admin_engine = self._create_engine(
            url.set(database="postgres", username=self._admin_username),
            role="admin",
            isolation_level="AUTOCOMMIT",
        )
        owner_admin_engine = self._create_engine(
            url.set(database="postgres", username=self._migration_username),
            role="migration",
            isolation_level="AUTOCOMMIT",
        )
        migration_engine = self._create_engine(
            url.set(username=self._migration_username), role="migration"
        )
        monitor_engine = self._create_engine(
            url.set(username=self._admin_username), role="admin"
        )

        try:
            with admin_engine.connect() as admin_connection:
                with postgresql_migration_lock(admin_connection):
                    with owner_admin_engine.connect() as owner_admin_connection:
                        with migration_engine.connect() as migration_connection:
                            with monitor_engine.connect() as monitor_connection:
                                if self._explicit_split_roles:
                                    self._validate_admin_capabilities(
                                        admin_connection=admin_connection,
                                        session_connection=monitor_connection,
                                        target_database=target_database,
                                    )
                                    operating_assessment = (
                                        PostgreSQLExistingInstallationInspector(
                                            application_config=self._operating_config,
                                            credentials=self._operating_credentials,
                                        ).inspect()
                                    )
                                    self._validate_split_upgrade_roles(
                                        url=url,
                                        admin_connection=admin_connection,
                                        migration_connection=migration_connection,
                                        operating_assessment=operating_assessment,
                                    )

                                migration_pid = int(
                                    migration_connection.execute(
                                        text("SELECT pg_backend_pid()")
                                    ).scalar_one()
                                )
                                sessions = inspect_postgresql_sessions(
                                    monitor_connection,
                                    excluded_pids=(migration_pid,),
                                )
                                if sessions.has_other_sessions:
                                    raise RuntimeError(
                                        "Die administrative Migration wurde "
                                        "abgebrochen: Weitere PostgreSQL-Sitzungen "
                                        "sind aktiv."
                                    )

                                inspection = self._migration_service.inspect_postgresql_schema_on_connection(
                                    migration_connection
                                )
                                if inspection.status == PostgreSQLSchemaStatus.UNKNOWN:
                                    raise RuntimeError(
                                        "Der Alembic-Revisionsstand ist unbekannt. "
                                        "Die Migration wurde nicht gestartet."
                                    )
                                if inspection.status == PostgreSQLSchemaStatus.OUTDATED:
                                    if not approval.migration_confirmed:
                                        raise RuntimeError(
                                            "Die Migration muss ausdrücklich bestätigt werden."
                                        )
                                else:
                                    validate_postgresql_migration(
                                        inspection=inspection,
                                        approval=approval,
                                    )
                                if (
                                    inspection.status
                                    in (
                                        PostgreSQLSchemaStatus.EMPTY,
                                        PostgreSQLSchemaStatus.OUTDATED,
                                    )
                                    and not approval.maintenance_confirmed
                                ):
                                    raise RuntimeError(
                                        "Der Wartungsbetrieb muss ausdrücklich bestätigt werden."
                                    )
                                if inspection.status == PostgreSQLSchemaStatus.CURRENT:
                                    return PostgreSQLMigrationDryRunResult(
                                        action=PostgreSQLMigrationAction.NONE,
                                        backup_path=None,
                                        backup_size=0,
                                        restored_table_count=0,
                                    )

                                if not self._explicit_split_roles:
                                    raise RuntimeError(
                                        "Ein administratives Upgrade benötigt "
                                        "ausdrücklich getrennte Betriebs-, "
                                        "Migrations- und Administrationsrollen."
                                    )

                                backup_result = PostgreSQLBackupService(
                                    application_config=self._operating_config,
                                    credentials=self._operating_credentials,
                                ).create_backup(backup_path=backup_path)
                                try:
                                    restore_result = (
                                        PostgreSQLRestoreVerificationService(
                                            application_config=self._admin_config,
                                            credentials=self._admin_credentials,
                                        ).verify_backup(
                                            backup_path=backup_result.backup_path,
                                            confirmed_source_database=target_database,
                                        )
                                    )
                                except Exception:
                                    # Kein Wartungszustand und keine Alembic-
                                    # Änderung vor einer bestätigten Restore-Probe.
                                    raise

                                action = validate_postgresql_migration(
                                    inspection=inspection,
                                    approval=PostgreSQLMigrationApproval(
                                        initialize_confirmed=approval.initialize_confirmed,
                                        migration_confirmed=approval.migration_confirmed,
                                        maintenance_confirmed=approval.maintenance_confirmed,
                                        confirmed_database_name=approval.confirmed_database_name,
                                        backup_path=backup_result.backup_path,
                                    ),
                                )
                                migration_connection.rollback()
                                with postgresql_maintenance_isolation(
                                    application_config=self._migration_config,
                                    target_database=target_database,
                                    admin_connection=admin_connection,
                                    migration_connection=migration_connection,
                                    migration_owner_connection=(
                                        owner_admin_connection
                                        if self._explicit_split_roles
                                        else None
                                    ),
                                    session_inspection_connection=monitor_connection,
                                ):
                                    current_inspection = self._migration_service.inspect_postgresql_schema_on_connection(
                                        migration_connection
                                    )
                                    if current_inspection != inspection:
                                        raise RuntimeError(
                                            "Der PostgreSQL-Schemazustand hat sich "
                                            "während der Vorbereitung verändert."
                                        )
                                    migration_connection.rollback()
                                    self._execute_migration_on_connection(
                                        migration_connection,
                                        target_database,
                                    )
                                    final_inspection = self._migration_service.inspect_postgresql_schema_on_connection(
                                        migration_connection
                                    )
                                    if (
                                        final_inspection.status
                                        != PostgreSQLSchemaStatus.CURRENT
                                        or final_inspection.current_revision
                                        != final_inspection.head_revision
                                    ):
                                        raise RuntimeError(
                                            "Die PostgreSQL-Migration hat nicht "
                                            "den erwarteten Alembic-Head erreicht."
                                        )
                                    migration_connection.rollback()

                                if self._explicit_split_roles:
                                    DatabaseMigrationService(
                                        application_config=self._operating_config,
                                        credentials=self._operating_credentials,
                                    ).check_ready_for_start()
                                    final_assessment = (
                                        PostgreSQLExistingInstallationInspector(
                                            application_config=self._operating_config,
                                            credentials=self._operating_credentials,
                                        ).inspect()
                                    )
                                    if (
                                        final_assessment.ownership_assessment
                                        != PostgreSQLOwnershipAssessment.SPLIT_ROLES_COMPATIBLE
                                        or final_assessment.migration_role_candidate
                                        != self._migration_username
                                        or final_assessment.schema_status
                                        != PostgreSQLSchemaStatus.CURRENT
                                        or final_assessment.blockers
                                    ):
                                        raise RuntimeError(
                                            "Das Upgrade war erfolgreich, aber die "
                                            "Betriebsrechte nach der Migration sind "
                                            "nicht vollständig. Die Anwendung darf "
                                            "noch nicht mit der Betriebsrolle starten."
                                        )

                                return PostgreSQLMigrationDryRunResult(
                                    action=action,
                                    backup_path=backup_result.backup_path,
                                    backup_size=backup_result.backup_size,
                                    restored_table_count=(
                                        restore_result.restored_table_count
                                    ),
                                )
        finally:
            monitor_engine.dispose()
            migration_engine.dispose()
            owner_admin_engine.dispose()
            admin_engine.dispose()
