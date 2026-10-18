"""Löschung mit echten SQLite-Transaktionen und vollständigem Transferbestand."""

from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event, select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from simpleob.client_transfer import archive
from simpleob.client_transfer.archive import read_client_transfer_archive
from simpleob.client_transfer.importer import ClientTransferImporter
from simpleob.database.client_deletion_repository import ClientDeletionRepository
from simpleob.database.database import Base
from simpleob.services import client_deletion_service as module
from simpleob.services.client_deletion_service import (
    ClientDeletionService,
    _transfer_repositories,
)
from tests.client_transfer.test_roundtrip import (
    _build_position_provider,
    _build_rich_transfer,
)


@pytest.fixture(params=["DELETE", "WAL"])
def populated(tmp_path, request):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'deletion.db'}", connect_args={"timeout": 0.1}
    )

    @event.listens_for(engine, "connect")
    def configure(dbapi, _):
        dbapi.execute("PRAGMA foreign_keys=ON")

    with engine.connect() as connection:
        connection.exec_driver_sql(f"PRAGMA journal_mode={request.param}")
    Base.metadata.create_all(engine)
    transfer = _build_rich_transfer()
    provider = _build_position_provider()
    with Session(engine) as session:
        ClientTransferImporter(**_transfer_repositories(session)).import_transfer(
            transfer=transfer,
            position_provider=provider,
        )
        # Zweiter vollständiger Mandant, mit unabhängigen fachlichen UUIDs.
        from simpleob.client_transfer.serialization import (
            client_transfer_from_json,
            client_transfer_to_json,
        )

        encoded = client_transfer_to_json(transfer)
        import re

        for old in set(
            re.findall(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", encoded)
        ):
            encoded = encoded.replace(old, str(uuid4()))
        other = client_transfer_from_json(encoded)
        ClientTransferImporter(**_transfer_repositories(session)).import_transfer(
            transfer=other,
            position_provider=provider,
        )
    yield (
        engine,
        transfer,
        other,
        ClientDeletionService(engine=engine, position_provider=provider),
    )
    engine.dispose()


def _raw(engine):
    with engine.connect() as connection:
        return {
            table.name: connection.execute(select(table).order_by(table.c.id)).all()
            for table in Base.metadata.sorted_tables
        }


def _delete(populated, path):
    engine, transfer, other, service = populated
    return service.delete(
        company_id=transfer.client.company_id,
        expected_name=transfer.client.master_data.name,
        backup_path=path,
    )


def test_complete_delete_preserves_other_client_and_restorable_archive(
    populated, tmp_path
):
    engine, transfer, other, service = populated
    with engine.connect() as connection:
        other_before = ClientDeletionRepository(connection).capture(
            other.client.company_id
        )
        before = ClientDeletionRepository(connection).capture(
            transfer.client.company_id
        )
    assert all(before.values()), "Die Fixture muss alle 16 Tabellen abdecken."
    path = tmp_path / "verified.simpleob"
    assert _delete(populated, path) == path
    assert read_client_transfer_archive(path).client == transfer.client
    with engine.connect() as connection:
        repository = ClientDeletionRepository(connection)
        assert not any(repository.capture(transfer.client.company_id).values())
        assert repository.capture(other.client.company_id) == other_before
        assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []


@pytest.mark.parametrize(
    "stage", ["write", "read", "sync", "publish", "directory", "final_read"]
)
def test_backup_failure_never_deletes(populated, tmp_path, monkeypatch, stage):
    engine, *_ = populated
    before = _raw(engine)
    path = tmp_path / "failed.simpleob"

    def fail(*args, **kwargs):
        raise OSError("simulierter Sicherungsfehler")

    if stage == "write":
        monkeypatch.setattr(archive, "write_client_transfer_archive", fail)
    elif stage == "read":
        monkeypatch.setattr(archive, "read_client_transfer_archive", fail)
    elif stage == "sync":
        monkeypatch.setattr(archive.os, "fsync", fail)
    elif stage == "publish":
        monkeypatch.setattr(archive.os, "link", fail)
    elif stage == "directory":
        monkeypatch.setattr(archive, "_sync_backup_directory", fail)
    else:
        original = archive.read_client_transfer_archive

        def final_read(target):
            if target == path:
                fail()
            return original(target)

        monkeypatch.setattr(archive, "read_client_transfer_archive", final_read)
    with pytest.raises(OSError, match="Sicherungsfehler"):
        _delete(populated, path)
    assert _raw(engine) == before
    assert not list(tmp_path.glob(".simpleob-*"))


def test_existing_backup_is_never_overwritten(populated, tmp_path):
    engine, *_ = populated
    before = _raw(engine)
    path = tmp_path / "existing.simpleob"
    path.write_bytes(b"vorhandene Sicherung")
    with pytest.raises(FileExistsError):
        _delete(populated, path)
    assert path.read_bytes() == b"vorhandene Sicherung"
    assert _raw(engine) == before


@pytest.mark.parametrize("stage", ["during_delete", "postcheck", "commit"])
def test_rollback_preserves_every_row_and_completed_backup(
    populated, tmp_path, monkeypatch, stage
):
    engine, *_ = populated
    before = _raw(engine)
    path = tmp_path / "kept.simpleob"
    if stage == "postcheck":

        def fail(*args):
            raise ValueError("postcheck")

        monkeypatch.setattr(ClientDeletionRepository, "check_deleted", fail)
    elif stage == "during_delete":

        @event.listens_for(engine, "before_cursor_execute")
        def fail(conn, cursor, statement, parameters, context, executemany):
            if statement.startswith("DELETE FROM buchungszeilen"):
                raise ValueError("during_delete")
    else:

        @event.listens_for(engine, "commit")
        def fail(conn):
            if path.exists():
                raise ValueError("commit")

    with pytest.raises(ValueError, match=stage):
        _delete(populated, path)
    assert _raw(engine) == before
    assert read_client_transfer_archive(path)


@pytest.mark.parametrize(
    "change",
    [
        "self_reference",
        "movement_reference",
        "indirect",
        "storno",
        "position",
        "normalization",
        "extra_table",
        "extra_column",
        "trigger",
        "name",
    ],
)
def test_inconsistent_or_changed_source_is_rejected(populated, tmp_path, change):
    engine, transfer, other, _ = populated
    with engine.begin() as connection:
        target = ClientDeletionRepository(connection).capture(
            transfer.client.company_id
        )
        foreign = ClientDeletionRepository(connection).capture(other.client.company_id)
        if change == "self_reference":
            table = Base.metadata.tables["wirtschaftsjahre"]
            connection.execute(
                table.update()
                .where(table.c.id == foreign[table.name][0]["id"])
                .values(
                    opening_source_id=target[table.name][0]["id"],
                )
            )
        elif change == "movement_reference":
            table = Base.metadata.tables["anlagebewegungen"]
            connection.execute(
                table.update()
                .where(table.c.id == foreign[table.name][0]["id"])
                .values(
                    reversed_movement_id=target[table.name][0]["id"],
                )
            )
        elif change == "indirect":
            table = Base.metadata.tables["anlagebewegungen"]
            connection.execute(
                table.update()
                .where(table.c.id == target[table.name][0]["id"])
                .values(
                    wirtschaftsjahr_id=foreign["wirtschaftsjahre"][0]["id"],
                )
            )
        elif change == "storno":
            table = Base.metadata.tables["buchungen"]
            connection.execute(
                table.update()
                .where(table.c.id == foreign[table.name][0]["id"])
                .values(
                    reversal_of_booking_id=target[table.name][0]["booking_id"],
                )
            )
        elif change == "position":
            table = Base.metadata.tables["buchungszeilen"]
            connection.execute(
                table.update()
                .where(table.c.id == target[table.name][0]["id"])
                .values(position=99)
            )
        elif change == "extra_table":
            connection.execute(text("CREATE TABLE unbekannt (id INTEGER PRIMARY KEY)"))
        elif change == "extra_column":
            connection.execute(
                text("ALTER TABLE gesellschafter ADD COLUMN unbekannt TEXT")
            )
        elif change == "trigger":
            connection.execute(
                text(
                    "CREATE TRIGGER unerwartet AFTER DELETE ON mandanten BEGIN UPDATE mandanten SET name='fremd'; END"
                )
            )
        elif change == "normalization":
            table = Base.metadata.tables["konten"]
            connection.execute(
                table.update()
                .where(table.c.id == target[table.name][0]["id"])
                .values(name=" Leerzeichen ")
            )
        else:
            table = Base.metadata.tables["mandanten"]
            connection.execute(
                table.update()
                .where(table.c.id == target[table.name][0]["id"])
                .values(name="Geändert")
            )
    before = _raw(engine)
    with pytest.raises(ValueError):
        _delete(populated, tmp_path / "rejected.simpleob")
    assert _raw(engine) == before
    assert not list(tmp_path.glob("*.simpleob"))


def test_writer_is_blocked_during_backup_and_after_deletes(
    populated, tmp_path, monkeypatch
):
    engine, *_ = populated
    original_backup = module.write_verified_client_backup
    original_check = ClientDeletionRepository.check_deleted
    observed = []

    def competing_writer():
        with engine.connect() as other:
            with pytest.raises(OperationalError, match="locked"):
                other.execute(text("UPDATE mandanten SET name = 'fremder Zugriff'"))
            other.rollback()
        observed.append(True)

    def backup(*args):
        competing_writer()
        return original_backup(*args)

    def postcheck(repository, captured):
        competing_writer()
        original_check(repository, captured)

    monkeypatch.setattr(module, "write_verified_client_backup", backup)
    monkeypatch.setattr(ClientDeletionRepository, "check_deleted", postcheck)
    _delete(populated, tmp_path / "locked.simpleob")
    assert len(observed) == 2


def test_existing_writer_prevents_export(populated, tmp_path, monkeypatch):
    engine, *_ = populated
    with engine.connect() as writer:
        writer.exec_driver_sql("BEGIN IMMEDIATE")
        with pytest.raises(OperationalError, match="locked"):
            _delete(populated, tmp_path / "blocked.simpleob")
        assert not list(tmp_path.glob("*.simpleob"))
        writer.rollback()


def test_content_mismatch_prevents_publication_and_deletion(
    populated, tmp_path, monkeypatch
):
    engine, *_ = populated
    before = _raw(engine)
    original = archive.read_client_transfer_archive

    def different(path):
        transfer = original(path)
        return replace(
            transfer, application=replace(transfer.application, version="abweichend")
        )

    monkeypatch.setattr(archive, "read_client_transfer_archive", different)
    with pytest.raises(ValueError, match="weicht"):
        _delete(populated, tmp_path / "mismatch.simpleob")
    assert _raw(engine) == before
    assert not list(tmp_path.glob("*.simpleob"))


def test_omitted_export_group_is_detected_before_any_deletion(
    populated, tmp_path, monkeypatch
):
    engine, *_ = populated
    before = _raw(engine)
    original = module.ClientTransferExporter.export

    def incomplete(exporter, **kwargs):
        transfer = original(exporter, **kwargs)
        return replace(transfer, client=replace(transfer.client, shareholders=()))

    monkeypatch.setattr(module.ClientTransferExporter, "export", incomplete)
    with pytest.raises(ValueError, match="verlustfrei"):
        _delete(populated, tmp_path / "incomplete.simpleob")
    assert _raw(engine) == before
    assert not list(tmp_path.glob("*.simpleob"))


def test_real_postcheck_detects_leftover_rows(populated, tmp_path, monkeypatch):
    engine, *_ = populated
    before = _raw(engine)
    monkeypatch.setattr(ClientDeletionRepository, "delete_captured", lambda *args: None)
    with pytest.raises(ValueError, match="zurückgeblieben"):
        _delete(populated, tmp_path / "leftovers.simpleob")
    assert _raw(engine) == before
    assert read_client_transfer_archive(tmp_path / "leftovers.simpleob")


def test_valid_movement_self_reference_is_backed_up_and_deleted(populated, tmp_path):
    engine, transfer, *_ = populated
    with engine.begin() as connection:
        captured = ClientDeletionRepository(connection).capture(
            transfer.client.company_id
        )
        movement = captured["anlagebewegungen"][0]
        line = next(
            row
            for row in captured["buchungszeilen"]
            if row["id"] == movement["buchungszeile_id"]
        )
        booking = next(
            row for row in captured["buchungen"] if row["id"] == line["buchung_id"]
        )
        new_booking_id, new_movement_id = str(uuid4()), str(uuid4())
        booking_values = {key: value for key, value in booking.items() if key != "id"}
        booking_values.update(
            booking_id=new_booking_id,
            booking_type="REVERSAL",
            reversal_of_booking_id=booking["booking_id"],
        )
        booking_pk = connection.execute(
            Base.metadata.tables["buchungen"].insert().values(**booking_values)
        ).inserted_primary_key[0]
        line_pk = None
        for original in captured["buchungszeilen"]:
            if original["buchung_id"] != booking["id"]:
                continue
            values = {key: value for key, value in original.items() if key != "id"}
            values.update(
                buchung_id=booking_pk,
                side="CREDIT" if original["side"] == "DEBIT" else "DEBIT",
            )
            inserted = connection.execute(
                Base.metadata.tables["buchungszeilen"].insert().values(**values)
            ).inserted_primary_key[0]
            if original["id"] == line["id"]:
                line_pk = inserted
        values = {key: value for key, value in movement.items() if key != "id"}
        values.update(
            movement_id=new_movement_id,
            movement_type="REVERSAL",
            reversed_movement_id=movement["id"],
            buchungszeile_id=line_pk,
        )
        connection.execute(
            Base.metadata.tables["anlagebewegungen"].insert().values(**values)
        )
    path = tmp_path / "selfreference.simpleob"
    _delete(populated, path)
    archived = read_client_transfer_archive(path)
    assert len(archived.client.fixed_assets[0].movements) == 2
    assert any(
        str(m.reversed_movement_id) == movement["movement_id"]
        for m in archived.client.fixed_assets[0].movements
    )


def test_large_client_uses_bounded_sql_parameters(populated, tmp_path):
    engine, transfer, *_ = populated
    with engine.begin() as connection:
        captured = ClientDeletionRepository(connection).capture(
            transfer.client.company_id
        )
        booking = next(
            row for row in captured["buchungen"] if row["booking_type"] == "REGULAR"
        )
        lines = [
            row
            for row in captured["buchungszeilen"]
            if row["buchung_id"] == booking["id"]
        ]
        for _ in range(510):
            values = {key: value for key, value in booking.items() if key != "id"}
            values["booking_id"] = str(uuid4())
            booking_pk = connection.execute(
                Base.metadata.tables["buchungen"].insert().values(**values)
            ).inserted_primary_key[0]
            for line in lines:
                values = {key: value for key, value in line.items() if key != "id"}
                values["buchung_id"] = booking_pk
                connection.execute(
                    Base.metadata.tables["buchungszeilen"].insert().values(**values)
                )

    @event.listens_for(engine, "before_cursor_execute")
    def bounded(conn, cursor, statement, parameters, context, executemany):
        assert len(parameters) <= 502

    path = tmp_path / "large.simpleob"
    _delete(populated, path)
    archived = read_client_transfer_archive(path)
    assert sum(len(year.bookings) for year in archived.client.fiscal_years) == (
        sum(len(year.bookings) for year in transfer.client.fiscal_years) + 510
    )


def test_canonical_covers_every_actual_fk_target_with_reassigned_ids(populated):
    engine, transfer, *_ = populated
    with engine.connect() as connection:
        captured = ClientDeletionRepository(connection).capture(
            transfer.client.company_id
        )
    assert all(captured.values())
    targets = {
        fk.column.table.name
        for table in Base.metadata.sorted_tables
        for fk in table.foreign_keys
    }
    assert targets == {
        "mandanten",
        "wirtschaftsjahre",
        "buchungen",
        "buchungszeilen",
        "anlagegueter",
        "anlagebewegungen",
        "anlageabschreibungen",
    }
    reassigned = {}
    for table in Base.metadata.sorted_tables:
        technical = {"id"} | {fk.parent.name for fk in table.foreign_keys}
        reassigned[table.name] = [
            {
                name: value + 10000
                if name in technical and value is not None
                else value
                for name, value in row.items()
            }
            for row in captured[table.name]
        ]
    assert ClientDeletionRepository.canonical(captured) == (
        ClientDeletionRepository.canonical(reassigned)
    )
