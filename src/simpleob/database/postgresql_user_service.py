"""Zusätzliche Benutzerverwaltung ohne Änderung der bestehenden Anmeldung."""

from __future__ import annotations

from dataclasses import replace

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

from simpleob.core.config import ApplicationConfig
from simpleob.database.connection_credentials import (
    PostgreSQLCredentials,
    database_connect_args,
)
from simpleob.database.database import Base
from simpleob.database.migration_service import DatabaseMigrationService
from simpleob.database.postgresql_initialization_service import (
    PostgreSQLInitializationService,
)
from simpleob.database.postgresql_migration_lock import postgresql_migration_lock


class PostgreSQLUserService:
    """Legt ausschließlich neue Loginrollen an; verändert keine vorhandenen Rollen."""

    def create_user(
        self,
        *,
        application_config: ApplicationConfig,
        admin_username: str,
        admin_credentials: PostgreSQLCredentials,
        application_credentials: PostgreSQLCredentials,
        migration_username: str | None = None,
        migration_credentials: PostgreSQLCredentials | None = None,
        new_database: bool,
        confirmed: bool,
    ) -> None:
        url = make_url(application_config.database_url)
        if not confirmed:
            raise ValueError("Die Benutzeranlage muss bestätigt werden.")
        if (
            url.drivername != "postgresql+psycopg"
            or not url.host
            or not url.port
            or not url.database
            or not url.username
            or url.password is not None
        ):
            raise ValueError(
                "Eine vollständige PostgreSQL-URL ohne Passwort ist nötig."
            )
        if url.database in {"postgres", "template0", "template1"}:
            raise ValueError("Systemdatenbanken sind nicht zulässig.")
        if (
            url.username == "postgres"
            or url.username.startswith("pg_")
            or "\x00" in url.username
            or "\x00" in url.database
            or len(url.username.encode()) > 63
            or len(url.database.encode()) > 63
        ):
            raise ValueError("Unzulässiger Benutzer- oder Datenbankname.")
        if (
            not application_credentials.password
            or "\x00" in application_credentials.password
        ):
            raise ValueError("Ein nicht leeres, gültiges Benutzerpasswort ist nötig.")

        admin_username = (
            admin_username.strip() if isinstance(admin_username, str) else ""
        )
        if not admin_username or "\x00" in admin_username:
            raise ValueError(
                "Eine administrative PostgreSQL-Rolle muss angegeben werden."
            )
        if new_database:
            migration_username = (
                migration_username.strip()
                if isinstance(migration_username, str)
                else ""
            )
            if (
                not migration_username
                or migration_username in {url.username, admin_username}
                or migration_username.startswith("pg_")
            ):
                raise ValueError(
                    "Betriebs-, Migrations- und Administrationsrolle müssen verschieden sein."
                )
            if (
                len(migration_username.encode()) > 63
                or "\x00" in migration_username
                or not isinstance(migration_credentials, PostgreSQLCredentials)
                or not migration_credentials.password
                or "\x00" in migration_credentials.password
            ):
                raise ValueError(
                    "Eine gültige Migrationsrolle mit nicht leerem Passwort ist erforderlich."
                )

        admin_url = url.set(username=admin_username, database="postgres")
        engine = create_engine(
            admin_url,
            isolation_level="AUTOCOMMIT",
            hide_parameters=True,
            connect_args=database_connect_args(str(admin_url), admin_credentials),
        )
        created = False
        role_may_exist = False
        temporary_createdb = False
        phase = "Verbindung zur administrativen PostgreSQL-Datenbank"
        try:
            with engine.connect() as connection:
                with postgresql_migration_lock(connection):
                    phase = "Prüfung von Benutzer und Datenbank"
                    if (
                        connection.execute(
                            text("SELECT 1 FROM pg_roles WHERE rolname = :name"),
                            {"name": url.username},
                        ).scalar_one_or_none()
                        is not None
                    ):
                        raise ValueError(
                            "Der Benutzer existiert bereits; er wird nicht verändert."
                        )
                    exists = (
                        connection.execute(
                            text("SELECT 1 FROM pg_database WHERE datname = :name"),
                            {"name": url.database},
                        ).scalar_one_or_none()
                        is not None
                    )
                    if new_database and exists:
                        raise ValueError("Die Datenbank existiert bereits.")
                    if not new_database and not exists:
                        raise ValueError(
                            "Die vorhandene Datenbank wurde nicht gefunden."
                        )
                    if new_database:
                        if (
                            connection.execute(
                                text("SELECT 1 FROM pg_roles WHERE rolname = :name"),
                                {"name": migration_username},
                            ).scalar_one_or_none()
                            is not None
                        ):
                            raise ValueError(
                                "Die Migrationsrolle existiert bereits; sie wird nicht verändert."
                            )
                        phase = "Anlegen der Betriebs- und Migrationsrolle"
                        admin_flags = connection.execute(
                            text(
                                "SELECT rolsuper, rolcreaterole "
                                "FROM pg_roles WHERE rolname = :name"
                            ),
                            {"name": admin_username},
                        ).one_or_none()
                        if admin_flags is None or (
                            not admin_flags.rolsuper and not admin_flags.rolcreaterole
                        ):
                            raise ValueError(
                                "Zum Erstellen der Rollen und zum Entfernen des "
                                "vorübergehenden CREATEDB-Rechts benötigt die "
                                "Administration CREATEROLE oder SUPERUSER."
                            )
                        # CREATE ROLE läuft auf dieser Verbindung im AUTOCOMMIT-Modus.
                        # Bei einem Verbindungsfehler kann die Rolle bereits existieren.
                        role_may_exist = True
                        self._create_role(
                            connection, url.username, application_credentials
                        )
                        # Bereits vor dem DDL markieren, damit auch ein
                        # Verbindungsabbruch nach CREATE ROLE bereinigt wird.
                        temporary_createdb = True
                        self._create_role(
                            connection,
                            migration_username,
                            migration_credentials,
                            createdb=True,
                        )
                    else:
                        phase = "Prüfen und Erteilen der Rechte für die vorhandene Datenbank"
                        self._grant_existing_access(
                            application_config,
                            admin_username,
                            admin_credentials,
                            application_credentials,
                        )
                        # Rollenanlage und Rechtevergabe wurden gemeinsam committed.
                        role_may_exist = True
                    created = True
            # Die bestehende Initialisierung erwirbt ihre eigene Advisory-Sperre.
            if new_database:
                phase = "Initialisieren der neuen Datenbank"
                PostgreSQLInitializationService().initialize_database(
                    application_config=application_config,
                    admin_username=admin_username,
                    admin_credentials=admin_credentials,
                    migration_username=migration_username,
                    migration_credentials=migration_credentials,
                    application_credentials=application_credentials,
                    confirmed=True,
                )
            phase = "Abschlussprüfung der neuen Anwendungsrolle"
            self._verify_access(application_config, application_credentials)
        except ValueError:
            raise
        except Exception as exc:
            sqlstate = self._sqlstate(exc)
            diagnostic = (
                f"Phase: {phase}. Fehlerklasse: {type(exc).__name__}. "
                f"PostgreSQL-SQLSTATE: {sqlstate or 'nicht verfügbar'}."
            )
            if role_may_exist or created:
                raise RuntimeError(
                    "Die Einrichtung ist fehlgeschlagen. Die neue Rolle wurde "
                    "möglicherweise bereits angelegt; bei einer neuen Datenbank "
                    "kann auch diese bereits bestehen. Bitte den Zustand prüfen. "
                    f"{diagnostic}"
                ) from None
            raise RuntimeError(
                "Die Benutzeranlage ist vor Abschluss der Rollenanlage "
                "fehlgeschlagen. Die Transaktion für Rollenanlage und Rechte "
                "wurde gegebenenfalls zurückgerollt. "
                f"{diagnostic}"
            ) from None
        finally:
            try:
                if temporary_createdb:
                    with engine.connect() as connection:
                        quote = connection.dialect.identifier_preparer.quote_identifier
                        exists = connection.execute(
                            text("SELECT 1 FROM pg_roles WHERE rolname = :name"),
                            {"name": migration_username},
                        ).scalar_one_or_none()
                        if exists is not None:
                            connection.exec_driver_sql(
                                f"ALTER ROLE {quote(migration_username)} NOCREATEDB"
                            )
            except Exception:
                raise RuntimeError(
                    "Die Einrichtung ist fehlgeschlagen und das vorübergehende "
                    "CREATEDB-Recht der Migrationsrolle konnte nicht entfernt "
                    "werden. Lassen Sie dieses Recht durch die PostgreSQL-"
                    "Administration prüfen und widerrufen."
                ) from None
            finally:
                engine.dispose()

    @staticmethod
    def _sqlstate(error: BaseException) -> str | None:
        """Liest ausschließlich einen SQLSTATE aus der sicheren Fehlerkette."""

        pending = [error]
        seen: set[int] = set()
        while pending:
            current = pending.pop(0)
            if id(current) in seen:
                continue
            seen.add(id(current))
            value = getattr(current, "sqlstate", None) or getattr(
                current, "pgcode", None
            )
            if isinstance(value, str) and len(value) == 5 and value.isalnum():
                return value
            for attribute in ("orig", "__cause__", "__context__"):
                nested = getattr(current, attribute, None)
                if isinstance(nested, BaseException):
                    pending.append(nested)
        return None

    @staticmethod
    def _create_role(connection, username, credentials, *, createdb=False):
        from psycopg import sql

        driver = connection.connection.driver_connection
        verifier = driver.pgconn.encrypt_password(
            credentials.password.encode(), username.encode(), b"scram-sha-256"
        ).decode()
        # Nur der SCRAM-Verifier erreicht das SQL, auch bei Server-Protokollierung.
        createdb_option = sql.SQL("CREATEDB" if createdb else "NOCREATEDB")
        statement = sql.SQL(
            "CREATE ROLE {} LOGIN NOSUPERUSER {} NOCREATEROLE "
            "NOREPLICATION NOBYPASSRLS PASSWORD {}"
        ).format(sql.Identifier(username), createdb_option, sql.Literal(verifier))
        with driver.cursor() as cursor:
            cursor.execute(statement)

    def _grant_existing_access(
        self, config, admin_username, admin_credentials, credentials
    ):
        url = make_url(config.database_url)
        admin_url = url.set(username=admin_username)
        admin_config = replace(config, database_url_override=str(admin_url))
        DatabaseMigrationService(
            application_config=admin_config,
            credentials=admin_credentials,
        ).check_ready_for_start()
        engine = create_engine(
            admin_url,
            hide_parameters=True,
            connect_args=database_connect_args(str(admin_url), admin_credentials),
        )
        try:
            with engine.begin() as connection:
                if (
                    connection.exec_driver_sql("SELECT current_schema()").scalar_one()
                    != "public"
                ):
                    raise ValueError(
                        "Die Benutzerverwaltung erwartet das SimpleOB-Schema public."
                    )
                expected = set(Base.metadata.tables) | {"alembic_version"}
                if (
                    set(inspect(connection).get_table_names(schema="public"))
                    != expected
                ):
                    raise ValueError(
                        "Das Schema enthält nicht ausschließlich die erwarteten SimpleOB-Tabellen."
                    )
                owners = (
                    connection.exec_driver_sql(
                        "SELECT DISTINCT pg_get_userbyid(c.relowner) FROM pg_class c "
                        "JOIN pg_namespace n ON n.oid = c.relnamespace "
                        "WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p', 'S')"
                    )
                    .scalars()
                    .all()
                )
                self._create_role(connection, url.username, credentials)
                quote = connection.dialect.identifier_preparer.quote_identifier
                role = quote(url.username)
                connection.exec_driver_sql(
                    f"GRANT CONNECT ON DATABASE {quote(url.database)} TO {role}"
                )
                connection.exec_driver_sql(f"GRANT USAGE ON SCHEMA public TO {role}")
                for name in sorted(expected):
                    connection.exec_driver_sql(
                        f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.{quote(name)} TO {role}"
                    )
                connection.exec_driver_sql(
                    f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {role}"
                )
                for owner in owners:
                    prefix = f"ALTER DEFAULT PRIVILEGES FOR ROLE {quote(owner)} IN SCHEMA public"
                    connection.exec_driver_sql(
                        f"{prefix} GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {role}"
                    )
                    connection.exec_driver_sql(
                        f"{prefix} GRANT USAGE, SELECT ON SEQUENCES TO {role}"
                    )
        finally:
            engine.dispose()

    @staticmethod
    def _verify_access(config, credentials):
        DatabaseMigrationService(
            application_config=config,
            credentials=credentials,
        ).check_ready_for_start()
        engine = create_engine(
            config.database_url,
            connect_args=database_connect_args(config.database_url, credentials),
        )
        try:
            with engine.connect() as connection:
                url = make_url(config.database_url)
                actual = connection.exec_driver_sql(
                    "SELECT current_database(), current_user, current_schema()"
                ).one()
                if tuple(actual) != (url.database, url.username, "public"):
                    raise RuntimeError(
                        "Unerwartete Datenbank, Rolle oder Anwendungsschema."
                    )
                for name in sorted(set(Base.metadata.tables) | {"alembic_version"}):
                    for privilege in ("SELECT", "INSERT", "UPDATE", "DELETE"):
                        if not connection.execute(
                            text(
                                "SELECT has_table_privilege(current_user, :table, :privilege)"
                            ),
                            {"table": f'public."{name}"', "privilege": privilege},
                        ).scalar_one():
                            raise RuntimeError("Erforderliche Tabellenrechte fehlen.")
                for name in inspect(connection).get_sequence_names(schema="public"):
                    if not connection.execute(
                        text(
                            "SELECT has_sequence_privilege(current_user, :sequence, 'USAGE')"
                        ),
                        {"sequence": 'public."' + name.replace('"', '""') + '"'},
                    ).scalar_one():
                        raise RuntimeError("Erforderliche Sequenzrechte fehlen.")
        finally:
            engine.dispose()
