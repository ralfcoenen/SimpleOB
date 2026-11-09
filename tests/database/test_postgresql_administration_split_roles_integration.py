from __future__ import annotations

import os
import shutil
import socket
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
from alembic import command
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, Connection

from simpleob.core.config import ApplicationConfig
from simpleob.database.connection_credentials import PostgreSQLCredentials
from simpleob.database.migration_service import (
    DatabaseMigrationService,
    PostgreSQLSchemaStatus,
)
from simpleob.database.postgresql_administration_service import (
    PostgreSQLAdministrationService,
)
from simpleob.database.postgresql_maintenance_isolation import (
    postgresql_maintenance_isolation,
)
from simpleob.database.postgresql_migration_lock import postgresql_migration_lock
from simpleob.database.postgresql_migration_safety import (
    PostgreSQLMigrationApproval,
)


@pytest.mark.integration
def test_split_role_administrative_upgrade_on_isolated_postgresql(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
            timeout=120,
        )

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]

    cluster = str(tmp_path / "cluster")
    started = False
    engines = []
    backup_path = tmp_path / "pre-upgrade.dump"
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
        monkeypatch.setenv(
            "PATH",
            str(binary_dir) + os.pathsep + os.environ.get("PATH", ""),
        )

        postgres_password = "temporary-cluster-secret"
        migration_password = "temporary-migration-secret"
        operating_password = "temporary-operating-secret"
        admin_password = "temporary-admin-secret"
        weak_admin_password = "temporary-weak-admin-secret"
        bootstrap_url = URL.create(
            "postgresql+psycopg",
            username="postgres",
            password=postgres_password,
            host="127.0.0.1",
            port=port,
            database="postgres",
        )
        bootstrap_engine = create_engine(
            bootstrap_url,
            isolation_level="AUTOCOMMIT",
            hide_parameters=True,
        )
        engines.append(bootstrap_engine)
        with bootstrap_engine.connect() as connection:
            connection.exec_driver_sql(
                "CREATE ROLE simpleob_migrator LOGIN "
                "PASSWORD 'temporary-migration-secret'"
            )
            connection.exec_driver_sql(
                "CREATE ROLE simpleob_operator LOGIN "
                "PASSWORD 'temporary-operating-secret'"
            )
            connection.exec_driver_sql(
                "CREATE ROLE simpleob_admin LOGIN CREATEDB "
                "PASSWORD 'temporary-admin-secret'"
            )
            connection.exec_driver_sql("GRANT pg_read_all_stats TO simpleob_admin")
            connection.exec_driver_sql(
                "CREATE ROLE simpleob_weak_admin LOGIN "
                "PASSWORD 'temporary-weak-admin-secret'"
            )
            connection.exec_driver_sql(
                "CREATE DATABASE simpleob_customer_books OWNER simpleob_migrator"
            )

        migration_url = URL.create(
            "postgresql+psycopg",
            username="simpleob_migrator",
            host="127.0.0.1",
            port=port,
            database="simpleob_customer_books",
        )
        migration_credentials = PostgreSQLCredentials(migration_password)
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
            connect_args={"password": migration_password},
            hide_parameters=True,
        )
        engines.append(migration_engine)
        with migration_engine.connect() as connection:
            alembic_config = migration_service._create_alembic_config()
            alembic_config.attributes["connection"] = connection
            with connection.begin():
                command.upgrade(alembic_config, "a6d18f2c94b7")

        with migration_engine.begin() as connection:
            connection.exec_driver_sql(
                "GRANT CONNECT ON DATABASE simpleob_customer_books TO simpleob_operator"
            )
            connection.exec_driver_sql(
                "GRANT USAGE ON SCHEMA public TO simpleob_operator"
            )
            connection.exec_driver_sql(
                "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public "
                "TO simpleob_operator"
            )
            connection.exec_driver_sql(
                "GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public "
                "TO simpleob_operator"
            )
            connection.exec_driver_sql(
                "ALTER DEFAULT PRIVILEGES FOR ROLE simpleob_migrator "
                "IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE "
                "ON TABLES TO simpleob_operator"
            )
            connection.exec_driver_sql(
                "ALTER DEFAULT PRIVILEGES FOR ROLE simpleob_migrator "
                "IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES "
                "TO simpleob_operator"
            )
            connection.exec_driver_sql(
                "GRANT SELECT ON TABLE public.alembic_version TO simpleob_operator"
            )
            connection.exec_driver_sql(
                "REVOKE INSERT, UPDATE, DELETE ON TABLE public.alembic_version "
                "FROM simpleob_operator"
            )
        migration_engine.dispose()
        engines.remove(migration_engine)

        operating_url = migration_url.set(username="simpleob_operator")
        operating_credentials = PostgreSQLCredentials(operating_password)
        application_config = ApplicationConfig(
            data_dir=tmp_path,
            database_file=tmp_path / "unused.sqlite",
            taxonomy_dir=tmp_path,
            config_file=tmp_path / "config.toml",
            database_url_override=operating_url.render_as_string(hide_password=True),
        )
        approval = PostgreSQLMigrationApproval(
            migration_confirmed=True,
            maintenance_confirmed=True,
            confirmed_database_name="simpleob_customer_books",
        )

        def service(*, admin="simpleob_admin", admin_password_value=admin_password):
            return PostgreSQLAdministrationService(
                application_config=application_config,
                operating_username="simpleob_operator",
                operating_credentials=operating_credentials,
                migration_username="simpleob_migrator",
                migration_credentials=migration_credentials,
                admin_username=admin,
                admin_credentials=PostgreSQLCredentials(admin_password_value),
            )

        migration_check = DatabaseMigrationService(
            application_config=application_config,
            credentials=operating_credentials,
        )
        assert (
            migration_check.inspect_postgresql_schema().status
            == PostgreSQLSchemaStatus.OUTDATED
        )

        # Ein exakter Datenbankname ohne explizite Upgradefreigabe reicht nicht.
        with pytest.raises(RuntimeError, match="bestätigt"):
            service().execute_migration(
                approval=PostgreSQLMigrationApproval(
                    confirmed_database_name="simpleob_customer_books",
                    maintenance_confirmed=True,
                ),
                backup_path=tmp_path / "unapproved-upgrade.dump",
            )
        assert not (tmp_path / "unapproved-upgrade.dump").exists()

        # Unbekannte Alembic-Revisionen werden vor Backup und Migration abgelehnt.
        with migration_engine.connect() as connection:
            connection.execute(
                text("UPDATE alembic_version SET version_num = 'unknown_revision'")
            )
            connection.commit()
        migration_engine.dispose()
        with pytest.raises(RuntimeError):
            service().execute_migration(
                approval=approval,
                backup_path=tmp_path / "unknown-revision.dump",
            )
        assert not (tmp_path / "unknown-revision.dump").exists()
        with migration_engine.connect() as connection:
            connection.execute(
                text("UPDATE alembic_version SET version_num = 'a6d18f2c94b7'")
            )
            connection.commit()
        migration_engine.dispose()

        # Ein fehlgeschlagener Dump verhindert die Restore-Probe und Migration.
        with patch(
            "simpleob.database.postgresql_administration_service.PostgreSQLBackupService.create_backup",
            side_effect=RuntimeError("Backup failed"),
        ):
            with pytest.raises(RuntimeError, match="Backup failed"):
                service().execute_migration(
                    approval=approval,
                    backup_path=tmp_path / "failed-backup.dump",
                )
        assert (
            migration_check.inspect_postgresql_schema().status
            == PostgreSQLSchemaStatus.OUTDATED
        )

        # Falsche Migrationsrolle wird vor Backup und Wartung abgelehnt.
        wrong_migration_service = PostgreSQLAdministrationService(
            application_config=application_config,
            operating_username="simpleob_operator",
            operating_credentials=operating_credentials,
            migration_username="simpleob_operator",
            migration_credentials=operating_credentials,
            admin_username="simpleob_admin",
            admin_credentials=PostgreSQLCredentials(admin_password),
        )
        with pytest.raises(RuntimeError, match="Migrationsrolle|Eigentümerrolle"):
            wrong_migration_service.execute_migration(
                approval=approval,
                backup_path=tmp_path / "wrong-migration-role.dump",
            )
        assert not (tmp_path / "wrong-migration-role.dump").exists()

        # Unzureichende Administrationsrechte werden vor dem Dump erkannt.
        with pytest.raises(RuntimeError, match="CREATEDB"):
            service(
                admin="simpleob_weak_admin",
                admin_password_value=weak_admin_password,
            ).execute_migration(
                approval=approval,
                backup_path=tmp_path / "weak-admin.dump",
            )
        assert not (tmp_path / "weak-admin.dump").exists()

        # Eine konkurrierende Client-Sitzung blockiert den Ablauf vor dem Backup.
        operator_engine = create_engine(
            operating_url,
            connect_args={"password": operating_password},
        )
        engines.append(operator_engine)
        with operator_engine.connect() as competing_connection:
            competing_connection.exec_driver_sql("SELECT 1")
            with pytest.raises(RuntimeError, match="Sitzungen"):
                service().execute_migration(
                    approval=approval,
                    backup_path=tmp_path / "competing-client.dump",
                )
        operator_engine.dispose()
        engines.remove(operator_engine)
        assert not (tmp_path / "competing-client.dump").exists()

        # Eine fehlgeschlagene Restore-Probe darf weder Wartungssperre noch
        # Alembic-Änderung auslösen.
        with patch(
            "simpleob.database.postgresql_administration_service.PostgreSQLRestoreVerificationService.verify_backup",
            side_effect=RuntimeError("Restore probe failed"),
        ):
            with pytest.raises(RuntimeError, match="Restore probe failed"):
                service().execute_migration(
                    approval=approval,
                    backup_path=backup_path,
                )
        assert (
            migration_check.inspect_postgresql_schema().status
            == PostgreSQLSchemaStatus.OUTDATED
        )
        with bootstrap_engine.connect() as connection:
            assert connection.execute(
                text(
                    "SELECT datallowconn FROM pg_database "
                    "WHERE datname = 'simpleob_customer_books'"
                )
            ).scalar_one()
        backup_path.unlink(missing_ok=True)

        # Ein Fehler beim Wiederfreigeben wird klar gemeldet. Die Test-
        # Administration stellt den temporären Cluster danach zurück.
        maintenance_admin_engine = create_engine(
            bootstrap_url,
            isolation_level="AUTOCOMMIT",
            hide_parameters=True,
        )
        owner_admin_url = migration_url.set(database="postgres")
        owner_admin_credentialed_url = owner_admin_url.set(password=migration_password)
        owner_admin_engine = create_engine(
            owner_admin_credentialed_url,
            isolation_level="AUTOCOMMIT",
            hide_parameters=True,
        )
        migration_monitor_engine = create_engine(
            migration_url.set(password=migration_password),
            hide_parameters=True,
        )
        admin_monitor_engine = create_engine(
            migration_url.set(
                username="simpleob_admin",
                password=admin_password,
            ),
            hide_parameters=True,
        )
        try:
            with maintenance_admin_engine.connect() as admin_connection:
                with postgresql_migration_lock(admin_connection):
                    with owner_admin_engine.connect() as owner_connection:
                        with migration_monitor_engine.connect() as migration_connection:
                            with admin_monitor_engine.connect() as session_connection:
                                original_execute = Connection.execute

                                def fail_allow_true(
                                    connection,
                                    statement,
                                    *args,
                                    **kwargs,
                                ):
                                    if "ALLOW_CONNECTIONS true" in str(statement):
                                        raise RuntimeError("simulated unlock failure")
                                    return original_execute(
                                        connection,
                                        statement,
                                        *args,
                                        **kwargs,
                                    )

                                with patch.object(
                                    Connection,
                                    "execute",
                                    fail_allow_true,
                                ):
                                    with pytest.raises(
                                        RuntimeError,
                                        match="weder mit der Migrationsrolle",
                                    ):
                                        with postgresql_maintenance_isolation(
                                            application_config=migration_config,
                                            target_database="simpleob_customer_books",
                                            admin_connection=admin_connection,
                                            migration_connection=migration_connection,
                                            migration_owner_connection=owner_connection,
                                            session_inspection_connection=session_connection,
                                        ):
                                            pass
            with bootstrap_engine.connect() as connection:
                assert (
                    connection.execute(
                        text(
                            "SELECT datallowconn FROM pg_database "
                            "WHERE datname = 'simpleob_customer_books'"
                        )
                    ).scalar_one()
                    is False
                )
                connection.execute(
                    text(
                        'ALTER DATABASE "simpleob_customer_books" '
                        "WITH ALLOW_CONNECTIONS true"
                    )
                )
        finally:
            admin_monitor_engine.dispose()
            migration_monitor_engine.dispose()
            owner_admin_engine.dispose()
            maintenance_admin_engine.dispose()

        # Vollständiger echter Ablauf: pg_dump, pg_restore in temporärer DB,
        # Wartungsisolierung, Alembic-Upgrade und Runtime-Rechteprüfung.
        result = service().execute_migration(
            approval=approval,
            backup_path=backup_path,
        )
        assert result.action.value == "upgrade"
        assert result.backup_size > 0
        assert result.restored_table_count > 0
        assert result.backup_path == backup_path
        assert (
            migration_check.inspect_postgresql_schema().status
            == PostgreSQLSchemaStatus.CURRENT
        )
        with bootstrap_engine.connect() as connection:
            assert connection.execute(
                text(
                    "SELECT datallowconn FROM pg_database "
                    "WHERE datname = 'simpleob_customer_books'"
                )
            ).scalar_one()
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
            backup_path.unlink(missing_ok=True)
