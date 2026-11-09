"""Einmalige Einrichtung einer neu angelegten SimpleOB-PostgreSQL-Datenbank.

Keine Migration vorhandener Datenbanken; keine automatische Bereinigung.
"""

from __future__ import annotations

from dataclasses import dataclass

from alembic import command
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

from simpleob.core.config import ApplicationConfig
from simpleob.database.connection_credentials import (
    PostgreSQLCredentials,
    database_connect_args,
)
from simpleob.database.migration_service import (
    DatabaseMigrationService,
    PostgreSQLSchemaStatus,
)
from simpleob.database.postgresql_migration_lock import (
    postgresql_migration_lock,
)


@dataclass(frozen=True, slots=True)
class PostgreSQLInitializationResult:
    database_name: str
    owner_role: str
    operating_role: str
    initialized: bool


class PostgreSQLInitializationService:
    """Erstellt und initialisiert nur eine während des Aufrufs neu angelegte DB."""

    def initialize_database(
        self,
        *,
        application_config: ApplicationConfig,
        admin_username: str,
        admin_credentials: PostgreSQLCredentials,
        migration_username: str,
        migration_credentials: PostgreSQLCredentials,
        application_credentials: PostgreSQLCredentials,
        confirmed: bool,
    ) -> PostgreSQLInitializationResult:
        if not confirmed:
            raise ValueError(
                "Die Datenbankneuanlage muss ausdrücklich bestätigt werden."
            )
        if not isinstance(admin_credentials, PostgreSQLCredentials):
            raise TypeError("Administrative Zugangsdaten fehlen.")
        if not isinstance(application_credentials, PostgreSQLCredentials):
            raise TypeError("Zugangsdaten der Anwendungsrolle fehlen.")
        if not isinstance(migration_credentials, PostgreSQLCredentials):
            raise TypeError("Zugangsdaten der Migrationsrolle fehlen.")
        if not isinstance(admin_username, str) or not admin_username.strip():
            raise ValueError("Eine Administrationsrolle muss angegeben werden.")

        database_url = application_config.database_url
        target_url = make_url(database_url)
        if target_url.drivername != "postgresql+psycopg":
            raise ValueError("PostgreSQL mit psycopg ist erforderlich.")
        database_name = target_url.database
        operating_role = target_url.username
        owner_role = migration_username.strip() if isinstance(migration_username, str) else ""
        if not database_name or not operating_role or not owner_role:
            raise ValueError("Datenbankname sowie Betriebs- und Migrationsrolle fehlen.")
        if len({owner_role, operating_role, admin_username.strip()}) < 3:
            raise ValueError(
                "Betriebs-, Migrations- und Administrationsrolle müssen verschieden sein."
            )
        if not target_url.host or target_url.port is None:
            raise ValueError("Server und Port müssen angegeben werden.")
        if target_url.password is not None:
            raise ValueError("Die Anwendungs-URL darf kein Passwort enthalten.")
        if database_name in {"postgres", "template0", "template1"}:
            raise ValueError("Eine PostgreSQL-Systemdatenbank ist unzulässig.")

        admin_url = target_url.set(
            database="postgres",
            username=admin_username.strip(),
            password=None,
        )
        admin_url_string = admin_url.render_as_string(hide_password=False)
        admin_engine = create_engine(
            admin_url,
            connect_args=database_connect_args(
                admin_url_string, admin_credentials
            ),
            isolation_level="AUTOCOMMIT",
        )

        created = False
        try:
            with admin_engine.connect() as admin_connection:
                with postgresql_migration_lock(admin_connection):
                    admin_can_create_as_migration_owner = self._validate_roles_and_admin(
                        admin_connection,
                        admin_username.strip(),
                        owner_role,
                        operating_role,
                    )
                    public_owner = self._template_public_owner(
                        target_url, admin_username.strip(), admin_credentials
                    )
                    if (
                        public_owner not in {"pg_database_owner", owner_role}
                        and not self._is_superuser(admin_connection)
                    ):
                        raise RuntimeError(
                            "Die PostgreSQL-Rolle kann das public-Schema einer neuen "
                            "Datenbank nicht sicher der Migrationsrolle zuordnen. "
                            "Für PostgreSQL vor Version 15 ist dafür eine "
                            "Administrationsrolle mit ausreichenden Schema-Eigentümerrechten nötig."
                        )
                    exists = admin_connection.execute(
                        text("SELECT 1 FROM pg_database WHERE datname = :name"),
                        {"name": database_name},
                    ).scalar_one_or_none()
                    if exists is not None:
                        raise RuntimeError(
                            "Die gewünschte PostgreSQL-Datenbank existiert bereits."
                        )

                    preparer = admin_connection.dialect.identifier_preparer
                    db_identifier = preparer.quote_identifier(database_name)
                    owner_identifier = preparer.quote_identifier(owner_role)
                    migration_has_createdb = bool(
                        admin_connection.execute(
                            text(
                                "SELECT rolcreatedb FROM pg_roles WHERE rolname = :role"
                            ),
                            {"role": owner_role},
                        ).scalar_one()
                    )
                    if admin_can_create_as_migration_owner:
                        admin_connection.exec_driver_sql(
                            f"CREATE DATABASE {db_identifier} OWNER {owner_identifier}"
                        )
                    elif migration_has_createdb:
                        self._create_database_as_migration_role(
                            target_url,
                            owner_role,
                            migration_credentials,
                            database_name,
                        )
                    else:
                        raise RuntimeError(
                            "Die Rollen können die neue Datenbank nicht mit der "
                            "Migrationsrolle als Eigentümerin anlegen."
                        )
                    created = True

                    if migration_has_createdb:
                        admin_connection.exec_driver_sql(
                            f"ALTER ROLE {owner_identifier} NOCREATEDB"
                        )
                    migration_flags = admin_connection.execute(
                        text(
                            "SELECT rolcreatedb, rolsuper, rolcreaterole "
                            "FROM pg_roles WHERE rolname = :role"
                        ),
                        {"role": owner_role},
                    ).one()
                    if any(migration_flags):
                        raise RuntimeError(
                            "Die Migrationsrolle hat weiterhin nicht erforderliche "
                            "Datenbank- oder Rollenverwaltungsrechte."
                        )

                    if public_owner not in {"pg_database_owner", owner_role}:
                        self._set_public_schema_owner(
                            target_url,
                            admin_username.strip(),
                            admin_credentials,
                            owner_role,
                        )

                    # Alembic und alle Schemaobjekte werden ausschließlich
                    # durch die ausdrücklich angegebene Migrationsrolle erzeugt.
                    migration_url = target_url.set(username=owner_role)
                    migration_url_string = migration_url.render_as_string(
                        hide_password=False
                    )
                    migration_engine = create_engine(
                        migration_url,
                        connect_args=database_connect_args(
                            migration_url_string, migration_credentials
                        ),
                    )
                    try:
                        with migration_engine.connect() as migration_connection:
                            actual_db, actual_user = migration_connection.exec_driver_sql(
                                "SELECT current_database(), current_user"
                            ).one()
                            if actual_db != database_name or actual_user != owner_role:
                                raise RuntimeError(
                                    "Migrationsverbindung verwendet eine unerwartete "
                                    "Datenbank oder Rolle."
                                )
                            migration_connection.rollback()

                            with migration_connection.begin():
                                self._configure_new_database(
                                    migration_connection,
                                    owner_role,
                                    operating_role,
                                    database_name,
                                )

                            migration_service = DatabaseMigrationService(
                                application_config=application_config,
                                credentials=migration_credentials,
                            )
                            inspection = (
                                migration_service.inspect_postgresql_schema_on_connection(
                                    migration_connection
                                )
                            )
                            if inspection.status != PostgreSQLSchemaStatus.EMPTY:
                                raise RuntimeError(
                                    "Die neu angelegte Datenbank ist nicht leer; "
                                    "Initialisierung abgebrochen."
                                )
                            migration_connection.rollback()

                            # Kontrollierte Erstinitialisierung der gerade
                            # angelegten Datenbank; kein administrativer
                            # Upgradeaufruf für eine bestehende Datenbank.
                            alembic_config = migration_service._create_alembic_config()
                            alembic_config.attributes["connection"] = migration_connection
                            with migration_connection.begin():
                                command.upgrade(alembic_config, "head")

                            final_status = (
                                migration_service.inspect_postgresql_schema_on_connection(
                                    migration_connection
                                )
                            )
                            if final_status.status != PostgreSQLSchemaStatus.CURRENT:
                                raise RuntimeError(
                                    "Die Datenbank wurde nicht bis zur aktuellen "
                                    "Alembic-Revision initialisiert."
                                )
                            migration_connection.rollback()
                    finally:
                        migration_engine.dispose()

                    self._grant_and_verify_operating_access(
                        target_url,
                        operating_role,
                        owner_role,
                        migration_credentials,
                        application_credentials,
                    )

                    # Die Abschlussprüfung bleibt unter derselben
                    # administrativen Advisory-Sperre.
                    DatabaseMigrationService(
                        application_config=application_config,
                        credentials=application_credentials,
                    ).check_ready_for_start()
        except Exception as exc:
            if created:
                raise RuntimeError(
                    "Die neue PostgreSQL-Datenbank wurde angelegt, aber die "
                    "Einrichtung oder Abschlussprüfung ist fehlgeschlagen. "
                    "Sie wird nicht automatisch gelöscht. Bitte den Fehler "
                    "administrativ prüfen; nicht unter demselben Namen "
                    "erneut anlegen."
                ) from exc
            raise
        finally:
            admin_engine.dispose()

        return PostgreSQLInitializationResult(
            database_name=database_name,
            owner_role=owner_role,
            operating_role=operating_role,
            initialized=True,
        )

    @staticmethod
    def _validate_roles_and_admin(connection, admin_username, migration_role, operating_role):
        rows = connection.execute(
            text(
                "SELECT rolname::text AS rolname, rolsuper, rolcreatedb, "
                "rolcreaterole, rolcanlogin "
                "FROM pg_roles WHERE rolname::text IN (:admin, :migration, :operating)"
            ),
            {
                "admin": admin_username,
                "migration": migration_role,
                "operating": operating_role,
            },
        ).all()
        roles = {row.rolname: row for row in rows}
        if migration_role not in roles or operating_role not in roles:
            raise RuntimeError(
                "Betriebs- und Migrationsrolle müssen vor der Datenbankanlage existieren."
            )
        if admin_username not in roles:
            raise RuntimeError("Die angegebene Administrationsrolle existiert nicht.")
        migration = roles[migration_role]
        operating = roles[operating_role]
        admin = roles[admin_username]
        if not migration.rolcanlogin or not operating.rolcanlogin:
            raise RuntimeError(
                "Betriebs- und Migrationsrolle müssen PostgreSQL-Anmeldungen erlauben."
            )
        if migration.rolsuper or migration.rolcreaterole:
            raise RuntimeError(
                "Die Migrationsrolle darf kein SUPERUSER oder CREATEROLE besitzen."
            )
        if operating.rolsuper or operating.rolcreatedb or operating.rolcreaterole:
            raise RuntimeError(
                "Die Betriebsrolle darf kein SUPERUSER, CREATEDB oder CREATEROLE besitzen."
            )
        if migration.rolcreatedb and not (admin.rolsuper or admin.rolcreaterole):
            raise RuntimeError(
                "Die temporäre CREATEDB-Berechtigung der Migrationsrolle kann nur "
                "mit SUPERUSER oder CREATEROLE wieder entfernt werden."
            )
        can_assume_migration = admin.rolsuper
        if not admin.rolsuper:
            set_option = connection.exec_driver_sql(
                "SELECT current_setting('server_version_num')::integer"
            ).scalar_one() >= 160000
            option = "SET" if set_option else "MEMBER"
            can_set_role = connection.execute(
                text(
                    "SELECT pg_has_role(current_user, CAST(:role AS name), :option)"
                ),
                {"role": migration_role, "option": option},
            ).scalar_one()
            can_assume_migration = bool(can_set_role)
        if connection.execute(
            text(
                "SELECT pg_has_role(CAST(:operating AS name), "
                "CAST(:migration AS name), 'MEMBER')"
            ),
            {"operating": operating_role, "migration": migration_role},
        ).scalar_one():
            raise RuntimeError(
                "Die Betriebsrolle darf nicht Mitglied der Migrationsrolle sein."
            )
        if not (admin.rolsuper or admin.rolcreatedb) and not migration.rolcreatedb:
            raise RuntimeError(
                "Für die Datenbankanlage benötigt entweder die Administration "
                "CREATEDB oder die Migrationsrolle vorübergehend CREATEDB."
            )
        return bool(admin.rolsuper or (admin.rolcreatedb and can_assume_migration))

    @staticmethod
    def _create_database_as_migration_role(
        target_url, migration_role, credentials, database_name
    ):
        admin_database_url = target_url.set(
            database="postgres", username=migration_role
        )
        url_string = admin_database_url.render_as_string(hide_password=False)
        engine = create_engine(
            admin_database_url,
            isolation_level="AUTOCOMMIT",
            connect_args=database_connect_args(url_string, credentials),
        )
        try:
            with engine.connect() as connection:
                actual_role, can_create = connection.exec_driver_sql(
                    "SELECT current_user, rolcreatedb FROM pg_roles "
                    "WHERE rolname = current_user"
                ).one()
                if actual_role != migration_role or not can_create:
                    raise RuntimeError(
                        "Die Migrationsrolle besitzt nicht die erwartete "
                        "vorübergehende Datenbankanlageberechtigung."
                    )
                quote = connection.dialect.identifier_preparer.quote_identifier
                connection.exec_driver_sql(
                    f"CREATE DATABASE {quote(database_name)}"
                )
        finally:
            engine.dispose()

    @staticmethod
    def _is_superuser(connection):
        return bool(
            connection.execute(
                text("SELECT rolsuper FROM pg_roles WHERE rolname = current_user")
            ).scalar_one()
        )

    @staticmethod
    def _template_public_owner(target_url, admin_username, credentials):
        template_url = target_url.set(database="template1", username=admin_username)
        template_url_string = template_url.render_as_string(hide_password=False)
        engine = create_engine(
            template_url,
            connect_args=database_connect_args(template_url_string, credentials),
        )
        try:
            with engine.connect() as connection:
                return connection.exec_driver_sql(
                    "SELECT pg_get_userbyid(nspowner) FROM pg_namespace "
                    "WHERE nspname = 'public'"
                ).scalar_one()
        finally:
            engine.dispose()

    @staticmethod
    def _set_public_schema_owner(target_url, admin_username, credentials, migration_role):
        admin_target = target_url.set(username=admin_username)
        admin_target_string = admin_target.render_as_string(hide_password=False)
        engine = create_engine(
            admin_target,
            connect_args=database_connect_args(admin_target_string, credentials),
        )
        try:
            with engine.begin() as connection:
                quote = connection.dialect.identifier_preparer.quote_identifier
                connection.exec_driver_sql(
                    f"ALTER SCHEMA public OWNER TO {quote(migration_role)}"
                )
        finally:
            engine.dispose()

    @staticmethod
    def _configure_new_database(connection, migration_role, operating_role, database_name):
        quote = connection.dialect.identifier_preparer.quote_identifier
        operating = quote(operating_role)
        database = quote(database_name)
        connection.exec_driver_sql("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
        connection.exec_driver_sql(
            f"REVOKE TEMPORARY ON DATABASE {database} FROM PUBLIC"
        )
        connection.exec_driver_sql(
            f"GRANT USAGE, CREATE ON SCHEMA public TO {quote(migration_role)}"
        )
        connection.exec_driver_sql(f"GRANT USAGE ON SCHEMA public TO {operating}")
        connection.exec_driver_sql(f"GRANT CONNECT ON DATABASE {database} TO {operating}")
        connection.exec_driver_sql(
            f"ALTER DEFAULT PRIVILEGES FOR ROLE {quote(migration_role)} IN SCHEMA public "
            f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {operating}"
        )
        connection.exec_driver_sql(
            f"ALTER DEFAULT PRIVILEGES FOR ROLE {quote(migration_role)} IN SCHEMA public "
            f"GRANT USAGE, SELECT ON SEQUENCES TO {operating}"
        )

    @staticmethod
    def _grant_and_verify_operating_access(
        target_url,
        operating_role,
        migration_role,
        migration_credentials,
        operating_credentials,
    ):
        migration_url = target_url.set(username=migration_role)
        migration_url_string = migration_url.render_as_string(hide_password=False)
        migration_engine = create_engine(
            migration_url,
            connect_args=database_connect_args(
                migration_url_string, migration_credentials
            ),
        )
        try:
            with migration_engine.begin() as connection:
                quote = connection.dialect.identifier_preparer.quote_identifier
                connection.exec_driver_sql(
                    "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public "
                    f"TO {quote(operating_role)}"
                )
                connection.exec_driver_sql(
                    "GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public "
                    f"TO {quote(operating_role)}"
                )
        finally:
            migration_engine.dispose()

        operating_url = target_url.set(username=operating_role)
        operating_url_string = operating_url.render_as_string(hide_password=False)
        operating_engine = create_engine(
            operating_url,
            connect_args=database_connect_args(
                operating_url_string, operating_credentials
            ),
        )
        try:
            with operating_engine.connect() as connection:
                (
                    actual_database,
                    actual_role,
                    schema_create,
                    database_create,
                    temporary_tables,
                    database_owner,
                    public_schema_owner,
                    schema_usage,
                    default_privilege_count,
                ) = (
                    connection.execute(
                        text(
                        "SELECT current_database(), current_user, "
                        "has_schema_privilege(current_user, 'public', 'CREATE'), "
                        "has_database_privilege(current_user, current_database(), 'CREATE'), "
                        "has_database_privilege(current_user, current_database(), 'TEMPORARY'), "
                        "(SELECT pg_get_userbyid(datdba) FROM pg_database "
                        "WHERE datname = current_database()), "
                        "(SELECT pg_get_userbyid(nspowner) FROM pg_namespace "
                        "WHERE nspname = 'public'), "
                        "has_schema_privilege(current_user, 'public', 'USAGE'), "
                        "(SELECT count(*) FROM pg_default_acl d "
                        "JOIN pg_namespace n ON n.oid=d.defaclnamespace "
                        "JOIN pg_roles r ON r.oid=d.defaclrole "
                        "WHERE n.nspname='public' AND r.rolname=:migration "
                        "AND d.defaclobjtype IN ('r','S'))"
                        ),
                        {"migration": migration_role},
                    ).one()
                )
                if (actual_database, actual_role) != (
                    target_url.database,
                    operating_role,
                ):
                    raise RuntimeError(
                        "Die Betriebsverbindung verwendet eine unerwartete Datenbank oder Rolle."
                    )
                if schema_create or database_create:
                    raise RuntimeError(
                        "Die Betriebsrolle besitzt unerwartete Rechte zum Ändern des Schemas."
                    )
                if temporary_tables:
                    raise RuntimeError(
                        "Die Betriebsrolle besitzt unerwartet das Recht zum Anlegen temporärer Tabellen."
                    )
                if (
                    database_owner != migration_role
                    or public_schema_owner not in {migration_role, "pg_database_owner"}
                    or not schema_usage
                ):
                    raise RuntimeError(
                        "Datenbankeigentum oder Schema-Usage entspricht nicht der Rollenaufteilung."
                    )
                if default_privilege_count != 2:
                    raise RuntimeError(
                        "Die Default Privileges für künftige Tabellen und Sequenzen fehlen."
                    )
                if connection.execute(
                    text(
                        "SELECT pg_has_role(current_user, CAST(:role AS name), 'MEMBER')"
                    ),
                    {"role": migration_role},
                ).scalar_one():
                    raise RuntimeError(
                        "Die Betriebsrolle besitzt über eine Rollenmitgliedschaft Eigentümerrechte."
                    )

                from simpleob.database.database import Base

                expected_tables = set(Base.metadata.tables) | {"alembic_version"}
                inspector = inspect(connection)
                if set(inspector.get_table_names(schema="public")) != expected_tables:
                    raise RuntimeError(
                        "Die initialisierte Datenbank enthält nicht die erwarteten SimpleOB-Tabellen."
                    )
                for table_name in sorted(expected_tables):
                    for privilege in ("SELECT", "INSERT", "UPDATE", "DELETE"):
                        if not connection.execute(
                            text(
                                "SELECT has_table_privilege(current_user, :table_name, :privilege)"
                            ),
                            {
                                "table_name": f'public."{table_name}"',
                                "privilege": privilege,
                            },
                        ).scalar_one():
                            raise RuntimeError(
                                "Der Betriebsrolle fehlen erforderliche Tabellenrechte."
                            )
                for sequence_name in inspector.get_sequence_names(schema="public"):
                    if not connection.execute(
                        text(
                            "SELECT has_sequence_privilege(current_user, :sequence_name, 'USAGE')"
                        ),
                        {"sequence_name": f'public."{sequence_name}"'},
                    ).scalar_one():
                        raise RuntimeError(
                            "Der Betriebsrolle fehlen erforderliche Sequenzrechte."
                        )
                owners = connection.execute(
                    text(
                        "SELECT DISTINCT pg_get_userbyid(relowner) FROM pg_class c "
                        "JOIN pg_namespace n ON n.oid = c.relnamespace "
                        "WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p', 'S', 'v', 'm', 'f')"
                    )
                ).scalars().all()
                if set(owners) != {migration_role}:
                    raise RuntimeError(
                        "Nicht alle SimpleOB-Schemaobjekte gehören der Migrationsrolle."
                    )
        finally:
            operating_engine.dispose()
