"""Opt-in-Test mit eigenem temporärem PostgreSQL-Cluster, ohne Bestandsdaten."""

import os
import socket
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.exc import ProgrammingError

from simpleob.core.config import ApplicationConfig
from simpleob.database.connection_credentials import PostgreSQLCredentials
from simpleob.database.postgresql_user_service import PostgreSQLUserService

pytestmark = pytest.mark.integration


def test_user_management_on_isolated_cluster(tmp_path):
    binary_dir = os.environ.get("SIMPLEOB_POSTGRES_BIN")
    if not binary_dir:
        pytest.skip("SIMPLEOB_POSTGRES_BIN für isolierten PostgreSQL-Test setzen.")
    binary_dir = Path(binary_dir)
    password_file = tmp_path / "admin-password"
    password_file.write_text("temporary-admin-secret\n")
    password_file.chmod(0o600)

    def run(name, *args):
        subprocess.run(
            [str(binary_dir / name), *args],
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        )

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    cluster = str(tmp_path / "cluster")
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
    started = False
    engines = []
    try:
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
        url = URL.create(
            "postgresql+psycopg",
            username="owner_one",
            host="127.0.0.1",
            port=port,
            database="books",
        )
        bootstrap_engine = create_engine(
            url.set(username="postgres", database="postgres"),
            connect_args={"password": "temporary-admin-secret"},
            hide_parameters=True,
        )
        engines.append(bootstrap_engine)
        with bootstrap_engine.begin() as connection:
            connection.exec_driver_sql(
                "CREATE ROLE simpleob_dbadmin LOGIN CREATEDB CREATEROLE "
                "PASSWORD 'temporary-limited-admin-secret'"
            )
        config = ApplicationConfig(
            data_dir=tmp_path,
            database_file=tmp_path / "unused.db",
            taxonomy_dir=tmp_path,
            config_file=tmp_path / "config.toml",
            database_url_override=str(url),
        )
        service = PostgreSQLUserService()
        postgres_admin = PostgreSQLCredentials("temporary-admin-secret")
        admin = PostgreSQLCredentials("temporary-limited-admin-secret")
        service.create_user(
            application_config=config,
            admin_username="simpleob_dbadmin",
            admin_credentials=admin,
            application_credentials=PostgreSQLCredentials("secret-one"),
            migration_username="migrator_one",
            migration_credentials=PostgreSQLCredentials("migration-secret"),
            new_database=True,
            confirmed=True,
        )
        migration_engine = create_engine(
            url.set(username="migrator_one"),
            connect_args={"password": "migration-secret"},
        )
        operating_engine = create_engine(url, connect_args={"password": "secret-one"})
        engines.extend([migration_engine, operating_engine])
        second = replace(
            config, database_url_override=str(url.set(username="user_two"))
        )
        service.create_user(
            application_config=second,
            admin_username="postgres",
            admin_credentials=postgres_admin,
            application_credentials=PostgreSQLCredentials("secret-two"),
            new_database=False,
            confirmed=True,
        )
        # The first initialization's defaults must grant access to future
        # objects created by the migration owner to the operating role.
        with migration_engine.begin() as connection:
            connection.exec_driver_sql(
                "CREATE TABLE public.default_privilege_probe "
                "(id serial PRIMARY KEY, value text)"
            )
        with operating_engine.begin() as connection:
            connection.exec_driver_sql(
                "INSERT INTO public.default_privilege_probe (value) "
                "VALUES ('runtime access')"
            )
            assert (
                connection.exec_driver_sql(
                    "SELECT value FROM public.default_privilege_probe"
                ).scalar_one()
                == "runtime access"
            )
        with pytest.raises(ValueError, match="Benutzer.*existiert"):
            service.create_user(
                application_config=second,
                admin_username="postgres",
                admin_credentials=postgres_admin,
                application_credentials=PostgreSQLCredentials("replacement"),
                new_database=False,
                confirmed=True,
            )
        admin_engine = create_engine(
            url.set(username="postgres"),
            connect_args={"password": postgres_admin.password},
        )
        engines.append(admin_engine)
        with admin_engine.connect() as conn:
            assert (
                conn.execute(
                    text(
                        "SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname='books'"
                    )
                ).scalar_one()
                == "migrator_one"
            )
            assert not conn.execute(
                text(
                    "SELECT pg_has_role('simpleob_dbadmin','migrator_one','SET') "
                    "OR pg_has_role('simpleob_dbadmin','migrator_one','USAGE')"
                )
            ).scalar_one()
            assert (
                conn.execute(
                    text(
                        "SELECT COUNT(DISTINCT pg_get_userbyid(relowner)) "
                        "FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
                        "WHERE n.nspname='public' AND c.relkind IN ('r','p','S')"
                    )
                ).scalar_one()
                == 1
            )
            assert (
                conn.execute(
                    text(
                        "SELECT DISTINCT pg_get_userbyid(relowner) "
                        "FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
                        "WHERE n.nspname='public' AND c.relkind IN ('r','p','S')"
                    )
                ).scalar_one()
                == "migrator_one"
            )
            assert all(
                not any(row)
                for row in conn.execute(
                    text(
                        "SELECT rolcreatedb, rolcreaterole, rolsuper "
                        "FROM pg_roles WHERE rolname IN ('owner_one','migrator_one')"
                    )
                ).all()
            )
            assert not conn.execute(
                text("SELECT pg_has_role('owner_one','migrator_one','MEMBER')")
            ).scalar_one()
            assert not conn.execute(
                text(
                    "SELECT has_database_privilege('owner_one','books','CREATE') "
                    "OR has_database_privilege('owner_one','books','TEMPORARY') "
                    "OR has_schema_privilege('owner_one','public','CREATE')"
                )
            ).scalar_one()
            assert conn.execute(
                text(
                    "SELECT has_table_privilege('owner_one','public.alembic_version','SELECT') "
                    "AND has_sequence_privilege('owner_one', "
                    "(SELECT quote_ident(n.nspname)||'.'||quote_ident(c.relname) "
                    "FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
                    "WHERE c.relkind='S' AND n.nspname='public' LIMIT 1), 'USAGE')"
                )
            ).scalar_one()
            assert not any(
                conn.execute(
                    text(
                        "SELECT rolsuper, rolcreatedb, rolcreaterole, rolbypassrls FROM pg_roles WHERE rolname='user_two'"
                    )
                ).one()
            )
            assert conn.execute(
                text(
                    "SELECT rolpassword LIKE 'SCRAM-SHA-256$%' FROM pg_authid WHERE rolname='user_two'"
                )
            ).scalar_one()
        owner_engine = create_engine(url, connect_args={"password": "secret-one"})
        user_engine = create_engine(
            url.set(username="user_two"), connect_args={"password": "secret-two"}
        )
        engines.extend([owner_engine, user_engine])
        with owner_engine.connect() as conn:
            with pytest.raises(
                ProgrammingError, match="permission denied for schema public"
            ):
                conn.exec_driver_sql(
                    "CREATE TABLE public.runtime_must_not_create (id integer)"
                )
            conn.rollback()
        with migration_engine.begin() as conn:
            conn.exec_driver_sql(
                "CREATE TABLE public.rights_probe (id serial PRIMARY KEY, value text)"
            )
            conn.exec_driver_sql(
                "INSERT INTO public.rights_probe (value) VALUES ('preserved')"
            )
        with user_engine.begin() as conn:
            assert (
                conn.exec_driver_sql(
                    "SELECT value FROM public.rights_probe"
                ).scalar_one()
                == "preserved"
            )
            conn.exec_driver_sql(
                "INSERT INTO public.rights_probe (value) VALUES ('new')"
            )
            conn.exec_driver_sql(
                "UPDATE public.rights_probe SET value='updated' WHERE value='new'"
            )
            assert (
                conn.exec_driver_sql(
                    "DELETE FROM public.rights_probe WHERE value='updated'"
                ).rowcount
                == 1
            )
    finally:
        for engine in engines:
            engine.dispose()
        if started:
            run("pg_ctl", "-D", cluster, "-m", "fast", "-w", "stop")
