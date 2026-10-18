"""Echte PostgreSQL-Sperren; ausschließlich ein neu angelegtes Testschema."""

import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Event
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from simpleob.client_transfer.archive import read_client_transfer_archive
from simpleob.client_transfer.importer import ClientTransferImporter
from simpleob.database.client_deletion_repository import ClientDeletionRepository
from simpleob.database.database import Base
from simpleob.database.postgresql_maintenance_guard import (
    install_postgresql_maintenance_guard,
)
from simpleob.services import client_deletion_service as module
from simpleob.services.client_deletion_service import (
    ClientDeletionCommitUnknown,
    ClientDeletionService,
    _transfer_repositories,
)
from tests.client_transfer.test_roundtrip import (
    _build_position_provider,
    _build_rich_transfer,
)


@pytest.fixture
def postgres_client():
    value = os.environ.get("SIMPLEOB_POSTGRES_TEST_URL")
    if not value:
        pytest.skip("SIMPLEOB_POSTGRES_TEST_URL ist nicht gesetzt.")
    url = make_url(value)
    if (
        url.drivername != "postgresql+psycopg"
        or url.database != "simpleob_migration_test"
        or url.host not in ("localhost", "127.0.0.1")
    ):
        pytest.fail("Nur die lokale Datenbank simpleob_migration_test ist zulässig.")
    schema = "deletion_test_" + uuid4().hex
    admin = create_engine(url)
    engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    created = False
    try:
        with admin.begin() as connection:
            connection.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
        created = True
        Base.metadata.create_all(engine)
        install_postgresql_maintenance_guard(engine)
        transfer = _build_rich_transfer()
        # Die bestehende SQLite-Fixture verwendet einen Ländernamen; PostgreSQL
        # erzwingt das im Modell vorgesehene zweistellige Länderkennzeichen.
        transfer = replace(
            transfer,
            client=replace(
                transfer.client,
                master_data=replace(transfer.client.master_data, country="DE"),
            ),
        )
        provider = _build_position_provider()
        with Session(engine) as session:
            ClientTransferImporter(**_transfer_repositories(session)).import_transfer(
                transfer=transfer,
                position_provider=provider,
            )
        yield (
            engine,
            transfer,
            ClientDeletionService(engine=engine, position_provider=provider),
        )
    finally:
        engine.dispose()
        if created:
            with admin.begin() as connection:
                connection.exec_driver_sql(f'DROP SCHEMA "{schema}" CASCADE')
        admin.dispose()


def _delete(client, path):
    engine, transfer, service = client
    return service.delete(
        company_id=transfer.client.company_id,
        expected_name=transfer.client.master_data.name,
        backup_path=path,
    )


def test_postgresql_blocks_writers_on_every_table_until_commit(
    postgres_client, tmp_path, monkeypatch
):
    engine, transfer, _ = postgres_client
    original = module.write_verified_client_backup
    original_check = ClientDeletionRepository.check_deleted
    observations = []

    def attempt_writes():
        for table in Base.metadata.sorted_tables:
            with engine.connect() as writer:
                writer.exec_driver_sql("SET LOCAL lock_timeout = '100ms'")
                with pytest.raises(OperationalError) as error:
                    writer.execute(table.update().values(id=table.c.id))
                assert error.value.orig.sqlstate == "55P03"
                writer.rollback()
            observations.append(table.name)

    def backup(*args):
        attempt_writes()
        with engine.connect() as reader:
            assert reader.execute(text("SELECT count(*) FROM mandanten")).scalar() == 1
        return original(*args)

    def postcheck(repository, captured):
        attempt_writes()
        original_check(repository, captured)

    monkeypatch.setattr(module, "write_verified_client_backup", backup)
    monkeypatch.setattr(ClientDeletionRepository, "check_deleted", postcheck)
    path = tmp_path / "postgres.simpleob"
    _delete(postgres_client, path)
    assert len(observations) == 32
    assert read_client_transfer_archive(path).client == transfer.client
    with engine.connect() as connection:
        assert not any(
            ClientDeletionRepository(connection)
            .capture(transfer.client.company_id)
            .values()
        )


def test_postgresql_export_includes_writer_committed_while_waiting_for_locks(
    postgres_client, tmp_path
):
    engine, transfer, _ = postgres_client
    ready, release = Event(), Event()
    accounts = Base.metadata.tables["konten"]

    def writer():
        with engine.begin() as connection:
            connection.execute(
                accounts.update()
                .where(accounts.c.account_number == "1000")
                .values(name="Parallel geändert")
            )
            ready.set()
            assert release.wait(10)

    def before_lock(conn, cursor, statement, parameters, context, executemany):
        if statement.startswith("LOCK TABLE"):
            release.set()

    event.listen(engine, "before_cursor_execute", before_lock)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(writer)
        try:
            assert ready.wait(10)
            path = tmp_path / "latest.simpleob"
            _delete(postgres_client, path)
        finally:
            release.set()
            future.result(timeout=10)
    archived = read_client_transfer_archive(path)
    assert (
        next(a.name for a in archived.client.accounts if a.account_number == "1000")
        == "Parallel geändert"
    )


@pytest.mark.parametrize("committed", [False, True])
def test_postgresql_lost_commit_response_is_unknown_without_retry(
    postgres_client, tmp_path, monkeypatch, committed
):
    engine, transfer, _ = postgres_client
    from sqlalchemy.engine import Connection

    original_commit = Connection.commit
    attempts = []

    def commit(connection):
        # Die In-Memory-Wiederherstellung verwendet eine andere Engine.
        if connection.engine is engine:
            attempts.append(True)
            if committed:
                original_commit(connection)
            raise OperationalError(
                None,
                None,
                OSError("Commit-Antwort verloren"),
                connection_invalidated=True,
            )
        return original_commit(connection)

    monkeypatch.setattr(Connection, "commit", commit)
    path = tmp_path / "unknown.simpleob"
    with pytest.raises(ClientDeletionCommitUnknown, match="unbestimmt") as error:
        _delete(postgres_client, path)
    assert error.value.backup_path == path
    assert len(attempts) == 1
    assert read_client_transfer_archive(path)
    with engine.connect() as connection:
        exists = bool(
            connection.execute(select(Base.metadata.tables["mandanten"])).first()
        )
    assert exists is not committed


def test_postgresql_rollback_after_partial_delete(
    postgres_client, tmp_path, monkeypatch
):
    engine, transfer, _ = postgres_client
    with engine.connect() as connection:
        before = ClientDeletionRepository(connection).capture(
            transfer.client.company_id
        )

    def fail(repository, captured):
        raise ValueError("Prüfung fehlgeschlagen")

    monkeypatch.setattr(ClientDeletionRepository, "check_deleted", fail)
    path = tmp_path / "rollback.simpleob"
    with pytest.raises(ValueError, match="Prüfung"):
        _delete(postgres_client, path)
    assert read_client_transfer_archive(path)
    with engine.connect() as connection:
        assert (
            ClientDeletionRepository(connection).capture(transfer.client.company_id)
            == before
        )


@pytest.mark.parametrize("change", ["none", "trigger", "foreign_fk", "split"])
def test_schema_checks_follow_resolved_tables_with_leading_schema(
    postgres_client, change
):
    engine, *_ = postgres_client
    # Alle zusätzlichen DDL-Objekte werden mit dieser Transaktion zurückgerollt.
    with engine.connect() as connection:
        actual = connection.exec_driver_sql("SELECT current_schema()").scalar_one()
        leading = "leading_" + uuid4().hex
        connection.exec_driver_sql(f'CREATE SCHEMA "{leading}"')
        connection.exec_driver_sql(f'SET LOCAL search_path = "{leading}", "{actual}"')
        assert (
            connection.exec_driver_sql("SELECT current_schema()").scalar_one()
            == leading
        )
        if change == "trigger":
            connection.exec_driver_sql(
                f'CREATE FUNCTION "{actual}".unexpected() RETURNS trigger '
                "LANGUAGE plpgsql AS 'BEGIN RETURN OLD; END'"
            )
            connection.exec_driver_sql(
                f"CREATE TRIGGER unexpected BEFORE DELETE ON mandanten "
                f'FOR EACH ROW EXECUTE FUNCTION "{actual}".unexpected()'
            )
        elif change == "foreign_fk":
            connection.exec_driver_sql(
                f'CREATE TABLE "{leading}".external_reference '
                f'(id integer REFERENCES "{actual}".mandanten(id))'
            )
        elif change == "split":
            connection.exec_driver_sql(
                f'CREATE TABLE "{leading}".gesellschafter '
                f'(LIKE "{actual}".gesellschafter INCLUDING ALL)'
            )
        repository = ClientDeletionRepository(connection)
        if change == "none":
            repository.lock_and_check_schema()
        else:
            with pytest.raises(
                ValueError,
                match={
                    "trigger": "Datenbanktrigger",
                    "foreign_fk": "fremdes Datenbankschema",
                    "split": "verschiedenen Schemas",
                }[change],
            ):
                repository.lock_and_check_schema()
        connection.rollback()
