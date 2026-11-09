"""Tests für die administrative PostgreSQL-Schemaprüfung."""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from simpleob.core.config import ApplicationConfig
from simpleob.database.connection_credentials import PostgreSQLCredentials
from simpleob.database.migration_service import (
    PostgreSQLSchemaStatus,
)
from simpleob.database.postgresql_administration_service import (
    PostgreSQLAdministrationService,
)
from simpleob.database.postgresql_migration_lock import (
    MIGRATION_LOCK_KEY,
)
from simpleob.database.postgresql_migration_safety import (
    PostgreSQLMigrationAction,
    PostgreSQLMigrationApproval,
)


@pytest.fixture
def database_url() -> str:
    url = os.environ.get("SIMPLEOB_POSTGRES_TEST_URL")

    if not url:
        pytest.skip("SIMPLEOB_POSTGRES_TEST_URL ist nicht gesetzt.")

    if make_url(url).database != "simpleob_migration_test":
        pytest.fail(
            "Die Tests dürfen ausschließlich 'simpleob_migration_test' verwenden."
        )

    return url


def _assert_migration_lock_available(database_url: str) -> None:
    """Prüft die Freigabe der exklusiven administrativen Sperre."""
    engine = create_engine(database_url)

    try:
        with engine.connect() as connection:
            acquired = connection.execute(
                text("SELECT pg_try_advisory_lock(:key)"),
                {"key": MIGRATION_LOCK_KEY},
            ).scalar_one()

            try:
                assert acquired is True
            finally:
                if acquired:
                    connection.execute(
                        text("SELECT pg_advisory_unlock(:key)"),
                        {"key": MIGRATION_LOCK_KEY},
                    )
                    connection.rollback()
    finally:
        engine.dispose()


def _service(
    database_url: str, *, application_config=None, **role_access
) -> PostgreSQLAdministrationService:
    config = application_config or Mock(database_url=database_url)
    return PostgreSQLAdministrationService(application_config=config, **role_access)


def test_administration_service_uses_explicit_credentials_for_engines(
    monkeypatch,
) -> None:
    config = Mock()
    config.database_url = (
        "postgresql+psycopg://migration_user@localhost:5432/simpleob_migration_test"
    )
    credentials = PostgreSQLCredentials("short-lived-secret")
    service = PostgreSQLAdministrationService(
        application_config=config,
        credentials=credentials,
    )
    engine_factory = Mock()
    monkeypatch.setattr(
        "simpleob.database.postgresql_administration_service.create_engine",
        engine_factory,
    )

    service._create_engine(config.database_url)

    engine_url = engine_factory.call_args.args[0]
    assert engine_url.password is None
    assert engine_factory.call_args.kwargs["connect_args"] == {
        "password": "short-lived-secret"
    }
    assert service._migration_service._credentials is credentials


def test_administration_service_routes_short_lived_role_credentials(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config = ApplicationConfig(
        data_dir=tmp_path,
        database_file=tmp_path / "unused.sqlite",
        taxonomy_dir=tmp_path,
        config_file=tmp_path / "config.toml",
        database_url_override=(
            "postgresql+psycopg://simpleob_operator@localhost:5432/"
            "simpleob_migration_test"
        ),
    )
    operating = PostgreSQLCredentials("operating-secret")
    migration = PostgreSQLCredentials("migration-secret")
    admin = PostgreSQLCredentials("admin-secret")
    service = PostgreSQLAdministrationService(
        application_config=config,
        operating_username="simpleob_operator",
        operating_credentials=operating,
        migration_username="simpleob_migrator",
        migration_credentials=migration,
        admin_username="simpleob_admin",
        admin_credentials=admin,
    )
    engine_factory = Mock()
    monkeypatch.setattr(
        "simpleob.database.postgresql_administration_service.create_engine",
        engine_factory,
    )

    service._create_engine(config.database_url, role="operating")
    operating_url = engine_factory.call_args.args[0]
    assert operating_url.username == "simpleob_operator"
    assert engine_factory.call_args.kwargs["connect_args"] == {
        "password": operating.password
    }

    service._create_engine(config.database_url, role="migration")
    migration_url = engine_factory.call_args.args[0]
    assert migration_url.username == "simpleob_migrator"
    assert engine_factory.call_args.kwargs["connect_args"] == {
        "password": migration.password
    }

    service._create_engine(config.database_url, role="admin")
    admin_url = engine_factory.call_args.args[0]
    assert admin_url.username == "simpleob_admin"
    assert engine_factory.call_args.kwargs["connect_args"] == {
        "password": admin.password
    }
    assert service._migration_service._credentials is migration


def test_target_database_requires_exact_explicit_confirmation() -> None:
    from sqlalchemy.engine import make_url

    url = make_url("postgresql+psycopg://user@localhost:5432/customer_books")

    with pytest.raises(ValueError, match="ausdrücklich bestätigte"):
        PostgreSQLAdministrationService._require_confirmed_database(
            url,
            "Upgrade",
            PostgreSQLMigrationApproval(),
        )

    with pytest.raises(ValueError, match="ausdrücklich bestätigte"):
        PostgreSQLAdministrationService._require_confirmed_database(
            url,
            "Upgrade",
            PostgreSQLMigrationApproval(
                confirmed_database_name="another_database"
            ),
        )

    assert (
        PostgreSQLAdministrationService._require_confirmed_database(
            url,
            "Upgrade",
            PostgreSQLMigrationApproval(
                confirmed_database_name="customer_books"
            ),
        )
        == "customer_books"
    )


def test_administrative_inspection_returns_current_schema(
    database_url: str,
) -> None:
    """Die bestehende Testdatenbank wird korrekt erkannt."""
    result = _service(database_url).inspect_schema()

    assert result.status == PostgreSQLSchemaStatus.CURRENT


def test_administrative_inspection_rejects_existing_lock(
    database_url: str,
) -> None:
    """Eine bereits aktive administrative Sperre verhindert die Prüfung."""
    engine = create_engine(make_url(database_url).set(database="postgres"))
    try:
        with engine.connect() as connection:
            connection.execute(
                text("SELECT pg_advisory_lock(:key)"),
                {"key": MIGRATION_LOCK_KEY},
            )
            connection.commit()

            try:
                with pytest.raises(
                    RuntimeError,
                    match="bereits aktiv",
                ):
                    _service(database_url).inspect_schema()
            finally:
                connection.execute(
                    text("SELECT pg_advisory_unlock(:key)"),
                    {"key": MIGRATION_LOCK_KEY},
                )
                connection.rollback()
    finally:
        engine.dispose()


def test_administrative_inspection_releases_lock(
    database_url: str,
) -> None:
    """Nach der Prüfung kann eine andere Verbindung die Sperre erwerben."""
    _service(database_url).inspect_schema()

    engine = create_engine(database_url)

    try:
        with engine.connect() as connection:
            acquired = connection.execute(
                text("SELECT pg_try_advisory_lock(:key)"),
                {"key": MIGRATION_LOCK_KEY},
            ).scalar_one()

            assert acquired is True

            connection.execute(
                text("SELECT pg_advisory_unlock(:key)"),
                {"key": MIGRATION_LOCK_KEY},
            )
            connection.rollback()
    finally:
        engine.dispose()


def test_administrative_inspection_rejects_sqlite() -> None:
    """SQLite darf nicht an den PostgreSQL-Administrationsdienst gelangen."""
    service = _service("sqlite:///:memory:")

    with pytest.raises(
        ValueError,
        match="nur für PostgreSQL",
    ):
        service.inspect_schema()


def test_administrative_inspection_rejects_other_sessions(
    database_url: str,
) -> None:
    """Andere Datenbanksitzungen verhindern die administrative Prüfung."""
    engine = create_engine(database_url)

    try:
        with engine.connect() as other_connection:
            other_connection.execute(text("SELECT 1"))

            with pytest.raises(
                RuntimeError,
                match="anderen Sitzungen",
            ):
                _service(database_url).inspect_schema()
    finally:
        engine.dispose()


def test_prepare_migration_current_schema(
    database_url: str,
) -> None:
    """Ein aktuelles Schema benötigt keine Migration."""
    result = _service(database_url).prepare_migration(
        approval=PostgreSQLMigrationApproval(confirmed_database_name="simpleob_migration_test")
    )

    assert result == PostgreSQLMigrationAction.NONE


def test_prepare_migration_rejects_other_sessions(
    database_url: str,
) -> None:
    """Andere Sitzungen verhindern die Migrationsvorbereitung."""
    engine = create_engine(database_url)

    try:
        with engine.connect() as other_connection:
            other_connection.execute(text("SELECT 1"))

            with pytest.raises(
                RuntimeError,
                match="anderen Sitzungen",
            ):
                _service(database_url).prepare_migration(
                    approval=PostgreSQLMigrationApproval(confirmed_database_name="simpleob_migration_test")
                )
    finally:
        engine.dispose()


def test_prepare_migration_rejects_sqlite() -> None:
    """Der administrative Ablauf ist ausschließlich für PostgreSQL."""
    service = _service("sqlite:///:memory:")

    with pytest.raises(
        ValueError,
        match="nur für PostgreSQL",
    ):
        service.prepare_migration(
            approval=PostgreSQLMigrationApproval(
                confirmed_database_name="simpleob_migration_test"
            )
        )


def test_migration_dry_run_current_schema(
    database_url: str,
    tmp_path: Path,
) -> None:
    """Der Probelauf erstellt und prüft ein Backup ohne Migration."""
    backup_path = tmp_path / "administrative_dry_run.dump"

    result = _service(database_url).run_migration_dry_run(
        approval=PostgreSQLMigrationApproval(confirmed_database_name="simpleob_migration_test"),
        backup_path=backup_path,
    )

    assert result.action == PostgreSQLMigrationAction.NONE
    assert result.backup_path == backup_path.resolve()
    assert result.backup_size > 0
    assert result.restored_table_count > 0
    assert backup_path.is_file()


def test_migration_dry_run_rejects_other_sessions(
    database_url: str,
    tmp_path: Path,
) -> None:
    """Bei weiteren Sitzungen wird kein Backup erstellt."""
    backup_path = tmp_path / "blocked_dry_run.dump"
    engine = create_engine(database_url)

    try:
        with engine.connect() as other_connection:
            other_connection.execute(text("SELECT 1"))

            with pytest.raises(
                RuntimeError,
                match="Weitere PostgreSQL-Sitzungen",
            ):
                _service(database_url).run_migration_dry_run(
                    approval=PostgreSQLMigrationApproval(confirmed_database_name="simpleob_migration_test"),
                    backup_path=backup_path,
                )
    finally:
        engine.dispose()

    assert not backup_path.exists()


def test_migration_dry_run_releases_lock_after_backup_failure(
    database_url: str,
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Ein Backupfehler beendet den Probelauf und gibt die Sperre frei."""
    from simpleob.database import postgresql_administration_service as module

    def failing_backup(self, *, backup_path):
        raise RuntimeError("Simulierter Backupfehler")

    monkeypatch.setattr(
        module.PostgreSQLBackupService,
        "create_backup",
        failing_backup,
    )

    with pytest.raises(
        RuntimeError,
        match="Simulierter Backupfehler",
    ):
        _service(database_url).run_migration_dry_run(
            approval=PostgreSQLMigrationApproval(confirmed_database_name="simpleob_migration_test"),
            backup_path=tmp_path / "failed_backup.dump",
        )

    _assert_migration_lock_available(database_url)


def test_migration_dry_run_releases_lock_after_restore_failure(
    database_url: str,
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Ein Restorefehler beendet den Probelauf und gibt die Sperre frei."""
    from simpleob.database import postgresql_administration_service as module

    def failing_restore(self, *, backup_path):
        raise RuntimeError("Simulierter Restorefehler")

    monkeypatch.setattr(
        module.PostgreSQLRestoreVerificationService,
        "verify_backup",
        failing_restore,
    )

    backup_path = tmp_path / "failed_restore.dump"

    with pytest.raises(
        RuntimeError,
        match="Simulierter Restorefehler",
    ):
        _service(database_url).run_migration_dry_run(
            approval=PostgreSQLMigrationApproval(confirmed_database_name="simpleob_migration_test"),
            backup_path=backup_path,
        )

    assert backup_path.is_file()
    _assert_migration_lock_available(database_url)


def test_inspect_schema_rejects_administrative_lock_on_postgres(
    database_url: str,
) -> None:
    """Eine Sperre auf 'postgres' verhindert die Schemaprüfung."""
    url = make_url(database_url)

    admin_engine = create_engine(url.set(database="postgres"))

    try:
        with admin_engine.connect() as connection:
            acquired = connection.execute(
                text("SELECT pg_try_advisory_lock(:key)"),
                {"key": MIGRATION_LOCK_KEY},
            ).scalar_one()

            connection.commit()

            assert acquired is True

            try:
                with pytest.raises(
                    RuntimeError,
                    match="andere administrative PostgreSQL-Migration",
                ):
                    _service(database_url).inspect_schema()
            finally:
                connection.execute(
                    text("SELECT pg_advisory_unlock(:key)"),
                    {"key": MIGRATION_LOCK_KEY},
                )
                connection.rollback()
    finally:
        admin_engine.dispose()


def test_migration_dry_run_rejects_administrative_lock_on_postgres(
    database_url: str,
    tmp_path: Path,
) -> None:
    """Eine administrative Sperre verhindert den Probelauf."""
    admin_engine = create_engine(make_url(database_url).set(database="postgres"))

    backup_path = tmp_path / "blocked_administrative_dry_run.dump"

    try:
        with admin_engine.connect() as connection:
            acquired = connection.execute(
                text("SELECT pg_try_advisory_lock(:key)"),
                {"key": MIGRATION_LOCK_KEY},
            ).scalar_one()

            connection.commit()
            assert acquired is True

            try:
                with pytest.raises(
                    RuntimeError,
                    match="bereits aktiv",
                ):
                    _service(database_url).run_migration_dry_run(
                        approval=PostgreSQLMigrationApproval(confirmed_database_name="simpleob_migration_test"),
                        backup_path=backup_path,
                    )
            finally:
                connection.execute(
                    text("SELECT pg_advisory_unlock(:key)"),
                    {"key": MIGRATION_LOCK_KEY},
                )
                connection.rollback()
    finally:
        admin_engine.dispose()

    assert not backup_path.exists()


def test_verify_maintenance_isolation(
    database_url: str,
) -> None:
    """Wartungsisolierung erlaubt bestehende Migrationsverbindung."""
    service = _service(database_url)

    service.verify_maintenance_isolation(confirmed_database_name="simpleob_migration_test")

    admin_engine = create_engine(make_url(database_url).set(database="postgres"))

    try:
        with admin_engine.connect() as connection:
            assert (
                connection.execute(
                    text(
                        "SELECT datallowconn FROM pg_database "
                        "WHERE datname = :database_name"
                    ),
                    {"database_name": "simpleob_migration_test"},
                ).scalar_one()
                is True
            )
    finally:
        admin_engine.dispose()


def test_verify_maintenance_isolation_rejects_other_sessions(
    database_url: str,
) -> None:
    """Eine weitere Datenbanksitzung verhindert die Wartung."""
    database_engine = create_engine(database_url)

    try:
        with database_engine.connect() as other_connection:
            other_connection.execute(text("SELECT 1"))

            with pytest.raises(
                RuntimeError,
                match="Sitzung",
            ):
                _service(database_url).verify_maintenance_isolation(confirmed_database_name="simpleob_migration_test")
    finally:
        database_engine.dispose()

    admin_engine = create_engine(make_url(database_url).set(database="postgres"))

    try:
        with admin_engine.connect() as connection:
            assert (
                connection.execute(
                    text(
                        "SELECT datallowconn FROM pg_database "
                        "WHERE datname = :database_name"
                    ),
                    {"database_name": "simpleob_migration_test"},
                ).scalar_one()
                is True
            )
    finally:
        admin_engine.dispose()


def test_maintenance_dry_run(
    database_url: str,
    tmp_path: Path,
) -> None:
    """Backup, Restore und Wartungsisolierung funktionieren gemeinsam."""
    backup_path = tmp_path / "maintenance_dry_run.dump"

    result = _service(database_url).run_maintenance_dry_run(
        approval=PostgreSQLMigrationApproval(confirmed_database_name="simpleob_migration_test"),
        backup_path=backup_path,
    )

    assert result.action == PostgreSQLMigrationAction.NONE
    assert result.backup_path == backup_path
    assert result.backup_size > 0
    assert result.restored_table_count > 0

    admin_engine = create_engine(make_url(database_url).set(database="postgres"))

    try:
        with admin_engine.connect() as connection:
            assert (
                connection.execute(
                    text(
                        "SELECT datallowconn FROM pg_database "
                        "WHERE datname = :database_name"
                    ),
                    {"database_name": "simpleob_migration_test"},
                ).scalar_one()
                is True
            )
    finally:
        admin_engine.dispose()

    _assert_migration_lock_available(database_url)


def test_maintenance_dry_run_rejects_other_sessions(
    database_url: str,
    tmp_path: Path,
) -> None:
    """Fremde Datenbanksitzungen verhindern den Probelauf."""
    backup_path = tmp_path / "blocked_maintenance.dump"
    database_engine = create_engine(database_url)

    try:
        with database_engine.connect() as other_connection:
            other_connection.execute(text("SELECT 1"))

            with pytest.raises(
                RuntimeError,
                match="Sitzungen",
            ):
                _service(database_url).run_maintenance_dry_run(
                    approval=PostgreSQLMigrationApproval(confirmed_database_name="simpleob_migration_test"),
                    backup_path=backup_path,
                )
    finally:
        database_engine.dispose()

    assert not backup_path.exists()
    _assert_migration_lock_available(database_url)


def test_execute_migration_on_connection_commits(split_role_upgrade, monkeypatch):
    unit = split_role_upgrade
    calls = []

    def simulated_upgrade(connection, **kwargs):
        assert kwargs["target_database"] == "simpleob_migration_test"
        calls.append(connection.in_transaction())

    monkeypatch.setattr(
        unit.service._migration_service,
        "_upgrade_postgresql_on_connection",
        simulated_upgrade,
    )
    engine = unit.service._create_engine(
        unit.service._migration_config.database_url, role="migration"
    )
    with engine.connect() as connection:
        unit.service._execute_migration_on_connection(
            connection, "simpleob_migration_test"
        )
        assert calls == [True]
        assert not connection.in_transaction()


def test_execute_migration_on_connection_rolls_back(split_role_upgrade, monkeypatch):
    unit = split_role_upgrade
    calls = []

    def failing_upgrade(connection, **kwargs):
        assert kwargs["target_database"] == "simpleob_migration_test"
        calls.append(connection.in_transaction())
        raise RuntimeError("Simulierter Alembic-Fehler")

    monkeypatch.setattr(
        unit.service._migration_service,
        "_upgrade_postgresql_on_connection",
        failing_upgrade,
    )
    engine = unit.service._create_engine(
        unit.service._migration_config.database_url, role="migration"
    )
    with engine.connect() as connection:
        with pytest.raises(RuntimeError, match="Simulierter Alembic-Fehler"):
            unit.service._execute_migration_on_connection(
                connection, "simpleob_migration_test"
            )
        assert calls == [True]
        assert not connection.in_transaction()


def test_migration_failure_releases_maintenance_isolation(
    split_role_upgrade, tmp_path, monkeypatch
):
    unit = split_role_upgrade

    def failing_upgrade(connection, **kwargs):
        assert connection.in_transaction() and not unit.state.allowed
        assert kwargs["target_database"] == "simpleob_migration_test"
        unit.state.events.append("upgrade-failed")
        raise RuntimeError("Simulierter Alembic-Fehler")

    upgrade = Mock(side_effect=failing_upgrade)
    monkeypatch.setattr(
        unit.service._migration_service, "_upgrade_postgresql_on_connection", upgrade
    )
    with pytest.raises(RuntimeError, match="Simulierter Alembic-Fehler"):
        unit.service.execute_migration(
            approval=_upgrade_approval(),
            backup_path=tmp_path / "maintenance_failure.dump",
        )
    upgrade.assert_called_once()
    assert unit.state.events == [
        "backup",
        "restore",
        "isolate",
        "upgrade-failed",
        "allow",
    ]
    assert unit.state.allowed and not unit.state.locked and not unit.state.transaction


def test_execute_migration_rejects_sqlite(
    tmp_path: Path,
) -> None:
    """SQLite darf nicht administrativ migriert werden."""
    service = _service("sqlite:///:memory:")

    with pytest.raises(
        ValueError,
        match="nur für PostgreSQL",
    ):
        service.execute_migration(
            approval=PostgreSQLMigrationApproval(
                confirmed_database_name="simpleob_migration_test"
            ),
            backup_path=tmp_path / "sqlite.dump",
        )


@pytest.fixture
def split_role_upgrade(monkeypatch, tmp_path):
    """Lokale SQL-/Werkzeugdoubles; Rollen- und Wartungsprüfungen laufen real."""
    from simpleob.database import migration_service as migrations
    from simpleob.database import models
    from simpleob.database import postgresql_administration_service as administration
    from simpleob.database.postgresql_existing_installation_inspector import (
        PostgreSQLDefaultPrivilege,
        PostgreSQLOwnershipAssessment,
        PostgreSQLRolePrivileges,
    )

    state = SimpleNamespace(
        status=PostgreSQLSchemaStatus.OUTDATED,
        revision="a6d18f2c94b7",
        allowed=True,
        locked=False,
        transaction=False,
        events=[],
    )
    config = ApplicationConfig(
        data_dir=tmp_path,
        database_file=tmp_path / "unused.sqlite",
        taxonomy_dir=tmp_path,
        config_file=tmp_path / "unused.toml",
        database_url_override=(
            "postgresql+psycopg://operator@unit.invalid:5432/simpleob_migration_test"
        ),
    )
    credentials = {
        role: PostgreSQLCredentials("unit-only-" + role)
        for role in ("operator", "migrator", "administrator")
    }
    service = _service(
        config.database_url,
        application_config=config,
        operating_username="operator",
        operating_credentials=credentials["operator"],
        migration_username="migrator",
        migration_credentials=credentials["migrator"],
        admin_username="administrator",
        admin_credentials=credentials["administrator"],
    )
    head = service._migration_service._head_revision(
        service._migration_service._create_alembic_config()
    )
    tables = set(models.Base.metadata.tables) | {"alembic_version"}

    missing_old_tables = {
        "guthaben_op_rueckerstattungen",
        "guthaben_op_rueckerstattungsruecknahmen",
        "kr_jahresumsatz_ergaenzungen",
    }

    def table_names():
        if state.status == PostgreSQLSchemaStatus.EMPTY:
            return []
        if state.status == PostgreSQLSchemaStatus.OUTDATED:
            return sorted(tables - missing_old_tables)
        return sorted(tables)

    monkeypatch.setattr(
        migrations, "inspect", lambda _: SimpleNamespace(get_table_names=table_names)
    )
    monkeypatch.setattr(
        migrations.MigrationContext,
        "configure",
        lambda _: SimpleNamespace(get_current_revision=lambda: state.revision),
    )
    # Unbeabsichtigte reale Verbindungen führen zu einem Testfehler.
    monkeypatch.setattr(
        "psycopg.connect",
        Mock(side_effect=AssertionError("Keine reale Datenbankverbindung erlaubt")),
    )

    assessments = []

    def assessment():
        known = state.status in (
            PostgreSQLSchemaStatus.CURRENT,
            PostgreSQLSchemaStatus.OUTDATED,
        )
        present = state.status != PostgreSQLSchemaStatus.EMPTY
        if state.status == PostgreSQLSchemaStatus.OUTDATED:
            blockers = (
                "SimpleOB-Tabellen fehlen: " + ", ".join(sorted(missing_old_tables)),
            )
        elif known:
            blockers = ()
        else:
            blockers = ("Kein bekanntes SimpleOB-Schema.",)
        privileges = PostgreSQLRolePrivileges(
            role="operator",
            database_connect=True,
            database_create=False,
            database_temporary=False,
            schema_usage=True,
            schema_create=False,
            table_privileges=tuple(
                (table, privilege, table != "alembic_version" or privilege == "SELECT")
                for table in table_names()
                for privilege in ("SELECT", "INSERT", "UPDATE", "DELETE")
            ),
            sequence_privileges=(
                ("mandanten_id_seq", "USAGE", True),
                ("mandanten_id_seq", "SELECT", True),
            )
            if known
            else (),
        )
        report = SimpleNamespace(
            operating_role="operator",
            migration_role_candidate="migrator"
            if state.status == PostgreSQLSchemaStatus.CURRENT
            else None,
            database_owner="migrator",
            schema_owner="pg_database_owner",
            schema_status=state.status,
            alembic_version_owner="migrator" if present else None,
            alembic_version_privileges=(
                ("SELECT", True),
                ("INSERT", False),
                ("UPDATE", False),
                ("DELETE", False),
            )
            if present
            else (),
            blockers=blockers,
            role_privileges=(privileges,),
            default_privileges=tuple(
                PostgreSQLDefaultPrivilege(
                    "migrator", "public", kind, "operator", privilege, False
                )
                for kind, names in (
                    ("r", ("SELECT", "INSERT", "UPDATE", "DELETE")),
                    ("S", ("USAGE", "SELECT")),
                )
                for privilege in names
            ),
            ownership_assessment=PostgreSQLOwnershipAssessment.SPLIT_ROLES_COMPATIBLE
            if state.status == PostgreSQLSchemaStatus.CURRENT
            else PostgreSQLOwnershipAssessment.UNKNOWN,
        )
        assessments.append(report)
        return report

    inspector = Mock()
    inspector.inspect.side_effect = assessment
    monkeypatch.setattr(
        administration,
        "PostgreSQLExistingInstallationInspector",
        Mock(return_value=inspector),
    )

    def result(value=None, rows=()):
        response = Mock()
        response.scalar_one.return_value = value
        response.scalar_one_or_none.return_value = value
        response.one.return_value = value
        response.one_or_none.return_value = value
        response.all.return_value = rows
        return response

    connections = []

    def engine_factory(url, **kwargs):
        url = make_url(url)
        assert url.username in credentials
        assert url.password is None
        assert kwargs["connect_args"] == {
            "password": credentials[url.username].password
        }
        backend_pid = 100 + len(connections)
        connection = MagicMock()
        connection.closed = False
        connection.dialect.name = "postgresql"
        connection.dialect.identifier_preparer.quote_identifier.side_effect = (
            lambda name: '"' + name + '"'
        )
        connection.engine.url = url
        connection.__enter__.return_value = connection
        connection.in_transaction.side_effect = lambda: state.transaction
        connection.rollback.side_effect = lambda: setattr(state, "transaction", False)

        @contextmanager
        def begin():
            state.transaction = True
            try:
                yield
            finally:
                state.transaction = False

        connection.begin.side_effect = begin

        def execute(statement, parameters=None):
            sql = " ".join(str(statement).split())
            if "pg_try_advisory_lock" in sql:
                state.locked = True
                return result(True)
            if "pg_advisory_unlock" in sql:
                state.locked = False
                return result(True)
            if "FROM pg_locks" in sql:
                return result(state.locked)
            if "current_database(), current_user, r.rolsuper" in sql:
                return result((url.database, url.username, False, True, True))
            if sql.startswith("SELECT r.rolsuper, r.rolcreatedb"):
                return result(
                    SimpleNamespace(
                        rolsuper=False, rolcreatedb=True, can_read_all_stats=True
                    )
                )
            if "current_database(), current_user, pg_get_userbyid" in sql:
                return result((url.database, url.username, "migrator"))
            if sql == "SELECT current_database(), current_user":
                from collections import namedtuple

                return result(
                    namedtuple("RoleConnection", "current_database current_user")(
                        url.database, url.username
                    )
                )
            if (
                "has_schema_privilege" in sql
                or "pg_get_userbyid(datdba) = current_user" in sql
            ):
                return result(True)
            if "FROM pg_class AS c" in sql:
                return result(
                    rows=[
                        SimpleNamespace(
                            relname=table,
                            relkind="r",
                            owner="migrator",
                            owning_table=None,
                        )
                        for table in table_names()
                    ]
                    + (
                        [
                            SimpleNamespace(
                                relname="mandanten_id_seq",
                                relkind="S",
                                owner="migrator",
                                owning_table="mandanten",
                            )
                        ]
                        if table_names()
                        else []
                    )
                )
            if sql == "SELECT pg_backend_pid()":
                return result(backend_pid)
            if sql == "SELECT current_database(), pg_backend_pid()":
                return result((url.database, backend_pid))
            if sql == "SELECT current_database()":
                return result(url.database)
            if "FROM pg_stat_activity" in sql:
                return result(rows=[])
            if "SELECT datallowconn" in sql:
                return result(state.allowed)
            if sql.startswith("ALTER DATABASE"):
                assert state.locked and url.username == "migrator"
                state.allowed = sql.endswith("true")
                state.events.append("allow" if state.allowed else "isolate")
                return result()
            raise AssertionError("Unerwartetes SQL: " + sql)

        connection.execute.side_effect = execute
        connection.exec_driver_sql.side_effect = execute
        connections.append(connection)
        engine = MagicMock()
        engine.connect.return_value = connection
        return engine

    monkeypatch.setattr(administration, "create_engine", engine_factory)
    monkeypatch.setattr(migrations, "create_engine", engine_factory)

    def backup(*, backup_path):
        state.events.append("backup")
        backup_path.write_bytes(b"simulated-backup")
        return SimpleNamespace(
            backup_path=backup_path, backup_size=backup_path.stat().st_size
        )

    backup_mock = Mock(side_effect=backup)

    def restore(*, backup_path, confirmed_source_database):
        assert (
            backup_path.is_file()
            and confirmed_source_database == "simpleob_migration_test"
        )
        state.events.append("restore")
        return SimpleNamespace(restored_table_count=len(tables))

    restore_mock = Mock(side_effect=restore)
    monkeypatch.setattr(
        administration,
        "PostgreSQLBackupService",
        Mock(return_value=SimpleNamespace(create_backup=backup_mock)),
    )
    monkeypatch.setattr(
        administration,
        "PostgreSQLRestoreVerificationService",
        Mock(return_value=SimpleNamespace(verify_backup=restore_mock)),
    )
    return SimpleNamespace(
        service=service,
        state=state,
        head=head,
        inspector=inspector,
        backup=backup_mock,
        restore=restore_mock,
        connections=connections,
        assessments=assessments,
    )


def _upgrade_approval(**overrides):
    values = dict(
        confirmed_database_name="simpleob_migration_test",
        migration_confirmed=True,
        maintenance_confirmed=True,
    )
    values.update(overrides)
    return PostgreSQLMigrationApproval(**values)


def test_execute_migration_current_schema_is_noop(split_role_upgrade, tmp_path):
    unit = split_role_upgrade
    unit.state.status = PostgreSQLSchemaStatus.CURRENT
    unit.state.revision = unit.head
    backup_path = tmp_path / "unnecessary_backup.dump"
    result = unit.service.execute_migration(
        approval=_upgrade_approval(), backup_path=backup_path
    )
    assert result.action == PostgreSQLMigrationAction.NONE
    unit.backup.assert_not_called()
    unit.restore.assert_not_called()
    assert unit.state.events == [] and not unit.state.locked


def test_execute_migration_empty_rejects_partial_approval(split_role_upgrade, tmp_path):
    unit = split_role_upgrade
    unit.state.status = PostgreSQLSchemaStatus.EMPTY
    unit.state.revision = None
    for initialize_confirmed in (False, True):
        with pytest.raises(RuntimeError, match="Bestandsprüfung"):
            unit.service.execute_migration(
                approval=_upgrade_approval(
                    initialize_confirmed=initialize_confirmed,
                    maintenance_confirmed=False,
                ),
                backup_path=tmp_path / "unapproved_initialization.dump",
            )
    assert unit.inspector.inspect.call_count == 2
    unit.backup.assert_not_called()
    assert unit.state.events == [] and not unit.state.locked


def test_execute_migration_outdated_requires_approval(split_role_upgrade, tmp_path):
    unit = split_role_upgrade
    with pytest.raises(RuntimeError, match="Migration muss ausdrücklich bestätigt"):
        unit.service.execute_migration(
            approval=_upgrade_approval(migration_confirmed=False),
            backup_path=tmp_path / "unapproved_upgrade.dump",
        )
    unit.backup.assert_not_called()
    assert unit.state.events == [] and not unit.state.locked


def test_execute_migration_outdated_success_simulated(
    split_role_upgrade, tmp_path, monkeypatch
):
    unit = split_role_upgrade

    def simulated_upgrade(connection, *, target_database, authorization):
        from simpleob.database.migration_service import (
            _ADMIN_POSTGRESQL_UPGRADE_AUTHORIZATION,
        )

        assert authorization is _ADMIN_POSTGRESQL_UPGRADE_AUTHORIZATION
        assert (
            target_database
            == connection.engine.url.database
            == "simpleob_migration_test"
        )
        assert connection.engine.url.username == "migrator"
        assert connection.in_transaction() and not unit.state.allowed
        assert unit.state.events == ["backup", "restore", "isolate"]
        unit.state.events.append("upgrade")
        unit.state.status = PostgreSQLSchemaStatus.CURRENT
        unit.state.revision = unit.head

    upgrade = Mock(side_effect=simulated_upgrade)
    monkeypatch.setattr(
        unit.service._migration_service, "_upgrade_postgresql_on_connection", upgrade
    )
    backup_path = tmp_path / "simulated_upgrade.dump"
    result = unit.service.execute_migration(
        approval=_upgrade_approval(), backup_path=backup_path
    )
    assert result.action == PostgreSQLMigrationAction.UPGRADE
    assert result.backup_path == backup_path and result.backup_size > 0
    assert result.restored_table_count > 0
    upgrade.assert_called_once()
    unit.backup.assert_called_once()
    unit.restore.assert_called_once()
    assert unit.inspector.inspect.call_count == 2
    assert any(
        connection.engine.url.username == "operator" for connection in unit.connections
    )
    assert unit.state.events == ["backup", "restore", "isolate", "upgrade", "allow"]
    assert unit.state.allowed and not unit.state.locked
    assert not unit.state.transaction


def test_execute_migration_failure_releases_isolation(
    split_role_upgrade, tmp_path, monkeypatch
):
    unit = split_role_upgrade

    def failing_upgrade(connection, *, target_database, authorization):
        assert connection.in_transaction() and not unit.state.allowed
        assert target_database == "simpleob_migration_test"
        unit.state.events.append("upgrade-failed")
        raise RuntimeError("Simulierter Alembic-Fehler")

    upgrade = Mock(side_effect=failing_upgrade)
    monkeypatch.setattr(
        unit.service._migration_service, "_upgrade_postgresql_on_connection", upgrade
    )
    backup_path = tmp_path / "simulated_failure.dump"
    with pytest.raises(RuntimeError, match="Simulierter Alembic-Fehler"):
        unit.service.execute_migration(
            approval=_upgrade_approval(), backup_path=backup_path
        )
    upgrade.assert_called_once()
    assert backup_path.is_file()
    assert unit.inspector.inspect.call_count == 1
    assert unit.state.events == [
        "backup",
        "restore",
        "isolate",
        "upgrade-failed",
        "allow",
    ]
    assert unit.state.allowed and not unit.state.locked and not unit.state.transaction
    assert unit.state.revision == "a6d18f2c94b7"


def test_execute_migration_rejects_empty_schema_before_backup(
    split_role_upgrade, tmp_path, monkeypatch
):
    unit = split_role_upgrade
    unit.state.status = PostgreSQLSchemaStatus.EMPTY
    unit.state.revision = None
    upgrade = Mock(side_effect=AssertionError("Keine Migration bei EMPTY"))
    monkeypatch.setattr(
        unit.service._migration_service, "_upgrade_postgresql_on_connection", upgrade
    )
    with pytest.raises(RuntimeError, match="Bestandsprüfung"):
        unit.service.execute_migration(
            approval=_upgrade_approval(initialize_confirmed=True),
            backup_path=tmp_path / "forbidden_initialization.dump",
        )
    unit.inspector.inspect.assert_called_once()
    assert [item.schema_status for item in unit.assessments] == [
        PostgreSQLSchemaStatus.EMPTY
    ]
    unit.backup.assert_not_called()
    unit.restore.assert_not_called()
    upgrade.assert_not_called()
    assert unit.state.events == [] and unit.state.allowed and not unit.state.locked


def test_execute_migration_rejects_unknown_schema(split_role_upgrade, tmp_path):
    unit = split_role_upgrade
    unit.state.status = PostgreSQLSchemaStatus.UNKNOWN
    unit.state.revision = "unknown_revision"
    with pytest.raises(RuntimeError, match="Bestandsprüfung"):
        unit.service.execute_migration(
            approval=_upgrade_approval(), backup_path=tmp_path / "forbidden.dump"
        )
    unit.backup.assert_not_called()
    unit.restore.assert_not_called()
    assert unit.state.events == [] and not unit.state.locked
