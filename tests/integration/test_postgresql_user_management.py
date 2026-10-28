"""Opt-in-Test mit eigenem temporärem PostgreSQL-Cluster, ohne Bestandsdaten."""

import os
import socket
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

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
        config = ApplicationConfig(
            data_dir=tmp_path,
            database_file=tmp_path / "unused.db",
            taxonomy_dir=tmp_path,
            config_file=tmp_path / "config.toml",
            database_url_override=str(url),
        )
        service = PostgreSQLUserService()
        admin = PostgreSQLCredentials("temporary-admin-secret")
        service.create_user(
            application_config=config,
            admin_credentials=admin,
            application_credentials=PostgreSQLCredentials("secret-one"),
            new_database=True,
            confirmed=True,
        )
        second = replace(
            config, database_url_override=str(url.set(username="user_two"))
        )
        service.create_user(
            application_config=second,
            admin_credentials=admin,
            application_credentials=PostgreSQLCredentials("secret-two"),
            new_database=False,
            confirmed=True,
        )
        with pytest.raises(ValueError, match="Benutzer.*existiert"):
            service.create_user(
                application_config=second,
                admin_credentials=admin,
                application_credentials=PostgreSQLCredentials("replacement"),
                new_database=False,
                confirmed=True,
            )
        admin_engine = create_engine(
            url.set(username="postgres"), connect_args={"password": admin.password}
        )
        engines.append(admin_engine)
        with admin_engine.connect() as conn:
            assert (
                conn.execute(
                    text(
                        "SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname='books'"
                    )
                ).scalar_one()
                == "owner_one"
            )
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
        with owner_engine.begin() as conn:
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
