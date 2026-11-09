"""Gemeinsame pytest-Konfiguration einschließlich lokaler PostgreSQL-Tests."""

from __future__ import annotations

import ipaddress
import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import OperationalError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
POSTGRES_TEST_ENV_FILE = PROJECT_ROOT / "config" / "postgres-test.env"
POSTGRES_URL_VARIABLES = (
    "SIMPLEOB_POSTGRES_TEST_URL",
    "SIMPLEOB_TEST_POSTGRESQL_URL",
)
EXPECTED_TEST_DATABASE = "simpleob_migration_test"
LOCAL_POSTGRES_HOSTS = {"localhost", "127.0.0.1", "::1"}


def _read_env_file(path: Path) -> dict[str, str]:
    """Liest die benötigten KEY=VALUE-Zeilen ohne externe dotenv-Abhängigkeit."""

    if not path.is_file():
        return {}

    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if key:
            values[key] = value
    return values


def _local_postgres_url(values: dict[str, str]) -> str | None:
    """Erzeugt nur dann URLs, wenn alle Angaben einschließlich Passwort vorliegen."""

    required = (
        "SIMPLEOB_TEST_PG_HOST",
        "SIMPLEOB_TEST_PG_PORT",
        "SIMPLEOB_TEST_PG_DATABASE",
        "SIMPLEOB_TEST_PG_USER",
        "SIMPLEOB_TEST_PG_PASSWORD",
    )
    if any(not values.get(key, "").strip() for key in required):
        return None

    try:
        port = int(values["SIMPLEOB_TEST_PG_PORT"])
    except ValueError:
        return None

    url = URL.create(
        "postgresql+psycopg",
        username=values["SIMPLEOB_TEST_PG_USER"],
        password=values["SIMPLEOB_TEST_PG_PASSWORD"],
        host=values["SIMPLEOB_TEST_PG_HOST"],
        port=port,
        database=values["SIMPLEOB_TEST_PG_DATABASE"],
    )
    return url.render_as_string(hide_password=False)


def _local_config_status() -> str:
    if not POSTGRES_TEST_ENV_FILE.is_file():
        return "Datei config/postgres-test.env fehlt"

    values = _read_env_file(POSTGRES_TEST_ENV_FILE)
    required = (
        "SIMPLEOB_TEST_PG_HOST",
        "SIMPLEOB_TEST_PG_PORT",
        "SIMPLEOB_TEST_PG_DATABASE",
        "SIMPLEOB_TEST_PG_USER",
    )
    if any(not values.get(key, "").strip() for key in required):
        return "Konfiguration unvollständig; Angaben in config/postgres-test.env prüfen"
    if not values.get("SIMPLEOB_TEST_PG_PASSWORD", "").strip():
        return "Passwort fehlt in config/postgres-test.env"
    try:
        port = int(values["SIMPLEOB_TEST_PG_PORT"])
    except ValueError:
        return "Ungültiger Port in config/postgres-test.env"
    if not 1 <= port <= 65535:
        return "Ungültiger Port in config/postgres-test.env"
    return "Konfiguration vorhanden; Verbindungsprüfung steht noch aus"


_local_values = _read_env_file(POSTGRES_TEST_ENV_FILE)
_local_url = _local_postgres_url(_local_values)
if _local_url is not None:
    for variable in POSTGRES_URL_VARIABLES:
        os.environ.setdefault(variable, _local_url)


def pytest_report_header() -> str:
    """Zeigt nur den Konfigurationsstatus, niemals URL oder Zugangsdaten."""

    if any(os.environ.get(variable) for variable in POSTGRES_URL_VARIABLES):
        return "PostgreSQL-Testkonfiguration: gesetzt; Zielprüfung erfolgt vor PG-Tests"
    return f"PostgreSQL-Tests nicht konfiguriert; {_local_config_status()}"


def _validate_database_url(variable: str, value: str) -> URL:
    try:
        url = make_url(value)
    except (TypeError, ValueError):
        pytest.exit(
            f"{variable} ist keine gültige PostgreSQL-Verbindungs-URL.",
            returncode=4,
        )

    if (
        not url.drivername.startswith("postgresql")
        or url.database != EXPECTED_TEST_DATABASE
        or url.host not in LOCAL_POSTGRES_HOSTS
    ):
        pytest.exit(
            f"{variable} muss ausschließlich auf die lokale Testdatenbank "
            f"{EXPECTED_TEST_DATABASE} zeigen.",
            returncode=4,
        )
    return url


def pytest_collection_finish(session: pytest.Session) -> None:
    """Prüft PG-Ziele vor Testausführung ausschließlich lesend."""

    postgres_modules: set[Path] = set()
    inspected_paths: set[Path] = set()
    for item in session.items:
        path = Path(str(item.path))
        if path in inspected_paths:
            continue
        inspected_paths.add(path)
        try:
            source = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        if any(variable in source for variable in POSTGRES_URL_VARIABLES):
            postgres_modules.add(path)

    if not postgres_modules:
        return

    urls: dict[str, tuple[str, URL]] = {}
    for variable in POSTGRES_URL_VARIABLES:
        value = os.environ.get(variable)
        if value:
            url = _validate_database_url(variable, value)
            urls[value] = (variable, url)

    if not urls:
        return

    for value, (variable, url) in urls.items():
        engine = create_engine(url)
        try:
            with engine.connect() as connection:
                connection.exec_driver_sql(
                    "SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY"
                )
                database, address = connection.execute(
                    text("SELECT current_database(), inet_server_addr()::text")
                ).one()
                is_loopback = (
                    address is not None
                    and ipaddress.ip_interface(address).ip.is_loopback
                )
                if database != EXPECTED_TEST_DATABASE or not is_loopback:
                    pytest.exit(
                        "Die PostgreSQL-Verbindung erreichte nicht die "
                        f"freigegebene lokale Testdatenbank ({variable}).",
                        returncode=4,
                    )
        except OperationalError as exc:
            reason = str(exc.orig).lower()
            if any(
                phrase in reason
                for phrase in (
                    "password authentication failed",
                    "no password supplied",
                    "authentication failed",
                )
            ):
                detail = "Anmeldung fehlgeschlagen; Zugangsdaten prüfen."
            elif any(
                phrase in reason
                for phrase in (
                    "connection refused",
                    "could not connect",
                    "connection timed out",
                    "could not translate host name",
                )
            ):
                detail = "PostgreSQL-Server nicht erreichbar."
            else:
                detail = "PostgreSQL-Verbindung fehlgeschlagen."
            pytest.exit(
                f"{variable}: {detail} Passwort und URL werden nicht ausgegeben.",
                returncode=4,
            )
        finally:
            engine.dispose()
